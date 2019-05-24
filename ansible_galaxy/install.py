# strategy for installing a Collection (name resolve it, find it,
#  fetch it's artifact, validate/verify it, install/extract it, update install dbs, etc)
import logging
import os
import pprint

import attr

from ansible_galaxy import repository_archive
from ansible_galaxy import exceptions
from ansible_galaxy import installed_repository_db
from ansible_galaxy.models.install_destination import InstallDestinationInfo
from ansible_galaxy.models.repository_spec import FetchMethods

log = logging.getLogger(__name__)

# This should probably be a state machine for stepping through the install states
# See actions.install.install_collection for a sketch of the states


def install(galaxy_context,
            collection_to_install,
            force_overwrite=False,
            display_callback=None):
    """extract the archive to the filesystem and write out install metadata.

    MUST be called after self.fetch()."""

    just_installed_spec_and_results = []

    repository_spec = collection_to_install['repo_spec']
    fetcher = collection_to_install['fetcher']

    # find_results = collection_to_install['find_results']
    fetch_results = collection_to_install['fetch_results']

    log.debug('install: repository_spec=%s, force_overwrite=%s',
              repository_spec, force_overwrite)

    # FIXME: really need to move the fetch step elsewhere and do it before,
    #        install should get pass a content_archive (or something more abstract)
    # TODO: some useful exceptions for 'cant find', 'cant read', 'cant write'

    archive_path = fetch_results.get('archive_path', None)

    # VALIDATE
    #   VALIDATE DOWNLOADS
    # TODO: this could be pulled up a layer, after getting fetch_results but before install()
    if not archive_path:
        raise exceptions.GalaxyClientError('No valid content data found for...')

    log.debug("installing from %s", archive_path)

    #   VALIDATE artifact archives
    repo_archive_ = repository_archive.load_archive(archive_path, repository_spec)

    log.debug('repo_archive_: %s', repo_archive_)
    log.debug('repo_archive_.info: %s', repo_archive_.info)

    # TODO: move to install action, before EXTRACT
    # preparation for archive extraction
    if not os.path.isdir(galaxy_context.collections_path):
        log.debug('No content path (%s) found so creating it', galaxy_context.collections_path)

        os.makedirs(galaxy_context.collections_path)

    # ALLOCATE
    # Build up all the info about where the repository will be installed to
    namespaced_repository_path = '%s/%s' % (repository_spec.namespace,
                                            repository_spec.name)

    editable = repository_spec.fetch_method == FetchMethods.EDITABLE

    destination_info = InstallDestinationInfo(collections_path=galaxy_context.collections_path,
                                              repository_spec=repository_spec,
                                              namespaced_repository_path=namespaced_repository_path,
                                              force_overwrite=force_overwrite,
                                              editable=editable)

    # EXTRACT
    # A list of InstallationResults
    res = repository_archive.install(repo_archive_,
                                     repository_spec=repository_spec,
                                     destination_info=destination_info,
                                     display_callback=display_callback)

    just_installed_spec_and_results.append((repository_spec, res))

    # CLEANUP
    # rm any temp files created when getting the content archive
    # TODO: use some sort of callback?
    fetcher.cleanup()

    # Could probably skip this step at some point to speed things up
    # VERIFY  reload the repos from disk to verify they are isntalled properly
    #
    # We know the repo specs for the repos we asked to install, and the installation results,
    # so now use that info to find the just installed repos on disk and load them and return them.
    just_installed_repository_specs = [x[0] for x in just_installed_spec_and_results]

    # log.debug('just_installed_repository_specs: %s', just_installed_repository_specs)

    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    just_installed_repositories = []

    for just_installed_repository_spec in just_installed_repository_specs:
        just_installed_repository_gen = irdb.by_repository_spec(just_installed_repository_spec)

        # TODO: Eventually, we could make install.install return a generator and yield these results straigt
        #       from just_installed_repository_generator. The loop here is mostly for logging/feedback.
        # Should only get one answer here for now.
        for just_installed_repository in just_installed_repository_gen:
            log.debug('just_installed_repository is installed: %s', pprint.pformat(attr.asdict(just_installed_repository)))

            just_installed_repositories.append(just_installed_repository)

    # log.debug('just_installed_repositories: %s', pprint.pformat(just_installed_repositories))

    return just_installed_repositories
