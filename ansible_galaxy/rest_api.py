########################################################################
#
# (C) 2013, James Cammarata <jcammarata@ansible.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#
########################################################################

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import codecs
import logging
import json
import os
import socket
import ssl
import sys
import uuid

from six.moves.urllib.parse import quote as urlquote
from six.moves.urllib.parse import urlparse
from six.moves import http_client

from ansible_galaxy import url_client
from ansible_galaxy import exceptions
from ansible_galaxy.multipart_form import MultiPartForm
from ansible_galaxy.utils.text import to_native, to_text

from ansible_galaxy.flat_rest_api.urls import open_url

log = logging.getLogger(__name__)


def g_connect(method):
    ''' wrapper to lazily initialize connection info to galaxy '''

    def wrapped(self, *args, **kwargs):
        if not self.initialized:
            log.debug("Initial connection to galaxy_server: %s", self.api_server)

            server_version = self._get_server_api_version()

            if server_version not in self.SUPPORTED_VERSIONS:
                raise exceptions.GalaxyClientError("Unsupported Galaxy server API version: %s" % server_version)

            self.baseurl = '%s/api/%s' % (self.api_server, server_version)
            self.version = server_version  # for future use

            # log.debug("Base API: %s", self.baseurl)

            self.initialized = True
        return method(self, *args, **kwargs)
    return wrapped


# TODO: extract a http client and/or most of __call_galaxy for generic  url/http use
class GalaxyAPI(object):
    ''' This class is meant to be used as a API client for an Ansible Galaxy server '''

    SUPPORTED_VERSIONS = ['v1']

    # FIXME: just pass in server_url
    def __init__(self, galaxy):

        # log.debug('galaxy: %s', galaxy)
        log.debug('Using galaxy server URL %s with ignore_certs=%s', galaxy.server['url'], galaxy.server['ignore_certs'])

        self.url_client = url_client.URLClient(galaxy)

        # these are set at the last minute @by g_connect
        self.baseurl = None
        self.version = None
        self.initialized = False

        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    # TODO: raise an API/net specific exception?
    @g_connect
    def __call_galaxy(self, url, args=None, headers=None, http_method=None):
        return self.url_client.request(url=url, args=args, headers=headers, http_method=http_method)

    @property
    def api_server(self):
        return self.url_client._api_server

    # @property
    # def validate_certs(self):
    #    return self._validate_certs

    def _get_server_api_version(self):
        """
        Fetches the Galaxy API current version to ensure
        the API server is up and reachable.
        """
        url = '%s/api/' % self.api_server

        try:
            return_data = open_url(url, validate_certs=self.url_client._validate_certs)
        except Exception as e:
            raise exceptions.GalaxyClientError("Failed to get data from the API server (%s): %s " % (url, to_native(e)))

        try:
            data = json.loads(to_text(return_data.read(), errors='surrogate_or_strict'))
        except Exception as e:
            raise exceptions.GalaxyClientError("Could not process data from the API server (%s): %s " % (url, to_native(e)))

        if 'current_version' not in data:
            raise exceptions.GalaxyClientError("missing required 'current_version' from server response (%s)" % url)

        self.log.debug('Server API version of URL %s is "%s"', url, data['current_version'])
        return data['current_version']

    @g_connect
    def lookup_repo_by_name(self, namespace, name):
        namespace = urlquote(namespace)
        name = urlquote(name)
        url = '%s/repositories/?name=%s&provider_namespace__namespace__name=%s' % (self.baseurl, name, namespace)
        data = self.__call_galaxy(url, http_method='GET')
        if data["results"]:
            return data["results"][0]
        return {}

    @g_connect
    def fetch_content_related(self, related_url):
        """
        Fetch the list of related items for the given role.
        The url comes from the 'related' field of the role.
        """
        self.log.debug('related_url=%s', related_url)

        # try:
        url = '%s%s?page_size=50' % (self.api_server, related_url)

        # can raise a GalaxyClientError
        data = self.__call_galaxy(url, http_method='GET')

        # empty list for return value if there are no results
        results = data.get('results', [])

        # TODO: generalize the pagination support
        # check for paginated results
        done = (data.get('next_link', None) is None)

        while not done:
            url = '%s%s' % (self.api_server, data['next_link'])
            data = self.__call_galaxy(url, http_method='GET')

            # if no results, default to a empty list
            results += data.get('results', [])

            done = (data.get('next_link', None) is None)

        return results

    @g_connect
    def fetch_namespace(self, namespace):
        namespace = urlquote(namespace)
        url = '%s/namespaces/?name=%s' % (self.baseurl, namespace)
        data = self.__call_galaxy(url, http_method='GET')
        if data["results"]:
            return data["results"][0]
        return {}

    @g_connect
    def publish_file(self, data, archive_path, publish_api_key):
        form = MultiPartForm()
        for key in data:
            form.add_field(key, data[key])

        form.add_file('file', os.path.basename(archive_path),
                      fileHandle=codecs.open(archive_path, "rb"),
                      mimetype='application/octet-stream')

        url = '%s/collections/' % self.baseurl
        log.debug('url: %s', url)

        _, netloc, url, _, _, _ = urlparse(url)

        try:
            form_buffer = form.get_binary().getvalue()
            http = http_client.HTTPConnection(netloc)
            http.connect()
            http.putrequest("POST", url)
            http.putheader('Content-type', form.get_content_type())
            http.putheader('Content-length', str(len(form_buffer)))

            if publish_api_key:
                http.putheader('Authorization', 'Token %s' % publish_api_key)

            http.endheaders()
            http.send(form_buffer)
        except socket.error as exc:
            log.exception(exc)
            raise exceptions.GalaxyPublishError(
                'Network error while transferring file "%s" to Galaxy server (%s): %s' %
                (archive_path, self.galaxy.server['url'], str(exc)),
                archive_path=archive_path
            )

        r = http.getresponse()

        log.debug('code: %s', r.getcode())
        log.debug('info: %s', r.info())
        log.debug('reason: %s', r.reason)

        response_body = r.read()
        log.debug('response_body: %s', response_body)

        # 202 'Accepted'
        if r.status == 202:
            return response_body
        else:
            raise exceptions.GalaxyPublishError(
                'Error transferring file "%s" to Galaxy server (%s): %s - %s' %
                (archive_path, self.galaxy.server['url'], r.status, r.reason),
                archive_path=archive_path
            )
