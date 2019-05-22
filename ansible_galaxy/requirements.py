import logging

from ansible_galaxy import collection_artifact
from ansible_galaxy import download
from ansible_galaxy.models.repository_spec import FetchMethods
from ansible_galaxy.models.requirement import Requirement, RequirementOps, RequirementScopes
from ansible_galaxy.models.requirement_spec import RequirementSpec
from ansible_galaxy import repository_spec_parse

log = logging.getLogger(__name__)


def requirements_from_strings(repository_spec_strings,
                              namespace_override=None,
                              editable=False):
    requirements_list = []

    for repository_spec_string in repository_spec_strings:
        fetch_method = \
            repository_spec_parse.choose_repository_fetch_method(repository_spec_string,
                                                                 editable=editable)
        log.debug('fetch_method: %s', fetch_method)

        if fetch_method == FetchMethods.LOCAL_FILE:
            # Since we only know this is a local file we vaguely recognize, we have to
            # open it up to get any more details. We _could_ attempt to parse the file
            # name, but that rarely ends well. Filename could also be arbitrary for downloads
            # from remote urls ('mazer install http://myci.example.com/somebuildjob/latest' etc)
            spec_data = collection_artifact.load_data_from_collection_artifact(repository_spec_string)
            spec_data['fetch_method'] = fetch_method
        elif fetch_method == FetchMethods.REMOTE_URL:
            # download the url
            # hope it is a collection artifact and use load_data_from_collection_artifact() for the
            # rest of the repo_spec data
            log.debug('repository_spec_string: %s', repository_spec_string)

            tmp_downloaded_path = download.fetch_url(repository_spec_string,
                                                     # This is for random remote_urls, so always validate_certs
                                                     validate_certs=True)
            spec_data = collection_artifact.load_data_from_collection_artifact(tmp_downloaded_path)

            # pretend like this is a local_file install now
            spec_data['fetch_method'] = FetchMethods.LOCAL_FILE
        else:
            spec_data = repository_spec_parse.spec_data_from_string(repository_spec_string,
                                                                    namespace_override=namespace_override,
                                                                    editable=editable)

            spec_data['fetch_method'] = fetch_method

        log.debug('spec_data: %s', spec_data)

        req_spec = RequirementSpec.from_dict(spec_data)

        req = Requirement(repository_spec=None, op=RequirementOps.EQ, requirement_spec=req_spec)

        requirements_list.append(req)

    return requirements_list


def from_dependencies_dict(dependencies_dict, namespace_override=None, editable=False, repository_spec=None):
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
