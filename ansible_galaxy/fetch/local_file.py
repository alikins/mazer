
import logging

from ansible_galaxy import repository
from ansible_galaxy import repository_archive
from ansible_galaxy.fetch import base

log = logging.getLogger(__name__)


class LocalFileFetch(base.BaseFetch):
    fetch_method = 'local_file'

    def find(self, requirement_spec):
        vspec = requirement_spec.version_spec.specs[0].spec

        # update local_path to point to the artifact
        self.local_path = requirement_spec.src

        results = {'content': {'galaxy_namespace': requirement_spec.namespace,
                               'repo_name': requirement_spec.name,
                               # For a local file, we created the version_spec to match
                               # exactly the version from the file, so dig into the version_spec
                               # a bit to pull that out.
                               # TODO/FIXME: helper method/wrapper for making this less coupled
                               'version': str(vspec)},
                   }

        return results

    def fetch(self, repository_spec_to_install, find_results=None):
        find_results = find_results or {}

        repository_archive_path = self.local_path

        log.debug('repository_archive_path=%s (inplace)', repository_archive_path)

        repo_archive = self._load_repository_archive(repository_archive_path)

        repo = self._load_repository(repo_archive)

        results = {'archive_path': repository_archive_path,
                   'fetch_method': self.fetch_method}

        results['custom'] = {'local_path': self.local_path}
        results['content'] = find_results['content']
        results['content']['fetched_name'] = repo.repository_spec.name

        return results

    def _load_repository_archive(self, archive_path):
        repo_archive = repository_archive.load_archive(archive_path)
        log.debug('repo_archive: %s', repo_archive)

        return repo_archive

    def _load_repository(self, repository_archive):
        repo = repository.load_from_archive(repository_archive)
        log.debug('repo: %s', repo)
        return repo

    def cleanup(self):
        return None
