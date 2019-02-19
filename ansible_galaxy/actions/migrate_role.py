import logging
import os

log = logging.getLogger(__name__)


def migrate(migrate_role_context,
            display_callback):

    log.debug('migrate_role_context: %s', migrate_role_context)

    display_callback("migrate_role something")

    return os.EX_OK  # 0:
