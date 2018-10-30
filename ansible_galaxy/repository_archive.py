import datetime
import logging
import os
import tarfile

import attr

from ansible_galaxy import archive
from ansible_galaxy import exceptions
from ansible_galaxy import install_info
from ansible_galaxy.models import content
from ansible_galaxy.models.repository_archive import RepositoryArchiveInfo
from ansible_galaxy.models.install_info import InstallInfo
from ansible_galaxy.models.installation_results import InstallationResults

log = logging.getLogger(__name__)

# TODO: better place to define?
META_MAIN = os.path.join('meta', 'main.yml')
GALAXY_FILE = 'ansible-galaxy.yml'
APB_YAML = 'apb.yml'


def null_display_callback(*args, **kwargs):
    log.debug('display_callback: %s', args)


def extract(repository_spec,
            repository_archive_info,
            content_path,
            extract_archive_to_dir,
            tar_file,
            force_overwrite=False,
            display_callback=None):

    all_installed_paths = []

    # TODO: move to content info validate step in install states?
    if not repository_spec.namespace:
        # TODO: better error
        raise exceptions.GalaxyError('While installing a role , no namespace was found. Try providing one with --namespace')

    # label = "%s.%s" % (repository_namespace, repository_name)

    # 'extract_to_path' is for ex, ~/.ansible/content
    log.info('About to extract %s "%s" to %s', repository_archive_info.archive_type,
             repository_spec.label, content_path)
    display_callback('- extracting %s repository from "%s"' % (repository_archive_info.archive_type,
                                                               repository_spec.label))

    tar_members = tar_file.members

    # This assumes the first entry in the tar archive / tar members
    # is the top dir of the content, ie 'my_content_name-branch' for collection
    # or 'ansible-role-my_content-1.2.3' for a traditional role.
    parent_dir = tar_members[0].name

    # self.log.debug('content_dest_root_subpath: %s', content_dest_root_subpath)

    # self.log.debug('content_dest_root_path1: |%s|', content_dest_root_path)

    # TODO: need to support deleting all content in the dirs we are targetting
    #       first (and/or delete the top dir) so that we clean up any files not
    #       part of the content. At the moment, this will add or update the files
    #       that are in the archive, but it will not delete files on the fs that are
    #       not in the archive
    files_to_extract = []
    for member in tar_members:
        # rel_path ~  roles/some-role/meta/main.yml for ex
        rel_path = member.name[len(parent_dir) + 1:]

        extract_to_filename_path = os.path.join(extract_archive_to_dir, rel_path)

        # self.log.debug('content_dest_root_path: %s', content_dest_root_path)
        # self.log.debug('content_dest_root_rel_path: %s', content_dest_root_rel_path)

        files_to_extract.append({
            'archive_member': member,
            # Note: for trad roles, we are extract the top level of the archive into
            #       a sub path of the destination
            'dest_dir': extract_archive_to_dir,
            'dest_filename': extract_to_filename_path,
            'force_overwrite': force_overwrite})

    file_extractor = archive.extract_files(tar_file, files_to_extract)

    installed_paths = [x for x in file_extractor]
    install_datetime = datetime.datetime.utcnow()

    all_installed_paths.extend(installed_paths)

    log.info('Extracted %s files from %s %s to %s',
             len(all_installed_paths),
             repository_archive_info.archive_type,
             repository_spec.label,
             extract_archive_to_dir)

    # TODO: InstallResults object? installedPaths, InstallInfo, etc?
    return all_installed_paths, install_datetime


@attr.s()
class BaseRepositoryArchive(object):
    info = attr.ib(type=RepositoryArchiveInfo)
    tar_file = attr.ib(type=tarfile.TarFile, default=None)

    display_callback = attr.ib(default=null_display_callback)
    META_INSTALL = os.path.join('meta', '.galaxy_install_info')

    def __attrs_post_init__(self):
        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

    def repository_dest_root_subpath(self, repository_name):
        '''The relative path inside the installed content where extract should consider the root

        A collection archive for 'my_namespace.my_content' will typically be extracted to
        '~/.ansible/content/my_namespace/my_content' in which case the content_dest_root_subpath
        should return just '/'.

        But Role archives will be extracted into a 'roles' sub dir of the typical path.
        ie, a 'my_namespace.my_role' role archive will need to be extracted to
        '~/.ansible/content/my_namespace/roles/my_role/' in which case the content_dest_root_subpatch
        should return 'roles/my_roles' (ie, 'roles/%s' % content_name)
        '''
        return ''


@attr.s()
class TraditionalRoleRepositoryArchive(BaseRepositoryArchive):
    ROLES_SUBPATH = 'roles'

    def repository_dest_root_subpath(self, repository_name):
        '''Traditional role archive repository gets installed into subpath of 'roles/CONTENT_NAME/'''
        return os.path.join(self.ROLES_SUBPATH, repository_name)


@attr.s()
class CollectionRepositoryArchive(BaseRepositoryArchive):
    pass


def detect_repository_archive_type(archive_path, archive_members):
    '''Try to determine if we are a role, multi-content, apb etc.

    if there is a meta/main.yml ->  role

    if there is any of the content types subdirs -> multi-content'''

    # FIXME: just looking for the root dir...

    top_dir = archive_members[0].name

    log.debug('top_dir of %s: %s', archive_path, top_dir)

    meta_main_target = os.path.join(top_dir, 'meta/main.yml')

    type_dirs = content.CONTENT_TYPE_DIR_MAP.values()
    # log.debug('type_dirs: %s', type_dirs)

    type_dir_targets = set([os.path.join(top_dir, x) for x in type_dirs])
    log.debug('type_dir_targets: %s', type_dir_targets)

    for member in archive_members:
        if member.name == meta_main_target:
            return 'role'

    for member in archive_members:
        if member.name in type_dir_targets:
            return 'multi-content'

    # TODO: exception
    return None


def load_archive_info(archive_path):
    archive_parent_dir = None

    if not tarfile.is_tarfile(archive_path):
        raise exceptions.GalaxyClientError("the file downloaded was not a tar.gz")

    if archive_path.endswith('.gz'):
        repository_tar_file = tarfile.open(archive_path, "r:gz")
    else:
        repository_tar_file = tarfile.open(archive_path, "r")

    members = repository_tar_file.getmembers()

    archive_parent_dir = members[0].name

    archive_type = detect_repository_archive_type(archive_path, members)

    log.debug('archive_type of %s: %s', archive_path, archive_type)
    log.debug("archive_parent_dir of %s: %s", archive_path, archive_parent_dir)

    # looks like we are a role, update the default content_type from all -> role
    if archive_type == 'role':
        log.debug('Found role metadata in the archive %s, so installing it as role content_type',
                  archive_path)

    archive_info = RepositoryArchiveInfo(top_dir=archive_parent_dir,
                                         archive_type=archive_type,
                                         archive_path=archive_path)

    log.debug('role archive_info for %s: %s', archive_path, archive_info)

    return archive_info, repository_tar_file


def load_archive(archive_path):
    # To avoid opening the archive file twice, and since we have to open/load it to
    # get the archive_info, we also return it from load_archive_info
    archive_info, tar_file = load_archive_info(archive_path)

    # factory-ish
    if archive_info.archive_type in ['role']:
        repository_archive_ = TraditionalRoleRepositoryArchive(info=archive_info,
                                                               tar_file=tar_file)
    else:
        repository_archive_ = CollectionRepositoryArchive(info=archive_info,
                                                          tar_file=tar_file)

    log.debug('repository archive_ for %s: %s', archive_path, repository_archive_)

    return repository_archive_


def install(repository_archive, repository_spec, destination_info, display_callback):
    log.debug('saving repo archive %s to destination %s', repository_archive, destination_info)

    all_installed_files, install_datetime = extract(repository_spec,
                                                    repository_archive.info,
                                                    content_path=destination_info.destination_root_dir,
                                                    extract_archive_to_dir=destination_info.extract_archive_to_dir,
                                                    tar_file=repository_archive.tar_file,
                                                    display_callback=display_callback)

    install_info_ = InstallInfo.from_version_date(repository_spec.version,
                                                  install_datetime=install_datetime)

    # TODO: this save will need to be moved to a step later. after validating install?
    install_info.save(install_info_, destination_info.install_info_path)

    installation_results = InstallationResults(install_info_path=destination_info.install_info_path,
                                               install_info=install_info_,
                                               installed_to_path=destination_info.path,
                                               installed_datetime=install_datetime,
                                               installed_files=all_installed_files)
    return installation_results
