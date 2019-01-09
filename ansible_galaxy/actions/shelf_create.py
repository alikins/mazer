import logging
import os

# from ansible_galaxy.build import Build, BuildStatuses
# from ansible_galaxy import collection_info
from ansible_galaxy import installed_repository_db
from ansible_galaxy import matchers
# from ansible_galaxy.models.repository_spec import RepositorySpec

log = logging.getLogger(__name__)


# FIXME: move to utils
def ensure_output_dir(output_path):
    if not os.path.isdir(output_path):
        log.debug('Creating output_path: %s', output_path)
        os.makedirs(output_path)
    return output_path


def _create(galaxy_context,
            shelf_creation_context,
            repository_match_filter=None,
            display_callback=None):

    results = {}

    log.debug('shelf_creation_context: %s', shelf_creation_context)

    collections_path = shelf_creation_context.collections_path

    results['collections_path'] = collections_path
    results['errors'] = []
    results['success'] = False

    ensure_output_dir(shelf_creation_context.shelf_output_path)

    # create a ShelfIndex, ShelfRootIndex, ShelfCollectionsIndex, ShelfOtherIndex etc
    # find/load collections info from collections_path
    #     add items to ShelfIndex and friends
    # do any file bookkeeping (making backups, or versioning, or scm hook, etc)
    # serialize ShelfIndex etc to shelf_output_path
    # populate any results info needed (date, version, chksums, warnings/errors, etc)

    # if we want to filter out what to include in the shelf, pass in a matcher
    #  - using InstalledRepositoryDB and or loader helpers (TODO: rename InstalledRepositoryDB)
    all_repository_match = repository_match_filter or matchers.MatchAll()

    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    for candidate_repository in irdb.select(repository_match_filter=all_repository_match):
        log.debug('candidate_repo: %s', candidate_repository)

    results['create_results'] = {'placeholder': 'nothing to see here yet'}
    results['success'] = True

    return results


# TODO: can probably generalize/reuse some of this
def create(galaxy_context,
           shelf_creation_context,
           display_callback=None):
    '''Run shelf_create action and return an exit code suitable for process exit'''

    results = _create(galaxy_context,
                      shelf_creation_context,
                      display_callback=display_callback)

    log.debug('cli shelf_create action results: %s', results)

    if results['errors']:
        for error in results['errors']:
            display_callback(error)

    if results['success']:
        return os.EX_OK  # 0

    return os.EX_SOFTWARE  # 70
