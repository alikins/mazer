import logging

from ansible_galaxy import requirement_spec
from ansible_galaxy.fetch import fetch_factory
from ansible_galaxy.models.requirement import Requirement, RequirementOps, RequirementScopes
from ansible_galaxy.models.requirement_spec import RequirementSpec
from ansible_galaxy import repository_spec_parse

log = logging.getLogger(__name__)


def requirements_from_strings(requirement_spec_strings,
                              namespace_override=None,
                              editable=False):
    requirements_list = []

    for requirement_spec_string in requirement_spec_strings:
        req_spec = requirement_spec.requirement_spec_from_string(requirement_spec_string)

        req = Requirement(repository_spec=None, op=RequirementOps.EQ,
                          requirement_spec=req_spec)

        log.debug('Requirement: %s', Requirement)

        requirements_list.append(req)

    return requirements_list


def from_dependencies_dict(dependencies_dict,
                           namespace_override=None,
                           editable=False,
                           repository_spec=None):
    '''Build a list of Requirement objects from the 'dependencies' item in galaxy.yml'''
    reqs = []
    for req_label, req_version_spec in dependencies_dict.items():
        req_spec_data = repository_spec_parse.spec_data_from_string(req_label,
                                                                    namespace_override=namespace_override,
                                                                    editable=editable)
        req_spec_data['version_spec'] = req_version_spec

        log.debug('req_spec_data: %s', req_spec_data)

        req_spec = RequirementSpec.from_dict(req_spec_data)

        log.debug('req_spec: %s', req_spec)

        requirement = Requirement(repository_spec=repository_spec, op=RequirementOps.EQ,
                                  scope=RequirementScopes.INSTALL,
                                  requirement_spec=req_spec)

        log.debug('requirement: %s', requirement)

        reqs.append(requirement)

    return reqs
