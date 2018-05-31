
import logging
import mock
import tempfile

from ansible_galaxy.actions import install
from ansible_galaxy.models.context import GalaxyContext

log = logging.getLogger(__name__)


def display_callback(msg, **kwargs):
    log.debug(msg)


def _galaxy_context():
    tmp_content_path = tempfile.mkdtemp()
    # FIXME: mock
    server = {'url': 'http://localhost:8000',
              'ignore_certs': False}
    return GalaxyContext(server=server, content_path=tmp_content_path)


def test_install_contents_empty_contents():
    contents = []

    galaxy_context = _galaxy_context()
    ret = install.install_contents(galaxy_context,
                                   requested_contents=contents,
                                   install_content_type='role',
                                   display_callback=display_callback)

    log.debug('ret: %s', ret)
    assert ret == 0


def test_install_contents():
    contents = [mock.Mock(content_type='role',
                          # FIXME: install bases update on install_info existing, so will fail for other content
                          install_info=None,
                          metadata={'content_type': 'role'})]

    galaxy_context = _galaxy_context()
    ret = install.install_contents(galaxy_context,
                                   requested_contents=contents,
                                   install_content_type='role',
                                   display_callback=display_callback)

    log.debug('ret: %s', ret)
    assert ret == 0


def test_install_contents_module():
    contents = [mock.Mock(content_type='module',
                          # FIXME: install bases update on install_info existing, so will fail for other content
                          install_info=None,
                          metadata={'content_type': 'module'})]

    galaxy_context = _galaxy_context()
    ret = install.install_contents(galaxy_context,
                                   requested_contents=contents,
                                   install_content_type='module',
                                   display_callback=display_callback)

    log.debug('ret: %s', ret)
    # assert ret == 0


def test_install_empty_content_specs():
    contents = []

    galaxy_context = _galaxy_context()
    ret = install.install_content_specs(galaxy_context,
                                        content_specs=contents,
                                        install_content_type='role',
                                        display_callback=display_callback)

    log.debug('ret: %s', ret)
    assert ret == 0


def test_install_malformed_content_specs():
    contents = ['blrp']

    galaxy_context = _galaxy_context()
    ret = install.install_content_specs(galaxy_context,
                                        content_specs=contents,
                                        install_content_type='role',
                                        display_callback=display_callback)

    log.debug('ret: %s', ret)
    assert ret == 0


def test_install_content_specs():
    contents = ['alikins.testing-content']

    galaxy_context = _galaxy_context()
    ret = install.install_content_specs(galaxy_context,
                                        content_specs=contents,
                                        install_content_type='role',
                                        display_callback=display_callback)

    log.debug('ret: %s', ret)
    assert ret == 0


def test_install_bogus_content_specs():
    contents = ['alikins.not-a-real-thing']

    galaxy_context = _galaxy_context()
    ret = install.install_content_specs(galaxy_context,
                                        content_specs=contents,
                                        install_content_type='role',
                                        display_callback=display_callback)

    log.debug('ret: %s', ret)
    assert ret == 1
