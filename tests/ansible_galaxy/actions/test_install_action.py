import logging
import mock

from ansible_galaxy.actions import install
from ansible_galaxy import exceptions
from ansible_galaxy import repository_spec
from ansible_galaxy import requirements
from ansible_galaxy.models.repository import Repository
from ansible_galaxy.models.repository_spec import RepositorySpec
from ansible_galaxy.models.requirement import Requirement, RequirementOps
from ansible_galaxy.models.requirement_spec import RequirementSpec

log = logging.getLogger(__name__)


def display_callback(msg, **kwargs):
    log.debug(msg)


def test_requirements_from_strings():
    res = install.requirements_from_strings(['alikins.some_collection',
                                             'testuser.another'])

    log.debug('res: %s', res)

    assert isinstance(res, list)
    reqs = [req for req in res]
    for req in reqs:
        assert isinstance(req, Requirement)

    namespaces = [x.requirement_spec.namespace for x in res]
    assert 'alikins' in namespaces
    assert 'testuser' in namespaces


def test_install_requirements(galaxy_context, mocker):
    mock_irdb = mocker.patch('ansible_galaxy.actions.install.installed_repository_db.InstalledRepositoryDatabase',
                             name='the_mock_irdb')
    mock_irdb2 = mocker.patch('ansible_galaxy.installed_repository_db.InstalledRepositoryDatabase',
                              name='the_mock_irdb2')

    repo_spec = RepositorySpec(namespace='alikins', name='some_collection',
                               version='4.2.1')
    repo = Repository(repository_spec=repo_spec, installed=True)

    mock_irdb.select.return_value = [repo]
    mock_irdb.by_requirement_spec.return_value = [repo]
    mock_irdb2.select.return_value = [repo]
    mock_irdb2.by_requirement_spec.return_value = [repo]

    log.debug('mock_irdb %s', mock_irdb)
    #              return_value=iter(['bar', 'baz']))

    requirements = install.requirements_from_strings(['alikins.some_collection',
                                                      'testuser.another'])

    log.debug('requirements: %s', requirements)

    res = install.install_requirements(galaxy_context,
                                       requirements,
                                       display_callback=None,
                                       ignore_errors=False,
                                       no_deps=False,
                                       force_overwrite=True)

    log.debug('res: %s', res)


def test_install_repos_empty_requirements(galaxy_context):
    requirements_to_install = []

    ret = install.install_repositories(galaxy_context,
                                       requirements_to_install=requirements_to_install,
                                       display_callback=display_callback)

    log.debug('ret: %s', ret)

    assert isinstance(ret, list)
    assert ret == []


def test_install_repositories(galaxy_context, mocker):
    repo_spec = RepositorySpec(namespace='some_namespace', name='some_name',
                               version='9.4.5')
    expected_repos = [Repository(repository_spec=repo_spec)]

    requirements_to_install = \
        requirements.from_dependencies_dict({'some_namespace.this_requires_some_name': '*'})

    mocker.patch('ansible_galaxy.actions.install.install_repository',
                 return_value=expected_repos)

    ret = install.install_repositories(galaxy_context,
                                       requirements_to_install=requirements_to_install,
                                       display_callback=display_callback)

    log.debug('ret: %s', ret)

    assert isinstance(ret, list)
    assert ret == expected_repos


def test_install_repository_deprecated(galaxy_context, mocker):
    requirements_to_install = \
        requirements.from_dependencies_dict({'some_namespace.this_requires_some_name': '*'})

    find_results = {'content': {'galaxy_namespace': 'some_namespace',
                                'repo_name': 'some_name'},
                    'custom': {'repo_data': {},
                               'download_url': 'http://foo.invalid/stuff/blip.tar.gz',
                               'repoversion': {'version': '9.3.245'},
                               'collection_is_deprecated': True,
                               },
                    }

    mocker.patch('ansible_galaxy.actions.install.install.find',
                 return_value=find_results)
    mocker.patch('ansible_galaxy.actions.install.install.fetch')
    mocker.patch('ansible_galaxy.actions.install.install.install')

    mock_display_callback = mocker.MagicMock(name='mock_display_callback')

    ret = install.install_repository(galaxy_context,
                                     requirement_to_install=requirements_to_install[0],
                                     display_callback=mock_display_callback)

    expected_display_calls = mocker.call("The collection 'some_namespace.this_requires_some_name' is deprecated.", level='warning')

    log.debug('ret: %s', ret)

    assert expected_display_calls in mock_display_callback.call_args_list


def test_install_repositories_no_deps_required(galaxy_context, mocker):
    needed_deps = []

    repository_specs_to_install = \
        [repository_spec.repository_spec_from_string('some_namespace.this_requires_nothing')]

    # mock out install_repository
    mocker.patch('ansible_galaxy.actions.install.install_repository',
                 return_value=[])

    ret = install.install_repositories(galaxy_context,
                                       requirements_to_install=repository_specs_to_install,
                                       display_callback=display_callback)

    log.debug('ret: %s', ret)

    assert isinstance(ret, list)
    assert ret == needed_deps


def test_verify_repository_specs_have_namespace_empty(galaxy_context):
    # will throw an exception if busted
    install._verify_requirements_repository_spec_have_namespaces([])


# even though 'blrp' isnt a valid spec, _build_content_set return something for now
def test_verify_repository_specs_have_namespace(galaxy_context):
    repository_spec = mock.Mock(requirement_spec=mock.Mock(namespace=None))
    try:
        install._verify_requirements_repository_spec_have_namespaces([repository_spec])
    except exceptions.GalaxyError as e:
        log.exception(e)
        return

    assert False, 'Expected a GalaxyError to be raised here since the repository_spec %s has no namespace or dots' % repository_spec


def test_find_new_deps_from_installed_no_deps(galaxy_context):
    res = install.find_new_deps_from_installed(galaxy_context, [], no_deps=True)
    assert res == []


def test_find_new_deps_from_installed_nothing_installed(galaxy_context):
    res = install.find_new_deps_from_installed(galaxy_context, [])
    assert res == []


def test_find_new_deps_from_installed(galaxy_context):
    repo_spec = RepositorySpec(namespace='some_namespace',
                               name='some_name',
                               version='4.3.2')

    req_spec = RequirementSpec(namespace='some_required_namespace',
                               name='some_required_name',
                               version_spec='==1.0.0')

    some_requirement = Requirement(repository_spec=repo_spec,
                                   op=RequirementOps.EQ,
                                   requirement_spec=req_spec)

    installed_repo = Repository(repo_spec, requirements=[some_requirement, some_requirement])
    res = install.find_new_deps_from_installed(galaxy_context, [installed_repo])

    log.debug('res: %s', res)
    assert isinstance(res, list)
    assert isinstance(res[0], Requirement)
    assert res[0].requirement_spec == req_spec
