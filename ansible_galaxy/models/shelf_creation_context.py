import logging

import attr

log = logging.getLogger(__name__)


@attr.s(frozen=True)
class ShelfCreationContext(object):
    collections_path = attr.ib()
    shelf_output_path = attr.ib()
