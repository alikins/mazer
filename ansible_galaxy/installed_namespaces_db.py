
import logging
import os

from ansible_galaxy import matchers
from ansible_galaxy.models.galaxy_namespace import GalaxyNamespace

log = logging.getLogger(__name__)


# FIXME: This could be used to automatically include the last 'ansible_collections'
#        part of collections_path
def get_namespace_paths(collections_path):
    # TODO: abstract this a bit?  one to make it easier to mock, but also
    #       possibly to prepare for nested dirs, multiple paths, various
    #       filters/whitelist/blacklist/excludes, caching, or respecting
    #       fs ordering, etc
    try:
        # TODO: filter on any rules for what a namespace path looks like
        #       may one being 'somenamespace.somename' (a dot sep ns and name)
        #
        namespace_paths = os.listdir(collections_path)
    except OSError as e:
        log.exception(e)
        log.warning('The content path %s did not exist so no content or repositories were found.',
                    collections_path)
        namespace_paths = []

    return namespace_paths


def installed_namespace_iterator(galaxy_context,
                                 match_filter=None):

    namespace_match_filter = match_filter or matchers.MatchAll()

    collections_path = galaxy_context.collections_path

    namespace_paths = get_namespace_paths(collections_path)

    log.debug('Looking for namespaces in %s', collections_path)
    for namespace_path in namespace_paths:
        # FIXME: This needs to compensate for 'ansible_collections'
        namespace_full_path = os.path.join(collections_path, namespace_path)

        collection_namespace = GalaxyNamespace(namespace=namespace_path,
                                               path=namespace_full_path)

        if namespace_match_filter(collection_namespace):
            log.debug('Found namespace "%s"', collection_namespace.namespace)
            yield collection_namespace


class InstalledNamespaceDatabase(object):
    def __init__(self, installed_context=None):
        self.installed_context = installed_context

    def select(self, namespace_match_filter=None):
        namespace_match_filter = namespace_match_filter or matchers.MatchAll()

        installed_namespaces = installed_namespace_iterator(self.installed_context,
                                                            match_filter=namespace_match_filter)

        for matched_namespace in installed_namespaces:
            yield matched_namespace
