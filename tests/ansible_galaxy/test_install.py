
import logging
import pprint

import pytest

from ansible_galaxy import exceptions
from ansible_galaxy import install
from ansible_galaxy.models.repository import Repository
from ansible_galaxy.models.repository_spec import RepositorySpec

log = logging.getLogger(__name__)
pf = pprint.pformat


def display_callback(msg, **kwargs):
    log.debug(msg)


def test_install_no_valid_content(galaxy_context, mocker):
    repo_spec = RepositorySpec(namespace='some_namespace',
                               name='some_name',
                               version='4.3.2')

    mock_fetcher = mocker.MagicMock(name='MockFetch')
    fetch_results = {}

    with pytest.raises(exceptions.GalaxyClientError, match='No valid content data found for') as exc_info:
        install.install(galaxy_context,
                        fetcher=mock_fetcher,
                        fetch_results=fetch_results,
                        repository_spec=repo_spec,
                        display_callback=display_callback)
    log.debug('exc_info: %s', exc_info)
    # log.debug('res: %s', res)


def test_install(galaxy_context, mocker):
    repo_spec = RepositorySpec(namespace='some_namespace',
                               name='some_name',
                               version='4.3.2')

    mock_fetcher = mocker.MagicMock(name='MockFetch')
    fetch_results = {'archive_path': '/dev/null/doesntexist'}

    # Mock args for creating a Mock to replace repository_archive.load_archive
    # TODO: the 'config' constructor can be replaced with straight mocker.patch?
    config = {'return_value': mocker.MagicMock(name='MockRepoArchive')}

    mocker.patch.object(install.repository_archive, 'load_archive', **config)

    res = install.install(galaxy_context,
                          fetcher=mock_fetcher,
                          fetch_results=fetch_results,
                          repository_spec=repo_spec,
                          display_callback=display_callback)
    log.debug('res: %s', res)

    assert isinstance(res, list)
    assert len(res) > 0
    assert isinstance(res[0], Repository)
    assert res[0].repository_spec == repo_spec
    assert galaxy_context.collections_path in res[0].path
