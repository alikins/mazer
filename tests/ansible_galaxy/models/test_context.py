
import logging

import pytest
import six


from ansible_galaxy.models import GalaxyContext

log = logging.getLogger(__name__)


def test_context_empty_init_raise_type_error():
    with pytest.raises(TypeError):
        GalaxyContext()


def test_context_with_content_path_and_server():
    content_path = '/dev/null/some_content_path'
    server_url = 'http://example.com:9999/'
    ignore_certs = False

    server = {'url': server_url,
              'ignore_certs': ignore_certs}

    galaxy_context = GalaxyContext(server=server, content_path=content_path)

    log.debug('galaxy_context: %s', galaxy_context)
    assert isinstance(galaxy_context, GalaxyContext)

    assert isinstance(galaxy_context.content_path, six.string_types)
    assert isinstance(galaxy_context.server, dict)

    assert galaxy_context.server['url'] == server_url
    assert galaxy_context.server['ignore_certs'] == ignore_certs

    assert galaxy_context.content_path == content_path


def test_context_from_empty_server():
    content_path = '/dev/null/some_content_path'

    server = {}

    with pytest.raises(ValueError):
        GalaxyContext(content_path=content_path,
                      server=server)


def test_context_server_none_content_path_none():

    with pytest.raises(TypeError):
        GalaxyContext(content_path=None,
                      server=None)

    return


def test_context_repr():
    content_path = '/dev/null/some_content_path'
    server_url = 'http://example.com:9999/'
    ignore_certs = False

    server = {'url': server_url,
              'ignore_certs': ignore_certs}

    galaxy_context = GalaxyContext(server=server, content_path=content_path)
    rep_res = repr(galaxy_context)

    log.debug('rep_res: %s', rep_res)

    assert isinstance(rep_res, six.string_types)
    assert 'content_path' in rep_res
    assert 'server' in rep_res
    assert 'some_content_path' in rep_res
