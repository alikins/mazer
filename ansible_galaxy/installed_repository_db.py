import logging
import os

from ansible_galaxy import repository
from ansible_galaxy import matchers
from ansible_galaxy import installed_namespaces_db
from ansible_galaxy.models.requirement_spec import RequirementSpec

log = logging.getLogger(__name__)

from icecream import ic


def get_repository_paths(namespace_path):
    # TODO: abstract this a bit?  one to make it easier to mock, but also
    #       possibly to prepare for nested dirs, multiple paths, various
    #       filters/whitelist/blacklist/excludes, caching, or respecting
    #       fs ordering, etc
    #
    # TODO: do some caching, invalidation based on dir mtimes?
    try:
        # TODO: filter on any rules for what a namespace path looks like
        #       may one being 'somenamespace.somename' (a dot sep ns and name)
        #
        repository_paths = os.listdir(namespace_path)
    except OSError as e:
        log.exception(e)
        log.warning('The namespace path %s did not exist so no repositories were found.',
                    namespace_path)
        repository_paths = []

    return repository_paths


def installed_repository_iterator(galaxy_context,
                                  namespace_match_filter=None,
                                  repository_match_filter=None):
    '''For each repository in galaxy_context.content_path, yield matching repositories'''

    namespace_match_filter = namespace_match_filter or matchers.MatchAll()
    repository_match_filter = repository_match_filter or matchers.MatchAll()

    installed_namespace_db = installed_namespaces_db.InstalledNamespaceDatabase(galaxy_context)

    # TODO: iterate/filter per namespace, then per repository, then per collection/role/etc
    for namespace in installed_namespace_db.select(namespace_match_filter=namespace_match_filter):
        log.debug('Looking for repos in namespace "%s"', namespace.namespace)

        # TODO: filter potential repository_paths based on repository_match_filer before we
        #       try to listdir() instead of after
        repository_paths = get_repository_paths(namespace.path)

        for repository_path in repository_paths:

            # TODO: if we need to distinquish repo from collection or role, we could do it here
            repository_ = repository.load_from_dir(galaxy_context.content_path,
                                                   namespace=namespace.namespace,
                                                   name=repository_path,
                                                   installed=True)

            # log.debug('candidate installed repo (pre filter): %s', repository_)

            if repository_match_filter(repository_):
                log.debug('Found repository "%s" in namespace "%s"', repository_path, namespace.namespace)
                yield repository_


def requirement_spec_iterator(galaxy_context,
                              requirement_spec):

    # should only be one match here...
    log.debug('Looking for repos that match req_spec "%s"', requirement_spec)

#    path_name = os.path.join(galaxy_context.content_path,
#                             repository_spec.namespace,
#                             repository_spec.name)

    repository_ = repository.load_from_dir(galaxy_context.content_path,
                                           namespace=requirement_spec.namespace,
                                           name=requirement_spec.name,
                                           installed=True)

    log.debug('loaded repository_ %s', repository_)
    if not repository_:
        return

    # Verify the repo matches what we asked for.
    # no version specified
    # if repository_spec.version is None:
    #    repository_match_filter = matchers.MatchRepositorySpecNamespaceName([repository_spec])
    # else:
    #    repository_match_filter = matchers.MatchRepositorySpecNamespaceNameVersion([repository_spec])

    repository_match_filter = matchers.MatchRequirementSpec([requirement_spec])

    if repository_match_filter(repository_):
        log.debug('Found repository "%s" in namespace "%s" at %s',
                  repository_.repository_spec.name,
                  repository_.repository_spec.namespace,
                  repository_.path)
        yield repository_


# TODO: add a get(namespace_id, repository_id) for loading a known ns.n directly without iterating
# TODO: add a contains(namespace_id, repository_id, matchers) for checking for existince
#       without loading the Repository from disk. Useful for things
#       like 'is some_repo_spec already installed?'
class InstalledRepositoryDatabase(object):

    def __init__(self, installed_context=None):
        self.installed_context = installed_context

    # TODO: add a repository_type_filter (ie, 'collection' or 'role' or 'other' etc)
    # TODO: something like namespace_condition or namespace_callable might be more accurate
    # TODO: "search" would be more accurate name for select()
    def select(self, namespace_match_filter=None, repository_match_filter=None, repository_spec=None, requirement_spec=None):
        # ie, default to select * more or less
        repository_match_filter = repository_match_filter or matchers.MatchAll()
        namespace_match_filter = namespace_match_filter or matchers.MatchAll()

        log.debug('repository_spec: %s', repository_spec)
        log.debug(ic(repository_spec))
        if repository_spec:
            # convert the repo spec to a requirement spec with version_spec '==repospec.version'
            # We are being specific and looking for the repo identified by repository_spec
            requirement_spec_match_repo = RequirementSpec(namespace=repository_spec.namespace,
                                                          name=repository_spec.name,
                                                          version_spec='==%s' % repository_spec.version)
            installed_repositories = requirement_spec_iterator(self.installed_context, requirement_spec_match_repo)
        elif requirement_spec:
            requirement_spec_match_repo = RequirementSpec(namespace=requirement_spec.namespace,
                                                          name=requirement_spec.name,
                                                          version_spec=requirement_spec.version_spec)
            installed_repositories = requirement_spec_iterator(self.installed_context, requirement_spec_match_repo)

        else:
            installed_repositories = installed_repository_iterator(self.installed_context,
                                                                   namespace_match_filter=namespace_match_filter,
                                                                   repository_match_filter=repository_match_filter)

        for matched_installed_repository in installed_repositories:
            yield matched_installed_repository

    def by_repository_spec(self, repository_spec):
        return self.select(repository_spec=repository_spec)

    def by_requirement(self, requirement):
        requirement_spec = requirement.requirement_spec
        log.debug('requirement_spec: %s', requirement_spec)

        return self.select(requirement_spec=requirement_spec)

    def by_requirement_spec(self, requirement_spec):
        log.debug('requirement_spec: %s', requirement_spec)

        return self.select(requirement_spec=requirement_spec)
