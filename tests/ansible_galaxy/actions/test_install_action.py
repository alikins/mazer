import logging
import mock
import os
import pprint

import pytest

from ansible_galaxy.actions import install
from ansible_galaxy import installed_repository_db
from ansible_galaxy import exceptions
from ansible_galaxy import repository_spec
from ansible_galaxy import requirements
from ansible_galaxy.fetch.base import BaseFetch
from ansible_galaxy.models.fetchable_requirement import FetchableRequirement
from ansible_galaxy.models.repository import Repository
from ansible_galaxy.models.repository_spec import RepositorySpec
from ansible_galaxy.models.requirement import Requirement, RequirementOps
from ansible_galaxy.models.requirement_spec import RequirementSpec

log = logging.getLogger(__name__)


def display_callback(msg, **kwargs):
    log.debug('%s: kwargs: %r', msg, kwargs)


def test_run(galaxy_context, mocker):
    mock_results = {'success': True,
                    'errors': []}
    mocker.patch('ansible_galaxy.actions.install.install_requirements_loop',
                 return_value=mock_results)
    res = install.run(galaxy_context,
                      requirement_spec_strings=['some_namespace.some_name'],
                      display_callback=display_callback)

    log.debug('res: %s', res)
    assert res == os.EX_OK  # 0


def test_run_errors(galaxy_context, mocker):
    mock_results = {'success': False,
                    'errors': ['The first thing that failed was everything.',
                               'Then the rest failed']}
    mocker.patch('ansible_galaxy.actions.install.install_requirements_loop',
                 return_value=mock_results)

    mock_display_callback = mocker.MagicMock(name='mock_display_callback',
                                             wraps=display_callback)

    res = install.run(galaxy_context,
                      requirement_spec_strings=['some_namespace.some_name'],
                      display_callback=mock_display_callback)

    log.debug('res: %s', res)
    assert res == os.EX_SOFTWARE  # 70

    expected_display_calls = [mocker.call('The first thing that failed was everything.'),
                              mocker.call('Then the rest failed')]

    log.debug('mdc.call_args_list: %s', mock_display_callback.call_args_list)
    assert expected_display_calls in mock_display_callback.call_args_list


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

    requirements_list = requirements.requirements_from_strings(['alikins.some_collection',
                                                                'testuser.another'])

    log.debug('requirements_list: %s', requirements_list)

    import pprint

    def stub_install_collection(*args, **kwargs):
        log.debug('mir: args=%s, kwargs=%s', pprint.pformat(args), repr(kwargs))
        req = args[2]

        log.debug('install_collection req: %s', req)
        log.debug('install_collection reqlabel: %s', req.requirement_spec.label)

        # TODO: fix .label / add .label equilv sans version

        repos = {'some_collection': [repo],
                 'another': [other_repo],
                 'some_required_name': [needed_repo]}

        return repos[req.requirement_spec.name]

    # mock out the install_collection to avoid the network requests, etc
    mock_ir = mocker.patch('ansible_galaxy.actions.install.install_collection',
                           side_effect=stub_install_collection)

    mocker.patch('ansible_galaxy.actions.install.find_required_collections',
                 return_value={'alikins.some_collection':
                               {'find_results':
                                {'requirements': []},
                                }
                               })
    res = install.install_requirements_loop(galaxy_context,
                                            requirements_list,
                                            display_callback=display_callback)

    log.debug('res: %s', res)
    log.debug('mock_ir.call_args_list: %s', pprint.pformat(mock_ir.call_args_list))

    for call in mock_ir.call_args_list:
        log.debug('call: %s', pprint.pformat(list(call)))

    assert isinstance(res, dict)
    assert isinstance(res['errors'], list)
    assert isinstance(res['success'], bool)

    assert res['success'] is True


# BOGUS?
def test_find_required_collections(galaxy_context, mocker):
    repo_spec = RepositorySpec(namespace='alikins', name='some_collection',
                               version='4.2.1')
    repo = Repository(repository_spec=repo_spec, installed=True)

    other_repo = Repository(repository_spec=RepositorySpec(namespace='xxxxxxxxxx',
                                                           name='mmmmmmm',
                                                           version='11.12.99'),
                            installed=True)

    requirements_list = requirements.requirements_from_strings(['alikins.some_collection',
                                                                'testuser.another'])

    log.debug('requirements_list: %s', requirements_list)

    mock_irdb2 = mocker.MagicMock(name='the_mock_irdb2')
    mock_irdb2.select.return_value = [repo, other_repo]
    # mock_irdb2.by_requirement_spec.return_value = [repo]
    # irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    another_repo_spec = RepositorySpec(namespace='testuser', name='another',
                                       version='11.12.99')
    expected_installs = [Repository(repository_spec=another_repo_spec)]

    # mocker.patch('ansible_galaxy.actions.install.install_repositories',
    #              return_value=expected_installs)
    mocker.patch('ansible_galaxy.actions.install.install_collections',
                 return_value=expected_installs)

    find_results = {'stuff_from_find': 'foo',
                    'custom': {}}

    repo_spec_germ = {'galaxy_namespace': 'testuser',
                      'repo_name': 'another',
                      'version': '11.12.99'}

    find_results = {'content': repo_spec_germ,
                    'repository_spec_to_install': another_repo_spec,
                    'artifact': {'sha256': '123451234512345',
                                 'filename': 'testuser-another-11.12.99',
                                 'size': 1024},
                    # 'requirement_spec': requirement_spec,
                    'requirements': [],
                    # 'requirement_spec': requirement_spec,
                    'custom': {'download_url': 'https://example.invalid/whatever',
                               'collection_is_deprecated': False,
                               },
                    }

    mock_find_collection_data_for_requirement = mocker.patch('ansible_galaxy.actions.install.find_collection_data_for_requirement',
                                                             return_value=find_results)

    fetchable_requirements_list = install.associate_fetchable_requirements(requirements_list,
                                                                           galaxy_context)

    # mock_irdb = mocker.MagicMock(name='the_mock_irdb')
    # mock_irdb.by_requirement.return_value = []

    res = install.find_required_collections(galaxy_context,
                                            mock_irdb2,
                                            fetchable_requirements_list,
                                            display_callback=None,
                                            ignore_errors=False,
                                            no_deps=False,
                                            force_overwrite=False)

    log.debug('res:\n%s', pprint.pformat(res))
    log.debug('mock_irdb2: %s', mock_irdb2)
    log.debug('mock_irdb2.call_args_list: %s', mock_irdb2.call_args_list)
    log.debug('mock_find_collection_data_for_requirement.call_args_list: %s', mock_find_collection_data_for_requirement.call_args_list)

    assert isinstance(res, dict)
    res_find_result = res['testuser.another']
    res_repo_spec = res_find_result['repo_spec']

    assert isinstance(res_repo_spec, RepositorySpec)
    assert res_repo_spec.namespace == 'testuser'
    assert res_repo_spec.name == 'another'


# BOGUS?
def test_find_required_collections_empty_requirements(galaxy_context):
    requirements_to_install = []

    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    ret = install.find_required_collections(galaxy_context,
                                            irdb,
                                            requirements_list=requirements_to_install,
                                            display_callback=display_callback)

    log.debug('ret: %s', ret)

    assert isinstance(ret, list)
    assert ret == []


# BOGUS?
def test_install_repositories(galaxy_context, mocker):
    repo_spec = RepositorySpec(namespace='some_namespace', name='some_name',
                               version='9.4.5')
    expected_repos = [Repository(repository_spec=repo_spec)]

    requirements_to_install = \
        requirements.from_dependencies_dict({'some_namespace.this_requires_some_name': '*'})

    mocker.patch('ansible_galaxy.actions.install.install_collection',
                 return_value=expected_repos)

    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    ret = install.install_repositories(galaxy_context,
                                       irdb,
                                       requirements_to_install=requirements_to_install,
                                       display_callback=display_callback)

    log.debug('ret: %s', ret)

    assert isinstance(ret, list)
    assert ret == expected_repos


def test_fetch_collection_validate_artifacts_exception(galaxy_context, mocker):
    repo_spec = RepositorySpec(namespace='some_namespace', name='some_name',
                               version='9.3.245')

    find_results = {'content': {'galaxy_namespace': 'some_namespace',
                                'repo_name': 'some_name'},
                    'custom': {'repo_data': {},
                               'download_url': 'http://foo.invalid/stuff/blip.tar.gz',
                               'repoversion': {'version': '9.3.245'},
                               'collection_is_deprecated': True,
                               },
                    }

    mocker.patch('ansible_galaxy.actions.install.install.install')

    mock_fetcher = mocker.MagicMock(name='MockFetch')
    mock_fetcher.find.return_value = find_results
    mock_fetcher.fetch.side_effect = exceptions.GalaxyArtifactChksumError(artifact_path='/dev/null/fake/path',
                                                                          expected='FAKEEXPECTEDa948904f2f0f479',
                                                                          actual='FAKEACTUAL4b0d2ed1c1cd2a1ec0fb85d2')

    # mocker.patch('ansible_galaxy.actions.install.fetch_factory.get',
    #             new=faux_get)

    collection_to_install = {'fetcher': mock_fetcher,
                             'repo_spec': repo_spec,
                             'find_results': find_results,
                             }

    with pytest.raises(exceptions.GalaxyClientError,
                       match="While fetching some_namespace.*/dev/null/fake/path.*did not match.*FAKEEXPECTEDa948904f2f0f479") as exc_info:
        install.fetch_collection(collection_to_install,
                                 display_callback=display_callback)

    log.debug('exc_info: %s', exc_info)


def test_find_collection_data_for_requirement_error(galaxy_context, mocker):
    requirements_list = \
        requirements.from_dependencies_dict({'some_namespace.this_requires_some_name': '*'})

    mocker.patch('ansible_galaxy.actions.install.install.install')

    mock_fetcher = mocker.MagicMock(name='MockFetcher', spec=BaseFetch)
    mock_fetcher.find.side_effect = exceptions.GalaxyError('Faux exception during find')

    fetchable_req = FetchableRequirement(requirements_list[0], mock_fetcher)
    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    with pytest.raises(exceptions.GalaxyError, match='.*Faux exception during find.*') as exc_info:
        install.find_collection_data_for_requirement(galaxy_context,
                                                     irdb,
                                                     fetchable_req,
                                                     display_callback=display_callback)

    log.debug('exc_info: %s %r', exc_info, exc_info)


def test_fetch_collection_fetch_error(galaxy_context, mocker):
    repo_spec = RepositorySpec(namespace='some_namespace', name='some_name',
                               version='9.3.245')

    find_results = {'content': {'galaxy_namespace': 'some_namespace',
                                'repo_name': 'some_name'},
                    'custom': {'repo_data': {},
                               'download_url': 'http://foo.invalid/stuff/blip.tar.gz',
                               'repoversion': {'version': '9.3.245'},
                               },
                    }

    mock_fetcher = mocker.MagicMock(name='MockFetch')
    mock_fetcher.find.return_value = find_results
    mock_fetcher.fetch.side_effect = exceptions.GalaxyDownloadError(url='http://foo.invalid/stuff/blip.tar.gz')

    # mocker.patch('ansible_galaxy.actions.install.fetch_factory.get',
    #             new=faux_get)

    collection_to_install = {'fetcher': mock_fetcher,
                             'repo_spec': repo_spec,
                             'find_results': find_results,
                             }
    with pytest.raises(exceptions.GalaxyError,
                       match='.*Error downloading .*http://foo.invalid/stuff/blip.tar.gz.*') as exc_info:
        install.fetch_collection(collection_to_install,
                                 display_callback=display_callback)

    log.debug('exc_info: %s %r', exc_info, exc_info)


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

    def faux_get(galaxy_context, requirement_spec):
        log.debug('faux get %s', requirement_spec)
        mock_fetcher = mocker.MagicMock(name='MockFetch')
        mock_fetcher.find.return_value = find_results
        mock_fetcher.fetch.return_value = {}
        return mock_fetcher

    mocker.patch('ansible_galaxy.actions.install.fetch_factory.get',
                 new=faux_get)
    mocker.patch('ansible_galaxy.actions.install.install.install')

    mock_display_callback = mocker.MagicMock(name='mock_display_callback')

    ret = install.install_collection(galaxy_context,
                                     requirement_to_install=requirements_to_install[0],
                                     display_callback=mock_display_callback)

    expected_display_calls = mocker.call("The collection 'some_namespace.this_requires_some_name' is deprecated.", level='warning')

    log.debug('ret: %s', ret)

    assert expected_display_calls in mock_display_callback.call_args_list


def test_install_repository_install_error(galaxy_context, mocker):
    requirements_to_install = \
        requirements.from_dependencies_dict({'some_namespace.this_requires_some_name': '*'})

    find_results = {'content': {'galaxy_namespace': 'some_namespace',
                                'repo_name': 'some_name'},
                    'custom': {'repo_data': {},
                               'download_url': 'http://foo.invalid/stuff/blip.tar.gz',
                               'repoversion': {'version': '9.3.245'},
                               },
                    }

    def faux_get(galaxy_context, requirement_spec):
        log.debug('faux get %s', requirement_spec)
        mock_fetcher = mocker.MagicMock(name='MockFetch')
        mock_fetcher.find.return_value = find_results
        mock_fetcher.fetch.return_value = {'stuff': 'whatever'}
        return mock_fetcher

    mocker.patch('ansible_galaxy.actions.install.fetch_factory.get',
                 new=faux_get)
    mocker.patch('ansible_galaxy.actions.install.install.install',
                 side_effect=exceptions.GalaxyClientError('Faux galaxy client error from test'))

    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    with pytest.raises(exceptions.GalaxyError,
                       match='.*Faux galaxy client error from test.*') as exc_info:
        install.install_collection(galaxy_context,
                                   irdb,
                                   requirement_to_install=requirements_to_install[0],
                                   display_callback=display_callback)

    log.debug('exc_info: %s %r', exc_info, exc_info)


def test_install_repository_install_empty_results(galaxy_context, mocker):
    requirements_to_install = \
        requirements.from_dependencies_dict({'some_namespace.this_requires_some_name': '*'})

    fetchable_requirements_list = install.associate_fetchable_requirements(requirements_to_install,
                                                                           galaxy_context)

    find_results = {'content': {'galaxy_namespace': 'some_namespace',
                                'repo_name': 'some_name'},
                    'custom': {'repo_data': {},
                               'download_url': 'http://foo.invalid/stuff/blip.tar.gz',
                               'repoversion': {'version': '9.3.245'},
                               },
                    }
    fetch_results = {
        'archive_path': '/tmp/al.tar.gz',
        'cleanup_helper': print,
        'fetch_method': 'galaxy_url',
        'custom': {'download_url': 'https://galaxy-dev.ansible.com/download/alikins-collection_inspect-0.0.38.tar.gz',
                   'collection_is_deprecated': False},
        'content': {'galaxy_namespace': 'alikins',
                    'repo_name': 'collection_inspect',
                    'version': '0.0.38'},
        'artifact': {'sha256': 'c6a69797cb04fa768acb74431ef7ea090e9c9d3e81044feeda65cdd020fbfffd',
                     'filename': 'alikins-collection_inspect-0.0.38.tar.gz',
                     'size': 13113}
    }

    def faux_get(galaxy_context, requirement_spec):
        log.debug('faux get %s', requirement_spec)
        mock_fetcher = mocker.MagicMock(name='MockFetch')
        mock_fetcher.find.return_value = find_results
        mock_fetcher.fetch.return_value = fetch_results
        return mock_fetcher

    mocker.patch('ansible_galaxy.actions.install.fetch_factory.get',
                 new=faux_get)
    mocker.patch('ansible_galaxy.actions.install.install.install',
                 return_value=[])

    with pytest.raises(exceptions.GalaxyError,
                       match='.*some_namespace.this_requires_some_name was NOT installed successfully.*') as exc_info:
        install.install_collection(galaxy_context,
                                   fetchable_requirements_list[0],
                                   display_callback=display_callback)

    log.debug('exc_info: %s %r', exc_info, exc_info)


def test_find_required_collections__no_deps_required(galaxy_context, mocker):
    needed_deps = {}

    requirements_list = \
        requirements.requirements_from_strings(['some_namespace.this_requires_nothing'])

    # mock out install_collection
    mocker.patch('ansible_galaxy.actions.install.install_collection',
                 return_value=[])

    req_already_installed_repo_spec = RepositorySpec(namespace='some_required_namespace',
                                                     name='some_required_name',
                                                     version='1.0.0')
    req_already_installed_repo = Repository(req_already_installed_repo_spec, requirements=[])

    # ? Mock this instead? maybe a fixture?
    # // irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)
    mock_irdb = mocker.MagicMock(name='the_mock_irdb')
    mock_irdb.by_requirement_spec.return_value = [req_already_installed_repo]

    # RESOLVE lazy requirements? (ie, http/file) ?
    # transaction_item = resolve_requ
    fetchable_requirements_list = install.associate_fetchable_requirements(requirements_list,
                                                                           galaxy_context)

    ret = install.find_required_collections(galaxy_context,
                                            mock_irdb,
                                            fetchable_requirements_list,
                                            display_callback=display_callback)

    log.debug('ret: %s', ret)

    assert isinstance(ret, dict)
    assert ret == needed_deps


def test_verify_repository_specs_have_namespace_empty(galaxy_context):
    # will throw an exception if busted
    install._verify_requirements_repository_spec_have_namespaces([])


# even though 'blrp' isnt a valid spec, _build_content_set return something for now
def test_verify_repository_specs_have_namespace(galaxy_context):
    req_spec = mock.Mock(requirement_spec=mock.Mock(namespace=None))
    try:
        install._verify_requirements_repository_spec_have_namespaces([req_spec])
    except exceptions.GalaxyError as e:
        log.exception(e)
        return

    assert False, 'Expected a GalaxyError to be raised here since the repository_spec %s has no namespace or dots' % repository_spec


def test_find_unsolved_deps_nothing_installed_nothing_to_install(galaxy_context, mocker):
    mock_irdb = mocker.MagicMock(name='the_mock_irdb')
    mock_irdb.by_requirement.return_value = []

    res = install.find_unsolved_deps(galaxy_context,
                                     irdb=mock_irdb,
                                     collections_to_install=[])
    log.debug('res: %s', res)

    assert res == []


def test_find_unsolved_deps_not_installed(galaxy_context, mocker):
    repo_spec = RepositorySpec(namespace='some_namespace',
                               name='some_name',
                               version='4.3.2')

    req_spec = RequirementSpec(namespace='some_required_namespace',
                               name='some_required_name',
                               version_spec='==1.0.0')

    some_requirement = Requirement(repository_spec=repo_spec,
                                   op=RequirementOps.EQ,
                                   requirement_spec=req_spec)
    # repo_to_install = Repository(repo_spec, requirements=[some_requirement, some_requirement])

    # mock out the install_collection to avoid the network requests, etc
    # mock_ir = mocker.patch('ansible_galaxy.actions.install.install_collection',
    #                       side_effect=stub_install_repository)

    mock_irdb = mocker.MagicMock(name='the_mock_irdb')
    mock_irdb.by_requirement.return_value = []

    find_results = {'requirements': [some_requirement, some_requirement]}

    collections_to_install = {}
    collections_to_install[repo_spec.label] = \
        {'find_results': find_results,
         'requirement_to_install': some_requirement,
         'fetcher': mocker.MagicMock(name='mock_fetcher'),
         'repo_spec': repo_spec,
         }

    res = install.find_unsolved_deps(galaxy_context,
                                     mock_irdb,
                                     collections_to_install,
                                     display_callback=display_callback)

    log.debug('res: %s', res)
    log.debug('mock_irdb.call_args_list: %s', pprint.pformat(mock_irdb.call_args_list))

    for call in mock_irdb.call_args_list:
        log.debug('call: %s', pprint.pformat(list(call)))

    assert isinstance(res, list)
    assert isinstance(res[0], Requirement)
    assert res[0].requirement_spec == req_spec


def test_find_unsolved_deps_req_already_installed(galaxy_context, mocker):
    repo_spec = RepositorySpec(namespace='some_namespace',
                               name='some_name',
                               version='4.3.2')

    req_spec = RequirementSpec(namespace='some_required_namespace',
                               name='some_required_name',
                               version_spec='==1.0.0')

    some_requirement = Requirement(repository_spec=repo_spec,
                                   op=RequirementOps.EQ,
                                   requirement_spec=req_spec)
    # repo_to_install = Repository(repo_spec, requirements=[some_requirement, some_requirement])

    req_already_installed_repo_spec = RepositorySpec(namespace='some_required_namespace',
                                                     name='some_required_name',
                                                     version='1.0.0')
    req_already_installed_repo = Repository(req_already_installed_repo_spec, requirements=[some_requirement, some_requirement])

    # mock out the install_collection to avoid the network requests, etc
    # mock_ir = mocker.patch('ansible_galaxy.actions.install.install_collection',
    #                       side_effect=stub_install_repository)

    mock_irdb = mocker.MagicMock(name='the_mock_irdb')
    mock_irdb.by_requirement.return_value = [req_already_installed_repo]

    find_results = {'requirements': [some_requirement, some_requirement]}

    collections_to_install = {}
    collections_to_install[repo_spec.label] = \
        {'find_results': find_results,
         'requirement_to_install': some_requirement,
         'fetcher': mocker.MagicMock(name='mock_fetcher'),
         'repo_spec': repo_spec,
         }

    res = install.find_unsolved_deps(galaxy_context,
                                     mock_irdb,
                                     collections_to_install,
                                     display_callback=display_callback)

    log.debug('res: %s', res)
    log.debug('mock_irdb.call_args_list: %s', pprint.pformat(mock_irdb.call_args_list))

    for call in mock_irdb.call_args_list:
        log.debug('call: %s', pprint.pformat(list(call)))

    assert isinstance(res, list)
    # no unsolved deps
    assert res == []
