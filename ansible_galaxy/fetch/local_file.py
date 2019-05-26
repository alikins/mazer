
import logging

from ansible_galaxy import repository
from ansible_galaxy import repository_archive
from ansible_galaxy import repository_spec
from ansible_galaxy.fetch import base
from ansible_galaxy.models.repository_spec import RepositorySpec

log = logging.getLogger(__name__)


class LocalFileFetch(base.BaseFetch):
    fetch_method = 'local_file'

    def find(self, requirement_spec):
        vspec = requirement_spec.version_spec.specs[0].spec

        # update local_path to point to the artifact
        self.local_path = requirement_spec.src

        # 'resolved_namespace' and 'resolved_name' included here if different
        repo_spec_germ = {'galaxy_namespace': requirement_spec.namespace,
                          'repo_name': requirement_spec.name,
                          # For a local file, we created the version_spec to match
                          # exactly the version from the file, so dig into the version_spec
                          # a bit to pull that out.
                          # TODO/FIXME: helper method/wrapper for making this less coupled
                          'version': str(vspec)}

        repo_spec_data = \
            repository_spec.repository_spec_data_from_find_results({'content': repo_spec_germ},
                                                                   requirement_spec)

        repository_spec_to_install = RepositorySpec.from_dict(repo_spec_data)

        # TODO: have to dig into the local file to find it's dependencies
        repo = self._load(self.local_path)

        log.debug('repo.requirements: %s', repo.requirements)

        # the name from the metadata in the artifact
        repo_spec_germ['fetched_name'] = repo.repository_spec.name

        results = {'content': repo_spec_germ,
                   'repository_spec_to_install': repository_spec_to_install,
                   'requirements': repo.requirements,
                   }

        return results

    def fetch(self, repository_spec_to_install, find_results=None):
        find_results = find_results or {}

        repository_archive_path = self.local_path

        results = {'archive_path': repository_archive_path,
                   'fetch_method': self.fetch_method}

        # repo = self._load(repository_archive_path)

        results['custom'] = {'local_path': self.local_path}
        results['content'] = find_results['content']
        # results['content']['fetched_name'] = repo.repository_spec.name

        return results

    def _load_repository_archive(self, archive_path):
        repo_archive = repository_archive.load_archive(archive_path)
        log.debug('repo_archive: %s', repo_archive)

        return repo_archive

    def _load_repository(self, repository_archive):
        repo = repository.load_from_archive(repository_archive)
        log.debug('repo: %s', repo)
        return repo

    def _load(self, archive_path):

        log.debug('repository_archive_path=%s (inplace)', archive_path)

        repo_archive = self._load_repository_archive(archive_path)

        repo = self._load_repository(repo_archive)

        return repo

    def cleanup(self):
        return None
