import logging

import attr

log = logging.getLogger(__name__)


@attr.s(frozen=True)
class GalaxyContentMeta(object):
    namespace = attr.ib()
    name = attr.ib()
    version = attr.ib()
    content_type = attr.ib()
    src = attr.ib(default=None)
    scm = attr.ib(default=None)
    content_dir = attr.ib(default=None)
    path = attr.ib(default=None)
    requires_meta_main = attr.ib(default=None, cmp=False)
    content_sub_dir = attr.ib(default=None, cmp=False)

    @classmethod
    def from_data(cls, data):
        inst = cls(**data)
        return inst


class GalaxyContent(object):
    def __init__(self):
        # need class for obj for ansible-galaxy.yml metadata file
        self.galaxy_metadata = {}
        # or instance of some InstallInfo class
        self.install_info = {}
        # or instance of GalaxyContentMeta
        self.content_meta = {}
