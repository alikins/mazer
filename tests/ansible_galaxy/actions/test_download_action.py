import logging
import os

import pytest

from ansible_galaxy.actions import download

log = logging.getLogger(__name__)


def logging_display_callback(msg, **kwargs):
    log.debug(msg)


@pytest.fixture
def display_callback(mocker):
    mock_display_callback = mocker.MagicMock(wraps=logging_display_callback)
    return mock_display_callback


def test_download_empty(galaxy_context, display_callback, tmpdir):
    temp_dir = tmpdir.mkdir('mazer_download_action_unit_test')
    res = download.download(galaxy_context,
                            [],
                            full_destination_path=temp_dir.strpath,
                            display_callback=display_callback)

    log.debug('res: %s', res)
    log.debug('display_callback.call_args_list: %s', display_callback.call_args_list)

    assert isinstance(res, dict)


def test_run_empty(galaxy_context, mocker, display_callback):
    mocker.patch('ansible_galaxy.actions.download.download',
                 return_value={'errors': ['alright I guess'],
                               'success': True})

    res = download.run(galaxy_context,
                       requirement_spec_strings=[],
                       display_callback=display_callback)

    log.debug('res: %s', res)
    log.debug('display_callback.call_args_list: %s', display_callback.call_args_list)

    assert res == os.EX_OK  # 0
    assert mocker.call('alright I guess') in display_callback.call_args_list


def test_run(galaxy_context, mocker, display_callback):
    mocker.patch('ansible_galaxy.actions.download.download',
                 return_value={'errors': ['alright I guess'],
                               'success': True})

    res = download.run(galaxy_context,
                       requirement_spec_strings=['alikins.whatever'],
                       display_callback=display_callback)

    log.debug('res: %s', res)
    log.debug('display_callback.call_args_list: %s', display_callback.call_args_list)

    assert res == os.EX_OK  # 0
    assert mocker.call('alright I guess') in display_callback.call_args_list


def test_run_error(galaxy_context, mocker, display_callback):
    mocker.patch('ansible_galaxy.actions.download.download',
                 return_value={'errors': ['bad!'],
                               'success': False})

    res = download.run(galaxy_context,
                       requirement_spec_strings=[],
                       display_callback=display_callback)

    log.debug('res: %s', res)
    log.debug('display_callback.call_args_list: %s', display_callback.call_args_list)

    assert res == os.EX_SOFTWARE
    assert mocker.call('bad!') in display_callback.call_args_list
