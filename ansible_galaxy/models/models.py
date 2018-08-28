import logging

import attr

log = logging.getLogger(__name__)


@attr.s(frozen=True)
class BuildContext(object):
    collection_path = attr.ib()
    output_path = attr.ib()


# see https://github.com/ansible/galaxy/issues/957
@attr.s(frozen=True)
class CollectionArtifactFile(object):
    name = attr.ib()
    ftype = attr.ib()
    src_name = attr.ib(default=None)
    chksum_type = attr.ib(default="sha256")
    chksum_sha256 = attr.ib(default=None)
    # name = attr.ib(default=None)
    format_version = attr.ib(default=0.0)


# see https://github.com/ansible/galaxy/issues/957
@attr.s(frozen=True)
class CollectionInfo(object):
    namespace = attr.ib()
    name = attr.ib()
    version = attr.ib()
    format_version = attr.ib(default=0.0)
    author = attr.ib(default=None)
    license = attr.ib(default=None)
