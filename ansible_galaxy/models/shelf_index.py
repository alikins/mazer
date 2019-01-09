import attr
import logging

from ansible_galaxy.models.shelf_collection_index import ShelfCollectionIndex, ShelfCollectionIndexFileInfo

log = logging.getLogger(__name__)

# Note we may end up with DTO which may be slightly different than
# a 'Shelf' or 'ShelfInfo' that m


@attr.s(frozen=True)
class ShelfIndex(object):
    # revision?
    serial_number = attr.ib(type=int)

    collection_index = attr.ib(type=ShelfCollectionIndex)


@attr.s(frozen=True)
class ShelfIndexFile(object):
    # name? label? nickname? namespace?
    # version?... but semver is likely not to be sufficient or meaningful
    # for a shelf version

    # revision?
    serial_number = attr.ib(type=int)

    # some uuid?
    collection_index_file_info = attr.ib(type=ShelfCollectionIndexFileInfo)
