import logging
import mock

from ansible_galaxy.actions import install
from ansible_galaxy import installed_repository_db
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
    # TODO: tests for local file, remote url, etc
    res = install.requirements_from_strings(['alikins.some_collection',
                                             'testuser.another',
                                             ])

    log.debug('res: %s', res)

    assert isinstance(res, list)
    reqs = [req for req in res]
    for req in reqs:
        assert isinstance(req, Requirement)

    namespaces = [x.requirement_spec.namespace for x in res]
    assert 'alikins' in namespaces
    assert 'testuser' in namespaces


def test_install_repository_specs_loop(galaxy_context, mocker):
    repo_spec = RepositorySpec(namespace='alikins', name='some_collection',
                               version='4.2.1')
    repo = Repository(repository_spec=repo_spec, installed=True)

    # needy_repo_spec = RepositorySpec(namespace='needy',
    #                                  name='allie',
    #                                  version='9.1.1'),

    other_repo_spec = RepositorySpec(namespace='testuser',
                                     name='another',
                                     version='11.12.99')

    needy_req_spec = RequirementSpec(namespace='some_required_namespace',
                                     name='some_required_name',
                                     version_spec='==1.0.0')

    needy_requirement = Requirement(repository_spec=other_repo_spec,
                                    op=RequirementOps.EQ,
                                    requirement_spec=needy_req_spec)

    other_repo = Repository(repository_spec=other_repo_spec,
                            requirements=[needy_requirement],
                            installed=True)

    needed_repo_spec = RepositorySpec(namespace='some_required_namespace',
                                      name='some_required_name',
                                      version='1.0.0')

    needed_repo = Repository(repository_spec=needed_repo_spec,
                             requirements=[],
                             )

    requested_spec_strings = install.requirements_from_strings(['alikins.some_collection',
                                                                'testuser.another'])

    log.debug('req_spec_strings: %s', requested_spec_strings)
    requirements_list = requested_spec_strings
    #     install.requirements_from_strings(repository_spec_strings=requested_spec_strings,
    #                                       editable=False,
    #                                       namespace_override=None)

    import pprint

    def mock_install_repository(*args, **kwargs):
        log.debug('mir: args=%s, kwargs=%s', pprint.pformat(args), repr(kwargs))
        req = args[2]

        log.debug('install_repo req: %s', req)
        log.debug('install_repo reqlabel: %s', req.requirement_spec.label)

        # TODO: fix .label / add .label equilv sans version

        repos = {'some_collection': [repo],
                 'another': [other_repo],
                 'some_required_name': [needed_repo]}
        return repos[req.requirement_spec.name]

    mock_ir = mocker.patch('ansible_galaxy.actions.install.install_repository',
                           side_effect=mock_install_repository)

    res = install.install_repository_specs_loop(galaxy_context,
                                                requirements_list,
                                                display_callback=display_callback)

    log.debug('res: %s', res)
    log.debug('mock_ir.call_args_list: %s', pprint.pformat(mock_ir.call_args_list))

    for call in mock_ir.call_args_list:
        log.debug('call: %s', pprint.pformat(list(call)))

    assert res == 0  # duh, it's hardcoded


def test_install_requirements(galaxy_context, mocker):
    repo_spec = RepositorySpec(namespace='alikins', name='some_collection',
                               version='4.2.1')
    repo = Repository(repository_spec=repo_spec, installed=True)

    other_repo = Repository(repository_spec=RepositorySpec(namespace='xxxxxxxxxx',
                                                           name='mmmmmmm',
                                                           version='11.12.99'),
                            installed=True)

    requirements = install.requirements_from_strings(['alikins.some_collection',
                                                      'testuser.another'])

    log.debug('requirements: %s', requirements)

    mock_irdb2 = mocker.MagicMock(name='the_mock_irdb2')
    mock_irdb2.select.return_value = [repo, other_repo]
    # mock_irdb2.by_requirement_spec.return_value = [repo]
    # irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    another_repo_spec = RepositorySpec(namespace='testuser', name='another',
                                       version='11.12.99')
    expected_installs = [Repository(repository_spec=another_repo_spec)]

    mocker.patch('ansible_galaxy.actions.install.install_repositories',
                 return_value=expected_installs)

    res = install.install_requirements(galaxy_context,
                                       mock_irdb2,
                                       requirements,
                                       display_callback=None,
                                       ignore_errors=False,
                                       no_deps=False,
                                       force_overwrite=False)

    log.debug('res: %s', res)
    log.debug('mock_irdb2: %s', mock_irdb2)
    log.debug('mock_irdb2.call_args_list: %s', mock_irdb2.call_args_list)

    assert isinstance(res, list)
    res_repo = res[0]
    assert isinstance(res_repo, Repository)
    assert isinstance(res_repo.repository_spec, RepositorySpec)
    assert res_repo.repository_spec.namespace == 'testuser'
    assert res_repo.repository_spec.name == 'another'


def test_install_repos_empty_requirements(galaxy_context):
    requirements_to_install = []

    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    ret = install.install_repositories(galaxy_context,
                                       irdb,
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

    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    ret = install.install_repositories(galaxy_context,
                                       irdb,
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

    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    ret = install.install_repository(galaxy_context,
                                     irdb,
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

    # ? Mock this instead? maybe a fixture?
    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    ret = install.install_repositories(galaxy_context,
                                       irdb,
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
