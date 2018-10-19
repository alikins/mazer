# strategy for installing a Collection (name resolve it, find it,
#  fetch it's artifact, validate/verify it, install/extract it, update install dbs, etc)
# import datetime
import logging
import os
import pprint

import attr

from ansible_galaxy import repository_archive
from ansible_galaxy import exceptions
from ansible_galaxy import installed_repository_db
from ansible_galaxy import matchers
from ansible_galaxy.fetch import fetch_factory

log = logging.getLogger(__name__)

# This should probably be a state machine for stepping through the install states
# See actions.install.install_collection for a sketch of the states


def fetcher(galaxy_context, repository_spec):
    log.debug('Attempting to get fetcher for repository_spec=%s', repository_spec)

    fetcher = fetch_factory.get(galaxy_context=galaxy_context,
                                repository_spec=repository_spec)

    log.debug('Using fetcher: %s for repository_spec: %s', fetcher, repository_spec)

    return fetcher


def find(fetcher):
    """find/discover info about the content"""

    find_results = fetcher.find()

    return find_results


# def fetch(fetcher, collection):
#    pass

def fetch(fetcher, repository_spec, find_results):
    """download the archive and side effect set self._archive_path to where it was downloaded to.

    MUST be called after self.find()."""

    log.debug('Fetching repository_spec=%s', repository_spec)

    try:
        # FIXME: note that ignore_certs for the galaxy
        # server(galaxy_context.server['ignore_certs'])
        # does not really imply that the repo archive download should ignore certs as well
        # (galaxy api server vs cdn) but for now, we use the value for both
        fetch_results = fetcher.fetch(find_results=find_results)
    except exceptions.GalaxyDownloadError as e:
        log.exception(e)

        # TODO: having to keep fetcher state for tracking fetcher.remote_resource and/or cleanup
        #       is kind of annoying.These methods may need to be in a class. Or maybe
        #       the GalaxyDownloadError shoud/could have any info.
        blurb = 'Failed to fetch the content archive "%s": %s'
        log.error(blurb, fetcher.remote_resource, e)

        # reraise, currently handled in main
        # TODO: if we support more than one archive per invocation, will need to accumulate errors
        #       if we want to skip some of them
        raise

    return fetch_results

#
# The caller of install() may be the best place to figure out things like where to
# extract the content too. Can likely handle figuring out if artifact is a collection_artifact
# or a trad_role_artifact and call different things. Or better, create an approriate
# ArchiveArtifact and just call it's extract()/install() etc.
#
# def install(fetch_results, enough_info_to_figure_out_where_to_extract_etc,
#            probably_a_progress_display_callback, maybe_an_error_callback):
#    pass

    # return install_time? an InstallInfo? list of InstalledCollection?


def update_repository_spec(fetch_results,
                           repository_spec=None):
    '''Verify we got the archive we asked for, checksums, check sigs, etc

    At the moment, also side effect and evols repository_spec to match fetch results
    so that needs to be extracted'''
    # TODO: do we still need to check the fetched version against the spec version?
    #       We do, since the unspecific version is None, so fetched versions wont match
    #       so we need a new repository_spec for install.
    # TODO: this is more or less a verify/validate step or state transition
    content_data = fetch_results.get('content', {})

    # If the requested namespace/version is different than the one we got via find()/fetch()...
    if content_data.get('fetched_version', repository_spec.version) != repository_spec.version:
        log.info('Version "%s" for %s was requested but fetch found version "%s"',
                 repository_spec.version, '%s.%s' % (repository_spec.namespace, repository_spec.name),
                 content_data.get('fetched_version', repository_spec.version))

        repository_spec = attr.evolve(repository_spec, version=content_data['fetched_version'])

    if content_data.get('content_namespace', repository_spec.namespace) != repository_spec.namespace:
        log.info('Namespace "%s" for %s was requested but fetch found namespace "%s"',
                 repository_spec.namespace, '%s.%s' % (repository_spec.namespace, repository_spec.name),
                 content_data.get('content_namespace', repository_spec.namespace))

        repository_spec = attr.evolve(repository_spec, namespace=content_data['content_namespace'])

    return repository_spec


def install(galaxy_context,
            fetcher,
            fetch_results,
            repository_spec,
            force_overwrite=False,
            display_callback=None):
    """extract the archive to the filesystem and write out install metadata.

    MUST be called after self.fetch()."""

    log.debug('install: repository_spec=%s, force_overwrite=%s',
              repository_spec, force_overwrite)
    just_installed_spec_and_results = []

    # FIXME: really need to move the fetch step elsewhere and do it before,
    #        install should get pass a content_archive (or something more abstract)
    # TODO: some useful exceptions for 'cant find', 'cant read', 'cant write'

    archive_path = fetch_results.get('archive_path', None)

    # TODO: this could be pulled up a layer, after getting fetch_results but before install()
    if not archive_path:
        raise exceptions.GalaxyClientError('No valid content data found for...')

    log.debug("installing from %s", archive_path)

    # TODO: this is figuring out the archive type (multi-content collection or a trad role)
    #       could potentially pull this up a layer
    content_archive_ = repository_archive.load_archive(archive_path)

    log.debug('content_archive_: %s', content_archive_)
    log.debug('content_archive_.info: %s', content_archive_.info)

    # we strip off any higher-level directories for all of the files contained within
    # the tar file here. The default is 'github_repo-target'. Gerrit instances, on the other
    # hand, does not have a parent directory at all.

    # preparation for archive extraction
    if not os.path.isdir(galaxy_context.content_path):
        log.debug('No content path (%s) found so creating it', galaxy_context.content_path)

        os.makedirs(galaxy_context.content_path)

    # A list of InstallationResults
    res = content_archive_.install(repository_spec=repository_spec,
                                   extract_to_path=galaxy_context.content_path,
                                   force_overwrite=force_overwrite)
    just_installed_spec_and_results.append((repository_spec, res))

    if display_callback:
        display_callback("- The repository %s was succssfully installed to %s" % (repository_spec.label,
                                                                                  galaxy_context.content_path))

    # rm any temp files created when getting the content archive
    # TODO: use some sort of callback?
    fetcher.cleanup()

    # We know the repo specs for the repos we asked to install, and the installation results,
    # so now use that info to find the just installed repos on disk and load them and return them.
    just_installed_repository_specs = [x[0] for x in just_installed_spec_and_results]

    log.debug('just_installed_repository_specs: %s', just_installed_repository_specs)

    just_installed_repository_match_filter = matchers.MatchRepositorySpecsNamespaceNameVersion(just_installed_repository_specs)

    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)
    just_installed_repository_generator = irdb.select(repository_match_filter=just_installed_repository_match_filter)

    just_installed_repositories = []

    # TODO: Eventually, we could make install.install return a generator and yield these results straigt
    #       from just_installed_repository_generator. The loop here is mostly for logging/feedback.
    for just_installed_repository in just_installed_repository_generator:
        log.debug('just_installed_repository is installed: %s', pprint.pformat(attr.asdict(just_installed_repository)))

        # log.info('Installed repository repository_spec: %s', just_installed_repository.repository_spec)
        # log.info('installed repository path: %s', just_installed_repository.path)

        just_installed_repositories.append(just_installed_repository)

    log.debug('just_installed_repositories: %s', pprint.pformat(just_installed_repositories))

    return just_installed_repositories
