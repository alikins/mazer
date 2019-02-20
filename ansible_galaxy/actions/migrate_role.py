import logging
import os

from ansible_galaxy import role_metadata

log = logging.getLogger(__name__)


def migrate(migrate_role_context,
            display_callback):

    log.debug('migrate_role_context: %s', migrate_role_context)

    display_callback("migrate_role something")

    # validate paths

    # load role from migrate_role_context.role_path
    # though, that may be just loading the role_path/meta/main.yml

    role_md = role_metadata.load_from_dir(migrate_role_context.role_path,
                                          role_name=migrate_role_context.role_name)

    log.debug('role_metadata: %s', role_md)

    #  maybe some file tree walking

    # (or just let CollectionInfo construct fail...)
    # verify/validate namespace and names are valid for collections
    # verify version number is valid for collection

    # create/populate dicts for collection_info
    # fill in namespace, name, version, deps, tags, etc

    # create a CollectionInfo

    # hmmm... should probably have a Collection/Repository save()
    # support, but if not, do the equiv

    # create any needed dirs in output_path/

    # persist CollectionInfo to output_path/galaxy.yml

    # cp role_path/role_stuff* dirs to output_path
    # TODO: should we migrate plugins and modules to be collection level
    #       or just keep the role level?

    # TODO: if there are modules or plugins using a bundled module_utils
    #       just moving the plugins isnt enough since the source code itself
    #       will need to be updated to use new plugin loader style paths

    # display any collected errors or messages
    # display the output path, maybe some summary of the migration results

    return os.EX_OK  # 0:
