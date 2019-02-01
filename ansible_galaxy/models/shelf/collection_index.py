import datetime
import logging

import attr

log = logging.getLogger(__name__)


@attr.s(frozen=True)
class ShelfCollectionIndex(object):
    collections = attr.ib(default=tuple)


# Based on yum repo metadata 'repomd.xml'

@attr.s(frozen=True)
class ShelfCollectionIndexFileInfo(object):
    '''Info and metadata about a shelf collection index file'''
    # url/uri, filepath, etc? could be relative or absolute
    # TODO: validation of location string
    location = attr.ib()

    # "collections", "roles", whatever high level content types we index
    index_type = attr.ib()

    # serialized to serializers formats datetime, for ex
    # JSON Date (just a string with iso8601 format)
    timestamp = attr.ib(type=datetime.datetime)

    # file size in bytes of the collections index file uncompressed
    size_bytes = attr.ib(type=int)

    # dont change chksum_type in constructor, it's here to allow
    # other checksum types in the future
    chksum_type = attr.ib(default="sha256")

    # checksum of collections index file uncompressed
    chksum_sha256 = attr.ib(default=None)

    # IIRC, the reason for checksums of both compressed and uncompressed versions
    # was to allow compressed versions to be verifies before uncompressing to avoid
    # compression bomb problems.

    # checksum of collections index file compressed if it is optionally compressed
    compressed_chksum_sha256 = attr.ib(default=None)

    # file size in bytes of the collections index file compressed if it
    # is optionally compressed
    compressed_size_bytes = attr.ib(type=int, default=None)

    # TODO: Instead of one file location string has implicit meaning (ie, a '.gz' means it is
    # compressed), should there be a main location and a sub list
    # of explicit alternate versions (ie, compressed copies)
