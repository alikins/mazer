import logging

import attr

log = logging.getLogger(__name__)


@attr.s(frozen=True)
class MigrateRoleContext(object):
    role_path = attr.ib()
    output_path = attr.ib()
