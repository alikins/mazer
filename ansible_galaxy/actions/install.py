import logging
import os
import pprint

from ansible_galaxy import display
from ansible_galaxy import exceptions
from ansible_galaxy import install
from ansible_galaxy import installed_repository_db
# from ansible_galaxy import matchers
from ansible_galaxy import requirements
from ansible_galaxy import repository_spec
from ansible_galaxy.fetch import fetch_factory

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


def _verify_requirements_repository_spec_have_namespaces(requirements_list):
    for requirement_to_install in requirements_list:
        req_spec = requirement_to_install.requirement_spec
        log.debug('repo install repository_spec: %s', req_spec)

        if not req_spec.namespace:
            raise exceptions.GalaxyRepositorySpecError(
                'The repository spec "%s" requires a namespace (either "namespace.name" or via --namespace)' % req_spec.spec_string,
                repository_spec=req_spec)


def install_repository(galaxy_context,
                       irdb,
                       requirement_to_install,
                       display_callback=None,
                       # TODO: error handling callback ?
                       ignore_errors=False,
                       no_deps=False,
                       force_overwrite=False):
    '''This installs a single package by finding it, fetching it, verifying it and installing it.'''

    display_callback = display_callback or display.display_callback

    # INITIAL state
    # dep_requirements = []

    # TODO: we could do all the downloads first, then install them. Likely
    #       less error prone mid 'transaction'
    log.debug('Processing %r', requirement_to_install)

    repository_spec_to_install = requirement_to_install.requirement_spec
    requirement_spec_to_install = requirement_to_install.requirement_spec

    # else trans to ... FIND_FETCHER?

    # TODO: check if already installed and move to approriate state

    log.debug('About to find() requested requirement_spec_to_install: %s', requirement_spec_to_install)

    # potential_repository_spec is a repo spec for the install candidate we potentially found.
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

        return None

    # TODO: revisit, issue with calling display from here is it doesn't know if it was
    #       is being called because of a dep or not
    display_callback('Preparing to install %s' % requirement_spec_to_install.label, level='info')
    # We dont have anything that matches the RequirementSpec installed
    fetcher = fetch_factory.get(galaxy_context=galaxy_context,
                                requirement_spec=requirement_spec_to_install)

    # if we fail to get a fetcher here, then to... FIND_FETCHER_FAILURE ?
    # could also move some of the logic in fetcher_factory to be driven from here
    # and make the steps of mapping repository spec -> fetcher method part of the
    # state machine. That might be a good place to support multiple galaxy servers
    # or preferring local content to remote content, etc.

    # FIND state
    # See if we can find metadata and/or download the archive before we try to
    # remove an installed version...
    try:
        find_results = fetcher.find()
    except exceptions.GalaxyError as e:
        log.debug('requirement_to_install %s failed to be met: %s', requirement_to_install, e)
        log.warning('Unable to find metadata for %s: %s', requirement_spec_to_install.label, e)
        # FIXME: raise dep error exception?
        raise_without_ignore(ignore_errors, e)

        # continue
        return None

    # TODO: make sure repository_spec version is correct and set

    # TODO: state transition, if find_results -> INSTALL
    #       if not, then FIND_FAILED

    # TODO/FIXME: We give find() a RequirementSpec, but find_results should have enough
    #             info to create a concrete RepositorySpec

    # TODO: if we want client side content whitelist/blacklist, or pinned versions,
    #       or rules to only update within some semver range (ie, only 'patch' level),
    #       we could hook rule validation stuff here.

    # TODO: build a new repository_spec based on what we actually fetched to feed to
    #       install etc. The fetcher.fetch() could return a datastructure needed to build
    #       the new one instead of doing it in verify()
    repository_spec_to_install = repository_spec.repository_spec_from_find_results(find_results,
                                                                                   requirement_spec_to_install)

    log.debug('About to download repository requested by %s: %s', requirement_spec_to_install, repository_spec_to_install)

    if find_results['custom'].get('collection_is_deprecated', False):
        display_callback("The collection '%s' is deprecated." % (repository_spec_to_install.label),
                         level='warning')

    # FETCH state
    # Note: fetcher.fetch() as a side effect sets fetcher._archive_path to where it was downloaded to.

    try:
        fetch_results = fetcher.fetch(find_results=find_results)

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

    # FIXME: seems like we want to resolve deps before trying install
    #        We need the role (or other content) deps from meta before installing
    #        though, and sometimes (for galaxy case) we dont know that until we've downloaded
    #        the file, which we dont do until somewhere in the begin of content.install (fetch).
    #        We can get that from the galaxy API though.
    #
    # FIXME: exc handling

    installed_repositories = []

    try:
        installed_repositories = install.install(galaxy_context,
                                                 fetcher,
                                                 fetch_results,
                                                 repository_spec=repository_spec_to_install,
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
def install_requirements(galaxy_context,
                         irdb,
                         requirements_to_install,
                         display_callback=None,
                         # TODO: error handling callback ?
                         ignore_errors=False,
                         no_deps=False,
                         force_overwrite=False):

    display_callback = display_callback or display.display_callback
    log.debug('requirements_to_install: %s', requirements_to_install)
    # log.debug('no_deps: %s', no_deps)
    # log.debug('force_overwrite: %s', force_overwrite)

    # dep_requirements = []
    most_installed_repositories = []

    # TODO: this should be adding the content/self.args/content_left to
    #       a list of needed deps

    # Remove any dupe repository_specs
    requirements_to_install_uniq = set(requirements_to_install)

    _verify_requirements_repository_spec_have_namespaces(requirements_to_install_uniq)
    # TODO: if the default ordering of repository_specs isnt useful, may need to tweak it
    for requirement_to_install in sorted(requirements_to_install_uniq):
        log.debug('requirement_to_install: %s', requirement_to_install)

        installed_repositories = install_repository(galaxy_context,
                                                    irdb,
                                                    requirement_to_install,
                                                    display_callback=display_callback,
                                                    ignore_errors=ignore_errors,
                                                    no_deps=no_deps,
                                                    force_overwrite=force_overwrite)

        # log.debug('dep_requirement_repository_specs1: %s', dep_requirements)

        if not installed_repositories:
            log.debug('install_repository() returned None for requirement_to_install: %s', requirement_to_install)
            continue

        for installed_repo in installed_repositories:
            required_by_blurb = ''
            if requirement_to_install.repository_spec:
                required_by_blurb = ' (required by %s)' % requirement_to_install.repository_spec.label

            log.info('Installed: %s %s to %s%s',
                     installed_repo.label,
                     installed_repo.repository_spec.version,
                     installed_repo.path,
                     required_by_blurb)

        most_installed_repositories.extend(installed_repositories)
        # dep_requirements.extend(new_dep_requirements)

    return most_installed_repositories


# NOTE: this is equiv to add deps to a transaction
def find_new_requirements_from_installed(galaxy_context, installed_repos, no_deps=False):
    if no_deps:
        return []

    total_reqs_set = set()

    log.debug('finding new deps for installed repos: %s',
              [str(x) for x in installed_repos])

    # install requirements ("dependencies" in collection info), if we want them
    for installed_repository in installed_repos:

        # convert reqs list to sets, Losing any ordering, but avoids dupes of requirements
        reqs_set = set(installed_repository.requirements)

        total_reqs_set.update(reqs_set)

    # TODO: This does not grow nicely as the size
    #       of the list of requirements of everything installed grows
    all_requirements = sorted(list(total_reqs_set))

    unsolved_requirements = []

    for requirement in all_requirements:
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

    log.debug('Found additional requirements: %s', pprint.pformat(unsolved_requirements))

    return unsolved_requirements


# TODO: rename 'install' once we rename ansible_galaxy.install to ansible_galaxy.install_collection
# FIXME: probably pass the point where passing around all the data to methods makes sense
#        so probably needs a stateful class here
def install_requirements_loop(galaxy_context,
                              requirements,
                              display_callback=None,
                              # TODO: error handling callback ?
                              ignore_errors=False,
                              no_deps=False,
                              force_overwrite=False):

    results = {
        'errors': [],
        'success': True
    }

    requirements_list = requirements

    log.debug('requirements_list: %s', requirements_list)

    # for req in requirements_list:
    #    display_callback('Installing %s' % req.requirement_spec.label, level='info')

    # TODO: rename installed_db? installed_collections_db? icdb?
    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    # Loop until there are no unresolved deps or we break
    while True:
        if not requirements_list:
            break

        just_installed_repositories = \
            install_requirements(galaxy_context,
                                 irdb,
                                 requirements_list,
                                 display_callback=display_callback,
                                 ignore_errors=ignore_errors,
                                 no_deps=no_deps,
                                 force_overwrite=force_overwrite)

        # set the repository_specs to search for to whatever the install reported as being needed yet
        # requirements_list = new_requirements_list
        requirements_list = find_new_requirements_from_installed(galaxy_context,
                                                                 just_installed_repositories,
                                                                 no_deps=no_deps)

        for req in requirements_list:
            if req.repository_spec:
                msg = 'Installing requirement %s (required by %s)' % (req.requirement_spec.label, req.repository_spec.label)
            else:
                msg = 'Installing requirement %s' % req.requirement_spec.label
            display_callback(msg, level='info')

    return results


def run(galaxy_context,
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
