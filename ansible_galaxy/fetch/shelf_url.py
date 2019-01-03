import logging

from ansible_galaxy import download
from ansible_galaxy import exceptions
from ansible_galaxy.fetch import base

log = logging.getLogger(__name__)


class ShelfFetch(base.BaseFetch):
    fetch_method = 'shelf'

    def __init__(self, repository_spec, shelf_uri, validate_certs=True):
        super(ShelfFetch, self).__init__()

        self.repository_spec = repository_spec
        self.remote_url = '%s/%s' % (shelf_uri, repository_spec.label)
        self.shelf_uri = shelf_uri
        log.debug('shelf_uri: %s', shelf_uri)
        log.debug('remote_url: %s', self.remote_url)

        self.validate_certs = validate_certs
        log.debug('Validate TLS certificates: %s', self.validate_certs)

        self.remote_resource = self.remote_url

    def find(self):
        # kluge, if we dont get an exception, lets assume it worked and didnt 404
        # we dont really care what is in it at the moment, just that the path exists
        content_url_exists = download.url_exists(self.remote_url, validate_certs=self.validate_certs)

        log.debug('content_url_exists: %s', content_url_exists)

        if not content_url_exists:
            raise exceptions.GalaxyClientError("- sorry, %s was not found on %s." % (self.repository_spec.label,
                                                                                     self.shelf_uri))

        results = {'content': {'galaxy_namespace': self.repository_spec.namespace,
                               'repo_name': self.repository_spec.name},
                   'specified_content_version': self.repository_spec.version,
                   'specified_repository_spec': self.repository_spec.scm}

        return results

    def fetch(self, find_results=None):
        '''Download the remote_url to a temp file

        Can raise GalaxyDownloadError on any exception while downloadin remote_url and saving it.'''

        find_results = find_results or {}

        # NOTE: could move download.fetch_url here instead of splitting it
        content_archive_path = download.fetch_url(self.remote_url, validate_certs=self.validate_certs)
        self.local_path = content_archive_path

        log.debug('content_archive_path=%s', content_archive_path)

        results = {'archive_path': content_archive_path,
                   'fetch_method': self.fetch_method}
        results['content'] = find_results['content']
        results['custom'] = {'remote_url': self.remote_url,
                             'validate_certs': self.validate_certs}
        return results
