import logging
import pytest

from ansible_galaxy.models.collection_info import CollectionInfo

log = logging.getLogger(__name__)


def test_no_license():
    test_data = {
        'name': 'foo.foo',
        'authors': ['alikins'],
        'version': '0.0.1',
        'description': 'unit testing thing',
    }
    with pytest.raises(ValueError) as exc:
        CollectionInfo(**test_data)
    assert 'license' in str(exc)


def test_null_license():
    test_data = {
        'name': 'foo.foo',
        'authors': ['alikins'],
        'version': '0.0.1',
        'license': None,
        'description': 'unit testing thing',
    }
    with pytest.raises(ValueError) as exc:
        CollectionInfo(**test_data)
    assert 'license' in str(exc)


def test_license_error():
    test_data = {
        'name': 'foo.foo',
        'authors': ['chouseknecht'],
        # 'GPLv2' is not a valid SPDX id so this
        # raises an error. A valid id would be 'GPL-2.0-or-later'
        'license': 'GPLv2',
        'version': '0.0.1',
        'description': 'unit testing thing',
    }
    coll_info = CollectionInfo(**test_data)
    assert coll_info.license == 'GPLv2'


def test_required_error():
    test_data = {
        'authors': ['chouseknecht'],
        'license': 'GPL-3.0-or-later',
        'version': '0.0.1',
        'description': 'unit testing thing'
    }
    with pytest.raises(ValueError) as exc:
        CollectionInfo(**test_data)
    assert 'name' in str(exc) in str(exc)


def test_name_parse_error():
    test_data = {
        'name': 'foo',
        'authors': ['chouseknecht'],
        'license': 'GPL-3.0-or-later',
        'version': '0.0.1',
        'description': 'unit testing thing'
    }
    with pytest.raises(ValueError) as exc:
        CollectionInfo(**test_data)
    assert 'name' in str(exc)


def test_type_list_error():
    test_data = {
        'name': 'foo.foo',
        'authors': 'chouseknecht',
        'license': 'GPL-3.0-or-later',
        'version': '0.0.1',
        'description': 'unit testing thing',
    }
    with pytest.raises(ValueError) as exc:
        CollectionInfo(**test_data)
    assert 'authors' in str(exc)


def test_semantic_version_error():
    test_data = {
        'name': 'foo.foo',
        'authors': ['chouseknecht'],
        'license': 'GPL-3.0-or-later',
        'version': 'foo',
        'description': 'unit testing thing',
    }
    with pytest.raises(ValueError) as exc:
        CollectionInfo(**test_data)
    assert 'version' in str(exc)


def test_namespace_property():
    test_data = {
        'name': 'foo.foo',
        'authors': ['chouseknecht'],
        'license': 'GPL-3.0-or-later',
        'version': '1.0.0',
        'description': 'unit testing thing',
    }
    info = CollectionInfo(**test_data)
    assert info.namespace == 'foo'
