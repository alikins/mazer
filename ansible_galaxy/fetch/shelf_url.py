import logging

import yaml

from ansible_galaxy import download
from ansible_galaxy import exceptions
from ansible_galaxy import url_client

from ansible_galaxy.fetch import base

from ansible_galaxy.models.collection_info import CollectionInfo

from ansible_galaxy.utils.text import to_text

log = logging.getLogger(__name__)


class ShelfFetch(base.BaseFetch):
    fetch_method = 'shelf'

    def __init__(self, repository_spec, galaxy_context, validate_certs=True):
        super(ShelfFetch, self).__init__()

        self.repository_spec = repository_spec
        self.galaxy_context = galaxy_context

        shelf_data = self.galaxy_context.shelves.get(repository_spec.shelf, None)

        self.remote_url = '%s/%s/%s' % (shelf_data['uri'], repository_spec.namespace, repository_spec.name)
        self.shelf_uri = shelf_data['uri']
        log.debug('shelf_uri: %s', self.shelf_uri)
        log.debug('remote_url: %s', self.remote_url)

        self.validate_certs = validate_certs
        log.debug('Validate TLS certificates: %s', self.validate_certs)

        self.remote_resource = self.remote_url

    def find(self):
        log.debug("find %s in shelf: %s at uri: %s", self.repository_spec.label, self.shelf_uri, self.remote_url)

        # TODO: need object/API that represents the 'Shelf' interface. Try to keep it
        #       consistent with the galaxy rest GalaxyAPI() interface
        #       and the InstalledRepositoryDatabase() apis

        # TODO: build the url to the shelf, and to the base index data of the repo
        #       (something like http://example.com/shelves/some_shelf/index.yml)
        #
        #       download the shelf index url. If that fails, return false (and/or
        #       raise an exception indicating the shelf doesnt exist)
        #
        #       get the index.yml, read/parse it into a data structure, then look
        #       for repository_spec in the data structure (ie, if the shelf has that repo_spec)
        #       if it does, return True.

        #       keep the data structure around (self.shelf_index for ex) since
        #       get()/fetch() will need it (it should include the download
        #       url for the archive itself)

        # kluge, if we dont get an exception, lets assume it worked and didnt 404
        # we dont really care what is in it at the moment, just that the path exists
        index_yml_url = '%s/%s' % (self.shelf_uri, 'index.yml')
        urlclient = url_client.URLClient(self.galaxy_context)

        response = urlclient.request(index_yml_url)
        response_body = to_text(response.read(), errors='surrogate_or_strict')

        response_slug = '"%s" %s' % (index_yml_url,
                                     response.getcode())

        log.debug('%s response: %s response_body:\n%s', response_slug, response, response_body)

        # reset since we log first
        response.seek(0)

        # FIXME: DO NOT TRY TO DESERIALIZE THIS WHOLE THING IN THE FIND METHOD
        # FIXME: build up attr based models etc
        # FIXME: replace with some ShelfInfo object
        data_dict = yaml.safe_load(response)

        log.debug('%s response data:\n%s', response_slug, data_dict)

        shelf_files = data_dict.get('files', [])

        collections_location = None

        for shelf_file in shelf_files:
            log.debug('shelf index file: %s', shelf_file)
            # FIXME: no dupe detections
            if shelf_file['type'] == 'collections':
                collections_location = shelf_file['location']

        log.debug('collections_location: %s', collections_location)

        collections_data = {}
        if collections_location:
            # FIXME/TODO: relative path sanitization
            collections_yml_url = '%s/%s' % (self.shelf_uri, collections_location)
            collections_response = urlclient.request(collections_yml_url)
            collections_data = yaml.safe_load(collections_response)

            log.debug('collections_data: %s', collections_data)

        namespaces = {}
        if collections_data:
            namespaces = collections_data.get('namespaces', {})

        if namespaces:
            target_namespace = namespaces.get(self.repository_spec.namespace, {})
            target_collection = target_namespace['collections'].get(self.repository_spec.name, {})
            log.debug('tns: %s tc: %s', target_namespace, target_collection)

            # FIXME: we are changing name in galaxy.yml/collection_info
            # target_collection['name'] = '%s.%s' % (self.repository_spec.namespace, self.repository_spec.name)

            try:
                col_info = CollectionInfo(**target_collection)
            except ValueError:
                raise
            except Exception as exc:
                raise exceptions.GalaxyClientError("Error parsing collection metadata: %s" % str(exc))

            log.debug('col_info: %s', col_info)

        # content_url_exists = download.url_exists(galaxy_yml_url, validate_certs=self.validate_certs)
        # co_path = download.fetch_url(self.remote_url, validate_certs=self.validate_certs)

        # log.debug('content_url_exists: %s', content_url_exists)

        if not data_dict:
            raise exceptions.GalaxyClientError("- sorry, %s was not found on %s." % (self.repository_spec.label,
                                                                                     self.shelf_uri))

        results = {'content': {'galaxy_namespace': self.repository_spec.namespace,
                               'repo_name': self.repository_spec.name},
                   'specified_content_version': self.repository_spec.version,
                   'specified_repository_spec': self.repository_spec.scm,
                   'custom': {'shelf_uri': self.shelf_uri,
                              # FIXME: this is just filler for testing
                              'shelf_sub_uri': self.remote_url},
                   }

        log.debug('shelf find results ds: %s', results)
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