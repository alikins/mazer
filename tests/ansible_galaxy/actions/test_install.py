
import logging
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


def test_install_empty_contents():
    contents = []

    galaxy_context = _galaxy_context()
    ret = install.install(galaxy_context,
                          contents=contents,
                          install_content_type='role',
                          display_callback=display_callback)

    log.debug('ret: %s', ret)


def test_install_contents():
    contents = ['alikins.testing-content']

    galaxy_context = _galaxy_context()
    ret = install.install(galaxy_context,
                          contents=contents,
                          install_content_type='role',
                          display_callback=display_callback)

    log.debug('ret: %s', ret)
