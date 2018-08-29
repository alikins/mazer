import logging

from ansible_galaxy.models import RoleMetadata

import attr

log = logging.getLogger(__name__)


def test_init_empty():
    role_md = RoleMetadata()

    log.debug('role_md: %s', role_md)

    assert isinstance(role_md, RoleMetadata)


def test_basic():
    role_md = RoleMetadata(name='some_role',
                           author='alikins@redhat.com',
                           description='some role that does stuff',
                           company='Red Hat',
                           license='GPLv3',
                           galaxy_tags=['stuff', 'nginx', 'system', 'devel'])

    log.debug('role_md: %s', role_md)
    assert isinstance(role_md, RoleMetadata)

    assert role_md.name == 'some_role'
    assert role_md.author == 'alikins@redhat.com'
    assert 'stuff' in role_md.galaxy_tags
    assert isinstance(role_md.galaxy_tags, list)
    assert role_md.allow_duplicates is False


def test_equal():
    role_md1 = RoleMetadata(name='some_role')
    role_md1a = RoleMetadata(name='some_role')
    role_md2 = RoleMetadata(name='a_different_role')

    assert role_md1 == role_md1a
    assert role_md1a == role_md1

    assert not role_md1 == role_md2
    assert not role_md2 == role_md1

    assert role_md1 != role_md2
    assert role_md2 != role_md1


def test_asdict():
    role_md = RoleMetadata(name='some_role',
                           author='alikins@redhat.com',
                           description='some role that does stuff',
                           company='Red Hat',
                           license='GPLv3',
                           galaxy_tags=['stuff', 'nginx', 'system', 'devel'])

    log.debug('role_md: %s', role_md)
    role_dict = attr.asdict(role_md)

    assert isinstance(role_dict, dict)
    assert role_dict['name'] == role_md.name == 'some_role'
    assert role_dict['galaxy_tags'] == role_md.galaxy_tags == ['stuff', 'nginx', 'system', 'devel']
