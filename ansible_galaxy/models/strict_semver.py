import logging
import re

# import attr
import semver

log = logging.getLogger(__name__)


# @attr.s(frozen=True)

# So we dont have to specify loose=False everytime we use
# SemVer or Range

class StrictSemVer(semver.SemVer):
    def __init__(self, version):
        super(StrictSemVer, self).__init__(version, loose=False)


class StrictRange(semver.Range):
    def __init__(self, range_, _split_rx=re.compile(r"\s*\|\|\s*")):
        super(StrictRange, self).__init__(range_, False, _split_rx)
