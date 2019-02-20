import logging

import attr

log = logging.getLogger(__name__)


@attr.s(frozen=True)
class MigrateRoleContext(object):
    role_path = attr.ib()
    output_path = attr.ib()

    # roles always have a name, but not a namespace
    role_name = attr.ib(default=None)

    # collections always have namespace and name
    collection_namespace = attr.ib(default=None)
    collection_name = attr.ib(default=None)
    collection_version = attr.ib(default=None)
