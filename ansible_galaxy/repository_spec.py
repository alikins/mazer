import logging

import attr

from ansible_galaxy import repository_spec_parse
from ansible_galaxy.models.repository_spec import RepositorySpec


log = logging.getLogger(__name__)


def repository_spec_from_string(repository_spec_string, namespace_override=None, editable=False):
    spec_data = repository_spec_parse.spec_data_from_string(repository_spec_string, namespace_override=namespace_override, editable=editable)

    log.debug('spec_data: %s', spec_data)

    return RepositorySpec(name=spec_data.get('name'),
                          namespace=spec_data.get('namespace'),
                          version=spec_data.get('version'),
                          # version=version,
                          scm=spec_data.get('scm'),
                          spec_string=spec_data.get('spec_string'),
                          fetch_method=spec_data.get('fetch_method'),
                          src=spec_data.get('src'))


def repository_spec_from_find_results(find_results,
                                      requirement_spec):
    '''Create a new RepositorySpec with updated info from fetch_results.

    Evolves repository_spec to match fetch results.'''

    # TODO: do we still need to check the fetched version against the spec version?
    #       We do, since the unspecific version is None, so fetched versions wont match
    #       so we need a new repository_spec for install.
    # TODO: this is more or less a verify/validate step or state transition
    content_data = find_results.get('content', {})
    resolved_version = content_data.get('version')

    log.debug('version_spec "%s" for %s was requested and was resolved to version "%s"',
              requirement_spec.version_spec, requirement_spec.label,
              resolved_version)

    # In theory, a fetch can return a different namespace/name than the one request. This
    # is for things like server side aliases.
    resolved_name = content_data.get('fetched_name', requirement_spec.name)
    resolved_namespace = content_data.get('content_namespace', requirement_spec.namespace)

    # Build a RepositorySpec based on RequirementSpec and the extra info resolved in find()
    spec_data = attr.asdict(requirement_spec)

    del spec_data['version_spec']

    spec_data['version'] = resolved_version
    spec_data['namespace'] = resolved_namespace
    spec_data['name'] = resolved_name

    repository_spec = RepositorySpec.from_dict(spec_data)
    return repository_spec
