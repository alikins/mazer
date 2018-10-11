# strategy for installing a Collection (name resolve it, find it,
#  fetch it's artifact, validate/verify it, install/extract it, update install dbs, etc)
import logging
# import pprint

from ansible_galaxy import exceptions
from ansible_galaxy.fetch import fetch_factory

log = logging.getLogger(__name__)

# This should probably be a state machine for stepping through the install states
# See actions.install.install_collection for a sketch of the states
#
# But... we are going to start with just extracting the related bits of
# flat_rest_api.content.GalaxyContent here as methods

# def find
# def fetch
# def install
# def update_dbs


def fetcher(galaxy_context, content_spec):
    log.debug('Attempting to get fetcher for content_spec=%s', content_spec)

    fetcher = fetch_factory.get(galaxy_context=galaxy_context,
                                content_spec=content_spec)

    log.debug('Using fetcher: %s for content_spec: %s', fetcher, content_spec)

    return fetcher


def find(fetcher, collection):
    """find/discover info about the content

    This is all side effect, setting self._find_results."""

    log.debug('Attempting to find() content_spec=%s', collection.content_spec)

    # TODO: sep method, called from actions.install
    find_results = fetcher.find()

    log.debug('find() found info for %s: %s', collection, find_results)

    return find_results


# def fetch(fetcher, collection):
#    pass

def fetch(fetcher, content_spec, find_results):
    """download the archive and side effect set self._archive_path to where it was downloaded to.

    MUST be called after self.find()."""

    log.debug('Fetching content_spec=%s', content_spec)

    try:
        # FIXME: note that ignore_certs for the galaxy
        # server(galaxy_context.server['ignore_certs'])
        # does not really imply that the repo archive download should ignore certs as well
        # (galaxy api server vs cdn) but for now, we use the value for both
        fetch_results = fetcher.fetch(find_results=find_results)
    except exceptions.GalaxyDownloadError as e:
        log.exception(e)

        # TODO: having to keep fetcher state for tracking fetcher.remote_resource and/or cleanup
        #       is kind of annoying.These methods may need to be in a class. Or maybe
        #       the GalaxyDownloadError shoud/could have any info.
        blurb = 'Failed to fetch the content archive "%s": %s'
        log.error(blurb, fetcher.remote_resource, e)

        # reraise, currently handled in main
        # TODO: if we support more than one archive per invocation, will need to accumulate errors
        #       if we want to skip some of them
        raise

    # self._fetch_results = fetch_results
    # self._archive_path = fetch_results['archive_path']

    return fetch_results


# The caller of install() may be the best place to figure out things like where to
# extract the content too. Can likely handle figuring out if artifact is a collection_artifact
# or a trad_role_artifact and call different things. Or better, create an approriate
# ArchiveArtifact and just call it's extract()/install() etc.
def install(fetch_results, enough_info_to_figure_out_where_to_extract_etc):
    pass
