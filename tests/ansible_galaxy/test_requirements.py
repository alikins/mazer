import logging

from semantic_version import Version, Spec

from ansible_galaxy import requirements
from ansible_galaxy.models.requirement import Requirement
from ansible_galaxy.models.requirement_spec import RequirementSpec

log = logging.getLogger(__name__)


def test_from_dependencies_dict_empty():
    dep_dict = {}
    res = requirements.from_dependencies_dict(dep_dict)

    log.debug('res: %s', res)

    assert isinstance(res, list)


def test_from_dependencies_dict():
    dep_dict = {'alikins.some_collection': '>=1.0.0',
                'testuser.another': '==0.6.6',
                'shrug.whatever': '*'}
    res = requirements.from_dependencies_dict(dep_dict)

    log.debug('res: %s', res)

    assert isinstance(res, list)
    for req in res:
        assert isinstance(req, Requirement)

    log.debug('res[0]: %s', res[0])
    assert isinstance(res[0].requirement_spec, RequirementSpec)
    assert res[0].requirement_spec.namespace == 'alikins'
    assert res[0].requirement_spec.name == 'some_collection'
    assert res[0].requirement_spec.version_spec == Spec('>=1.0.0')
    assert res[0].requirement_spec.version_spec.match(Version('1.0.0'))
    assert res[0].requirement_spec.version_spec.match(Version('1.2.0'))
    assert not res[0].requirement_spec.version_spec.match(Version('0.0.37'))


def test_requirements_from_strings():
    # TODO: tests for local file, remote url, etc
    res = requirements.requirements_from_strings(['alikins.some_collection',
                                                  'alikins.picky,1.2.3',
                                                  'alikins.picky,version=3.4.5',
                                                  'testuser.another',
                                                  # FIXME: '=' and ',' in version spec
                                                  # freaks out cli parser
                                                  # 'testuser.picky,version="!=3.1.4,>=3.0.0"',
                                                  ])

    log.debug('res: %s', res)

    assert isinstance(res, list)
    reqs = [req for req in res]
    for req in reqs:
        assert isinstance(req, Requirement)

    namespaces = [x.requirement_spec.namespace for x in res]
    assert 'alikins' in namespaces
    assert 'testuser' in namespaces
    assert res[0].requirement_spec.namespace == 'alikins'
    assert res[0].requirement_spec.name == 'some_collection'
    assert res[0].requirement_spec.version_spec == Spec('*')

    assert res[1].requirement_spec.namespace == 'alikins'
    assert res[1].requirement_spec.name == 'picky'
    assert res[1].requirement_spec.version_spec == Spec('==1.2.3')

    assert res[2].requirement_spec.namespace == 'alikins'
    assert res[2].requirement_spec.name == 'picky'
    assert res[2].requirement_spec.version_spec == Spec('==3.4.5')
