import logging

import attr

log = logging.getLogger(__name__)


@attr.s(frozen=True)
class BuildContext(object):
    collection_path = attr.ib()
    output_path = attr.ib()


# see https://github.com/ansible/galaxy/issues/957
@attr.s(frozen=True)
class CollectionArtifactFile(object):
    name = attr.ib()
    ftype = attr.ib()
    src_name = attr.ib(default=None)
    chksum_type = attr.ib(default="sha256")
    chksum_sha256 = attr.ib(default=None)
    # name = attr.ib(default=None)
    format_version = attr.ib(default=0.0)


# see https://github.com/ansible/galaxy/issues/957
@attr.s(frozen=True)
class CollectionInfo(object):
    namespace = attr.ib()
    name = attr.ib()
    version = attr.ib()
    format_version = attr.ib(default=0.0)
    author = attr.ib(default=None)
    license = attr.ib(default=None)


# TODO: static method of CollectionArtifactFile?
def convert_file_dict_list_to_artifact_file_list(val):
    '''Convert a list of dicts with file info into list of CollectionArtifactFile'''

    new_list = []
    for file_item in val:
        if isinstance(file_item, CollectionArtifactFile):
            new_list.append(file_item)
        else:
            artifact_file = CollectionArtifactFile(name=file_item['name'],
                                                   ftype=file_item['ftype'],
                                                   chksum_type=file_item.get('chksum_type'),
                                                   chksum_sha256=file_item.get('chksum_sha256'))
            new_list.append(artifact_file)

    return new_list


# see https://github.com/ansible/galaxy/issues/957
@attr.s(frozen=True)
class CollectionArtifactManifest(object):
    collection_info = attr.ib(type=CollectionInfo)
    format_version = attr.ib(default=0.0)

    files = attr.ib(factory=list, converter=convert_file_dict_list_to_artifact_file_list)

    # a build_info = attr.ib(type=CollectionArtifactBuildInfo)
    #   CollectionArtifactBuildInfo has 'build_date', 'build_tool'
    # created_with =
    # when/build_date =


@attr.s(frozen=True)
class ContentArchiveMeta(object):
    requires_meta_main = False

    archive_type = attr.ib()
    top_dir = attr.ib()
    archive_path = attr.ib(default=None)

    # download url?
    # file path?
    # checksum?
    # signature?


@attr.s(frozen=True)
class ContentSpec(object):
    '''The info used to identify and reference a galaxy content.

    For ex, 'testing.ansible-testing-content' will result in
    a ContentSpec(name=ansible-testing-content, repo=ansible-testing-content,
                  namespace=testing, raw=testing.ansible-testing-content)'''
    namespace = attr.ib()
    name = attr.ib()
    version = attr.ib(default=None)

    # only namespace/name/version are used for eq checks
    fetch_method = attr.ib(default=None, cmp=False)
    scm = attr.ib(default=None, cmp=False)
    spec_string = attr.ib(default=None, cmp=False)
    src = attr.ib(default=None, cmp=False)

    @property
    def label(self):
        return '%s.%s' % (self.namespace, self.name)


@attr.s(frozen=True)
class ContentRepository(object):
    content_spec = attr.ib(type=ContentSpec)
    path = attr.ib(default=None)
    installed = attr.ib(default=False, type=bool, cmp=False)


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

# TODO:
# class GalaxyContent(object):
#    def __init__(self):
#        # need class for obj for ansible-galaxy.yml metadata file
#        self.galaxy_metadata = {}
#        # or instance of some InstallInfo class
#        self.install_info = {}
#        # or instance of GalaxyContentMeta
#        self.content_meta = {}