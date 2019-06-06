import logging
import os
import pprint

from ansible_galaxy import collection_artifact
from ansible_galaxy import collections_lockfile
from ansible_galaxy import collection_artifact
from ansible_galaxy import display
from ansible_galaxy import exceptions
from ansible_galaxy.fetch import fetch_factory
from ansible_galaxy import install
from ansible_galaxy import installed_repository_db
from ansible_galaxy import requirements
from ansible_galaxy.fetch import fetch_factory
from ansible_galaxy.models.collections_lock import CollectionsLock
from ansible_galaxy.models.fetchable_requirement import FetchableRequirement
from ansible_galaxy.models.repository_spec import FetchMethods
from ansible_galaxy.models.requirement import Requirement, RequirementOps
from ansible_galaxy.models.requirement_spec import RequirementSpec
from ansible_galaxy.utils.misc import uniq

log = logging.getLogger(__name__)


# TODO: revisit this since we don't have to emulate the 'ansible-galaxy install'
#       support for roles now, and could used different error handling
def raise_without_ignore(ignore_errors, msg=None, rc=1):
    """
    Exits with the specified return code unless the
    option --ignore-errors was specified
    """
    ignore_error_blurb = '- you can use --ignore-errors to skip failed collections and finish processing the list.'
    # TODO: error if ignore_errors, warn otherwise?
    if not ignore_errors:
        # Note: msg may actually be an exception instance or a text string

        message = ignore_error_blurb
        if msg:
            message = '%s:\n%s' % (msg, ignore_error_blurb)
        # TODO: some sort of ignoreable exception
        raise exceptions.GalaxyError(message)


def _log_installed(installed_repositories, requirement_to_install, display_callback):
    for installed_repo in installed_repositories:
        required_by_blurb = ''
        # FIXME
        # if requirement_to_install.repository_spec:
        #    required_by_blurb = ' (required by %s)' % requirement_to_install.repository_spec.label

        msg = 'Installed: %s %s to %s%s' % (installed_repo.label,
                                            installed_repo.repository_spec.version,
                                            installed_repo.path,
                                            required_by_blurb)

        log.info(msg)
        display_callback(msg)


def _verify_requirements_repository_spec_have_namespaces(requirements_list):
    for requirement_to_install in requirements_list:
        req_spec = requirement_to_install.requirement_spec
        # log.debug('repo install repository_spec: %s', req_spec)

        if not req_spec.namespace:
            raise exceptions.GalaxyRepositorySpecError(
                'The repository spec "%s" requires a namespace (either "namespace.name" or via --namespace)' % (req_spec),
                repository_spec=None)


def requirement_needs_installed(irdb,
                                requirement_to_install,
                                display_callback=None):
    '''Filter out requirements that should not actually be installed

    This include requirements met my already installed collections.'''

    # TODO: if we want client side content whitelist/blacklist, or pinned versions,
    #       or rules to only update within some semver range (ie, only 'patch' level),
    #       we could hook rule validation stuff here.

    # TODO: we could do all the downloads first, then install them. Likely
    #       less error prone mid 'transaction'
    log.debug('Processing/filtering %r', requirement_to_install)

    requirement_spec_to_install = requirement_to_install.requirement_spec

    # else trans to ... FIND_FETCHER?

    # TODO: check if already installed and move to approriate state

    log.debug('About to filter requested requirement_spec_to_install: %s', requirement_spec_to_install)
    log.debug('Checking to see if %s is already installed', requirement_spec_to_install)

    already_installed_iter = irdb.by_requirement_spec(requirement_spec_to_install)
    already_installed = sorted(list(already_installed_iter))

    log.debug('req_spec: %s already_installed: %s', requirement_spec_to_install, already_installed)

    if already_installed:
        for already_installed_repository in already_installed:
            display_callback('%s is already installed at %s' % (already_installed_repository.repository_spec.label,
                                                                already_installed_repository.path),
                             level='warning')
        log.debug('Stuff %s was already installed. In %s', requirement_spec_to_install, already_installed)

        return False

    return True


def find_requirement(galaxy_context,
                     irdb,
                     fetchable_requirement,
                     # fetcher,
                     display_callback=None,
                     # TODO: error handling callback ?
                     ignore_errors=False,
                     no_deps=False,
                     force_overwrite=False):
    '''Lookup metadata about requirement_to_install (ie, from Galaxy API)'''

    requirement_spec_to_install = fetchable_requirement.requirement.requirement_spec

    # TODO: revisit, issue with calling display from here is it doesn't know if it was
    #       is being called because of a dep or not
    display_callback('Finding %s' % requirement_spec_to_install.label, level='info')

    # if we fail to get a fetcher here, then to... FIND_FETCHER_FAILURE ?
    # could also move some of the logic in fetcher_factory to be driven from here
    # and make the steps of mapping repository spec -> fetcher method part of the
    # state machine. That might be a good place to support multiple galaxy servers
    # or preferring local content to remote content, etc.

    # FIND state
    # See if we can find metadata and/or download the archive before we try to
    # remove an installed version...
    try:
        find_results = fetchable_requirement.fetcher.find(requirement_spec=requirement_spec_to_install)
    except exceptions.GalaxyError as e:
        # log.debug('requirement_to_install %s failed to be met: %s', requirement_to_install, e)
        msg = 'Unable to find metadata for %s: %s' % (requirement_spec_to_install.label, e)
        log.warning(msg)
        # FIXME: raise dep error exception?
        raise_without_ignore(ignore_errors, msg=msg)

        # continue
        return None

    # find() builds a RepoSpec from a ReqSpec
    repository_spec_to_install = find_results.get('repository_spec_to_install', None)

    if find_results.get('custom'):
        if find_results['custom'].get('collection_is_deprecated', False):
            display_callback("The collection '%s' is deprecated." % (repository_spec_to_install.label),
                             level='warning')

    # FIXME: make this a real object not just a tuple
    return find_results


def fetch_repo(collection_to_install,
               ignore_errors=False,
               force_overwrite=False,
               display_callback=None):

    log.debug('collection_to_install: %s', collection_to_install)

    fetcher = collection_to_install['fetcher']
    repository_spec_to_install = collection_to_install['repo_spec']
    find_results = collection_to_install['find_results']

    try:
        fetch_results = fetcher.fetch(repository_spec_to_install,
                                      find_results=find_results)

        log.debug('fetch_results: %s', fetch_results)

        # fetch_results will include a 'archive_path' pointing to where the artifact
        # was saved to locally.
    except exceptions.GalaxyError as e:
        # fetch error probably should just go to a FAILED state, at least until
        # we have to implement retries

        log.warning('Unable to fetch %s: %s',
                    repository_spec_to_install.name,
                    e)

        raise_without_ignore(ignore_errors, e)

        # FIXME: raise ?
        return None

    log.debug('FETCHED: %s', repository_spec_to_install)
    return fetch_results


def install_repo(galaxy_context,
                 collection_to_install,
                 ignore_errors=False,
                 force_overwrite=False,
                 display_callback=None):

    # FIXME: exc handling

    installed_repositories = []

    repository_spec_to_install = collection_to_install['repo_spec']

    try:
        installed_repositories = install.install(galaxy_context,
                                                 collection_to_install,
                                                 force_overwrite=force_overwrite,
                                                 display_callback=display_callback)
    except exceptions.GalaxyError as e:
        # TODO: make the display an error here? depending on ignore_error?
        msg = "- %s was NOT installed successfully: %s "
        display_callback(msg % (repository_spec_to_install.label, e), level='warning')
        log.warning(msg, repository_spec_to_install.label, str(e))
        raise_without_ignore(ignore_errors, e)
        return []

    if not installed_repositories:
        msg_tmpl = "- %s was NOT installed successfully:"
        log.warning(msg_tmpl, repository_spec_to_install.label)
        msg = msg_tmpl % repository_spec_to_install.label
        raise_without_ignore(ignore_errors, msg)

    return installed_repositories


# TODO: split into resolve, find/get metadata, resolve deps, download, install transaction
def find_required_collections(galaxy_context,
                              irdb,
                              _fetchable_requirements_list,
                              display_callback=None,
                              # TODO: error handling callback ?
                              ignore_errors=False,
                              no_deps=False,
                              force_overwrite=False):
    '''Return collections_to_install'''

    display_callback = display_callback or display.display_callback

    collections_to_install = {}

    fetchable_requirements_list = uniq(_fetchable_requirements_list)

    # _verify_requirements_repository_spec_have_namespaces(requirements_list)

    for fetchable_requirement_to_install in fetchable_requirements_list:
        requirement_to_install = fetchable_requirement_to_install.requirement

        log.debug('requirement_to_install: %s', fetchable_requirement_to_install)
        # log.debug('version_spec: %s', version_spec)

        # INITIAL state

        # RESOLVE REQUIREMENT  # ie, if http://example.com/foo.tar.gz, download, extract, get ns,n,v

        log.debug('requirement_to_install: %s', requirement_to_install)
        log.debug('requirement_to_install: %r', requirement_to_install)

        # FILTER
        if not requirement_needs_installed(irdb, requirement_to_install,
                                           display_callback=display_callback):
            log.debug('FILTERED out: %s', requirement_to_install)
            continue

        # fetcher = fetch_factory.get(galaxy_context=galaxy_context,
        #                            requirement_spec=requirement_to_install.requirement_spec)

        # FIND
        find_results = find_requirement(galaxy_context,
                                        irdb,
                                        fetchable_requirement_to_install,
                                        # fetcher,
                                        display_callback=display_callback,
                                        ignore_errors=ignore_errors,
                                        no_deps=no_deps,
                                        force_overwrite=force_overwrite)

        # TODO: state transition, if find_results -> INSTALL
        #       if not, then FIND_FAILED
        if not find_results:
            log.debug('find_requirement() returned None for requirement_to_install: %s', requirement_to_install)
            continue

        # log.debug('find_results: %s', pprint.pformat(find_results))
        repo_spec_to_install = find_results.get('repository_spec_to_install')
        if not repo_spec_to_install:
            log.debug('find_requirement() was not able to find a solution for requirement_to_install: %s', requirement_to_install)
            continue

        collections_to_install[repo_spec_to_install.label] = \
            {'find_results': find_results,
             'requirement_to_install': requirement_to_install,
             'fetcher': fetchable_requirement_to_install.fetcher,
             'repo_spec': repo_spec_to_install,
             }

        log.debug('About to FETCH repository requested by %s: %s',
                  requirement_to_install, repo_spec_to_install)

        log.debug('collections_to_install: %s', pprint.pformat(collections_to_install))

    return collections_to_install


def fetch_repos(collections_to_install):
    log.debug('collections_to_install: %s', collections_to_install)
    for col_key, collection_to_install in collections_to_install.items():

        # FETCH
        fetch_results = fetch_repo(collection_to_install)

        # side effect, modifying value in dict in place
        collection_to_install['fetch_results'] = fetch_results
        # collections_to_install[repo_spec_to_install.label]['fetch_results'] = fetch_results

    log.debug('collections_to_install2: %s', collections_to_install)
    return collections_to_install


def install_collections(galaxy_context, collections_to_install, display_callback=None):
    all_installed_repos = []

    for col_key, collection_to_install in collections_to_install.items():
        fetcher = collection_to_install['fetcher']

        # INSTALL
        installed_repositories = install_repo(galaxy_context,
                                              collection_to_install,
                                              display_callback=display_callback)

        # CLEANUP
        fetcher.cleanup()

        # ANNOUNCE
        _log_installed(installed_repositories, requirement_to_install=None,
                       display_callback=display_callback)

        # ACCUMULATE
        all_installed_repos.extend(installed_repositories)

    return all_installed_repos


def find_unsolved_deps(galaxy_context,
                       collections_to_install,
                       display_callback=None):

    log.debug('find_unsolved_deps len(collections)=%s',
              len(collections_to_install))

    all_deps = []
    dupe_deps = []

    for collection_to_install in collections_to_install:
        col_data = collections_to_install[collection_to_install]

        deps = col_data['find_results'].get('requirements', {})

        log.debug('deps from %s:\n%s', collection_to_install, pprint.pformat(deps))

        for dep in deps:
            if dep in all_deps:
                dupe_deps.append(dep)
                log.warning('WARN duplicate deps, first is %s, second is %s from %s',
                            all_deps[dep], dep, collection_to_install)
                continue

            all_deps.append(dep)

    log.debug('dupe_deps: %s', dupe_deps)
    log.debug('all_deps\n:%s', pprint.pformat(all_deps))

    # unsolved_requirements = requirements.from_dependencies_dict(all_deps)

    unsolved_requirements = []

    for requirement in all_deps:
        log.debug('Checking if %s is provided by something installed', str(requirement))

        # Search for an exact ns_n_v match
        irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

        already_installed_iter = irdb.by_requirement(requirement)
        already_installed = list(already_installed_iter)

        log.debug('already_installed: %s', already_installed)

        solved = False
        for provider in already_installed:
            log.debug('The requirement %s is already provided by %s', requirement, provider)
            solved = solved or True

        if solved:
            log.debug('skipping requirement %s', requirement)
            continue

        unsolved_requirements.append(requirement)

    log.debug('unsolved_requirements: %s', unsolved_requirements)

    return unsolved_requirements


def fetcher_for_requirement(requirement, galaxy_context):
    '''Figure out the fetcher for this requirement, create it, return it'''

    fetcher = fetch_factory.get(galaxy_context=galaxy_context,
                                requirement_spec=requirement.requirement_spec)
    log.debug('fetcher: %s', fetcher)

    return fetcher


def associate_fetchable_requirements(requirements_list,
                                     galaxy_context):
    fetchable_requirements = []

    for requirement in requirements_list:
        fetcher = fetcher_for_requirement(requirement, galaxy_context)

        fetchable_req = FetchableRequirement(requirement, fetcher)

        fetchable_requirements.append(fetchable_req)

    return fetchable_requirements


def install_requirements_loop(galaxy_context,
                              requirements_list,
                              display_callback=None,
                              ignore_errors=False,
                              no_deps=False,
                              force_overwrite=False):

    results = {
        'errors': [],
        'success': True
    }

    log.debug('requirements_list: %s', requirements_list)

    # TODO: rename installed_db? installed_collections_db? icdb?
    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    collections_to_install = {}

    log.debug('DEPSOLVE')

    # Loop until there are no unresolved deps or we break
    while True:
        if not requirements_list:
            break

        # RESOLVE lazy requirements? (ie, http/file) ?
        # transaction_item = resolve_requ
        fetchable_requirements_list = associate_fetchable_requirements(requirements_list,
                                                                       galaxy_context)

        new_required_collections = \
            find_required_collections(galaxy_context,
                                      irdb,
                                      fetchable_requirements_list,
                                      display_callback=display_callback,
                                      ignore_errors=ignore_errors,
                                      no_deps=no_deps,
                                      force_overwrite=force_overwrite)

        collections_to_install.update(new_required_collections)

        # VALIDATE_DEPS  # validate that all of the deps, when combined, don't contradict etc
        # raise Dependency conflicts? Or possible accumalte all problems then raise dep exceptions
        # validate_dependencies(collections_to_install)

        log.debug('FINDUNSOLVEDEPS')

        new_requirements = find_unsolved_deps(galaxy_context,
                                              new_required_collections,
                                              display_callback=display_callback)

        log.debug('new_requirements: %s', new_requirements)

        # Note that requirements_list is used for the main conditional in the while loop
        # Reset requirements_list
        requirements_list = new_requirements

        for req in requirements_list:
            if req.repository_spec:
                msg = 'Installing requirement %s (required by %s)' % (req.requirement_spec.label, req.repository_spec.label)
            else:
                msg = 'Installing requirement %s' % req.requirement_spec.label
            display_callback(msg, level='info')

    # DEPS SOLVED
    # FETCH
    log.debug('FETCH')

    collections_to_install = fetch_repos(collections_to_install)

    log.debug('collections_to_install: %s', pprint.pformat(collections_to_install))

    # VERIFY
    log.debug('VERIFY')
    # verify downloaded artifacts

    # INSTALL
    #   TODO: EXTRACT
    #   TODO: REPLACE_INSTALLED
    installed_collections = install_collections(galaxy_context,
                                                collections_to_install,
                                                display_callback=display_callback)

    log.debug('installed_collections: %s', installed_collections)

    return results


def run(galaxy_context,
        collections_lockfile_path=None,
        requirement_spec_strings=None,
        requirement_specs_file=None,
        editable=False,
        namespace_override=False,
        ignore_errors=False,
        no_deps=False,
        force_overwrite=False,
        display_callback=None):

    requirements_list = []

    if requirement_spec_strings:
        requirements_list += \
            requirements.requirements_from_strings(requirement_spec_strings=requirement_spec_strings,
                                                   editable=editable,
                                                   namespace_override=namespace_override)

    if requirement_specs_file:
        # yaml load the file
        # requirements_list += \
        #     requirements.requirements_from_dict()
        pass

    log.debug('requirements_list: %s', requirements_list)

    results = install_requirements_loop(galaxy_context,
                                        requirements_list,
                                        display_callback=display_callback,
                                        ignore_errors=ignore_errors,
                                        no_deps=no_deps,
                                        force_overwrite=force_overwrite)

    log.debug('install results: %s', results)

    if results['errors']:
        for error in results['errors']:
            display_callback(error)

    if results['success']:
        return os.EX_OK  # 0

    # TODO: finer grained return codes

    return os.EX_SOFTWARE  # 70
