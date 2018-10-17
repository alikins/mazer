
import logging
import mock
import tempfile

from ansible_galaxy.actions import install
from ansible_galaxy import exceptions
from ansible_galaxy.models.content import InstalledContent
from ansible_galaxy.models.context import GalaxyContext
from ansible_galaxy.models.role_metadata import RoleMetadata

log = logging.getLogger(__name__)


def display_callback(msg, **kwargs):
    log.debug(msg)


def _galaxy_context():
    tmp_content_path = tempfile.mkdtemp()
    # FIXME: mock
    server = {'url': 'http://localhost:8000',
              'ignore_certs': False}
    return GalaxyContext(server=server, content_path=tmp_content_path)


def test_install_contents_empty_contents(galaxy_context):
    contents = []

    ret = install.install_collections(galaxy_context,
                                      content_specs_to_install=contents,
                                      display_callback=display_callback)

    log.debug('ret: %s', ret)
    assert isinstance(ret, list)
    assert ret == []


# TODO: replace InstalledContent with @attr thing, then shouldn't need a mock
def test_install_collections(galaxy_context):
    needed_deps = ['some_namespace.some_name']
    mock_role_metadata = RoleMetadata(name='some_role', dependencies=needed_deps)
    mock_installed = [mock.Mock(name='a mock InstalledCollection maybe',
                                spec=InstalledContent,
                                metadata=mock_role_metadata)]
    contents = [mock.Mock(content_type='role',
                          # FIXME: install bases update on install_info existing, so will fail for other content
                          install_info=None,
                          install=mock.Mock(return_value=mock_installed),
                          metadata={'content_type': 'role'})]

    ret = install.install_collections(galaxy_context,
                                      content_specs_to_install=contents,
                                      display_callback=display_callback)

    log.debug('ret: %s', ret)
    assert isinstance(ret, list)
    assert ret == needed_deps


def test_install_collections_no_deps_required(galaxy_context):
    needed_deps = []
    mock_role_metadata = RoleMetadata(name='some_role', dependencies=needed_deps)
    mock_installed = [mock.Mock(name='a mock InstalledCollection maybe',
                                spec=InstalledContent,
                                metadata=mock_role_metadata)]
    contents = [mock.Mock(content_type='role',
                          # FIXME: install bases update on install_info existing, so will fail for other content
                          install_info=None,
                          install=mock.Mock(return_value=mock_installed),
                          metadata={'content_type': 'role'})]

    ret = install.install_collections(galaxy_context,
                                      content_specs_to_install=contents,
                                      display_callback=display_callback)

    log.debug('ret: %s', ret)
    assert isinstance(ret, list)
    assert ret == needed_deps


def test_verify_content_specs_have_namespace_empty(galaxy_context):
    ret = install._verify_content_specs_have_namespace([])

    log.debug('ret: %s', ret)
    assert isinstance(ret, list)
    assert ret == []


# even though 'blrp' isnt a valid spec, _build_content_set return something for now
def test_verify_content_specs_have_namespace(galaxy_context):
    content_spec = mock.Mock(namespace=None)
    try:
        install._verify_content_specs_have_namespace([content_spec])
    except exceptions.GalaxyError as e:
        log.exception(e)
        return

    assert False, 'Expected a GalaxyError to be raised here since the content_spec %s has no namespace or dots' % content_spec
