import logging
import os

log = logging.getLogger(__name__)


def migrate(collection_output_dir,
            display_callback):

    display_callback("migrate_role something")
    return os.EX_OK  # 0
