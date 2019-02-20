from collections import OrderedDict

import logging
import os

from ansible_galaxy import role_metadata
from ansible_galaxy.models.collection_info import CollectionInfo

log = logging.getLogger(__name__)


def migrate(migrate_role_context,
            display_callback):

    log.debug('migrate_role_context: %s', migrate_role_context)

    display_callback("migrate_role something")

    # validate paths

    # load role from migrate_role_context.role_path
    # though, that may be just loading the role_path/meta/main.yml

    dir_basename = os.path.basename(os.path.normpath(migrate_role_context.role_path))
    log.debug('dir_basename: %s', dir_basename)

    name_parts = dir_basename.split('.', 1)
    log.debug('name_parts: %s', name_parts)

    role_name = name_parts[0]
    role_namespace = None

    if len(name_parts) == 2:
        role_namespace = name_parts[0]
        role_name = name_parts[1]

    role_name = migrate_role_context.role_name or role_name

    collection_name = migrate_role_context.collection_name or role_name
    collection_namespace = migrate_role_context.collection_namespace or role_namespace

    log.debug('role_name: %s mrc.role_name: %s dir_basename: %s name_parts: %s',
              role_name, migrate_role_context.role_name, dir_basename, name_parts)

    role_md = role_metadata.load_from_dir(migrate_role_context.role_path,
                                          role_name=migrate_role_context.role_name)

    log.debug('role_metadata: %s', role_md)

    #  maybe some file tree walking

    # (or just let CollectionInfo construct fail...)
    # verify/validate namespace and names are valid for collections
    # verify version number is valid for collection

    # create/populate dicts for collection_info
    # fill in namespace, name, version, deps, tags, etc

    # FIXME: license format is different, will have to map
    collection_info_dict = OrderedDict([
        # TODO: namespace, name
        ('namespace', collection_namespace),
        ('name', collection_name),
        ('version', migrate_role_context.collection_version),
        ('license', role_md.license),
        ('description', role_md.description),
        # FIXME: verify role_md.author is a list or single
        ('authors', [role_md.author]),
        ('tags', role_md.galaxy_tags),
        ('issues', role_md.issue_tracker),
        ('dependencies', role_md.dependencies)
    ])

    log.debug('collection_info_dict: %s', collection_info_dict)
    # create a CollectionInfo
    col_info = CollectionInfo(**collection_info_dict)

    log.debug('col_info: %s', col_info)

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


def _migrate(migrate_role_context, display_callback):
    pass
