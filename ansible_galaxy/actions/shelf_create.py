import logging
import os
import pprint
import uuid
import yaml

import attr
import yamlloader

# from ansible_galaxy.build import Build, BuildStatuses
# from ansible_galaxy import collection_info
from ansible_galaxy import installed_repository_db
from ansible_galaxy import matchers
from ansible_galaxy.models.shelf_index import ShelfIndex
from ansible_galaxy.models.shelf_collection_index import ShelfCollectionIndex
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

    repositories = []
    for candidate_repository in irdb.select(repository_match_filter=all_repository_match):
        log.debug('candidate_repo: %s', candidate_repository)

        repositories.append(candidate_repository)

    collection_index = ShelfCollectionIndex(collections=repositories)
    # TODO/FIXME: serial numbers are a PITA, maybe just a UUID

    shelf_serial_number = uuid.uuid4().int
    shelf_index = ShelfIndex(shelf_serial_number,
                             collection_index=collection_index)

    log.debug('shelf_index: %s', shelf_index)
    log.debug('shelf_index asdict: %s', pprint.pformat(attr.asdict(shelf_index)))

    # FIXME: extract and refactor to method in different module
    # write out the collection_index file
    # flush/save, get size and chksum return
    collection_index_file_path = os.path.join(shelf_creation_context.shelf_output_path,
                                              'collections.yml')
    try:
        with open(collection_index_file_path, 'w+') as collections_index_stream:
            dumpresult = yaml.dump(attr.asdict(collection_index),
                                   collections_index_stream,
                                   Dumper=yamlloader.ordereddict.CSafeDumper,
                                   default_flow_style=False)
            log.debug('yaml.dump result: %s', dumpresult)
    except Exception as e:
        log.exception(e)
        log.error('Unable to save collection index file (%s): %s', collection_index_file_path, e)

        raise

    # collection_index_file = ShelfCollectionIndexFile
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
