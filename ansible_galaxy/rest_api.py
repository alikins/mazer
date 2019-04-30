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

import requests

from six.moves.urllib.parse import quote as urlquote
from six.moves.urllib.parse import urlencode

from ansible_galaxy import __version__ as mazer_version
from ansible_galaxy import exceptions
from ansible_galaxy.multipart_form import MultiPartForm
from ansible_galaxy.utils.text import to_native

log = logging.getLogger(__name__)
http_log = logging.getLogger('%s.(http).(general)' % __name__)
request_log = logging.getLogger('%s.(http).(request)' % __name__)
response_log = logging.getLogger('%s.(http).(response)' % __name__)

USER_AGENT_FORMAT = 'Mazer/{version} ({platform}; python:{py_major}.{py_minor}.{py_micro}) ansible_galaxy/{version}'


def user_agent():
    user_agent_data = {'version': mazer_version,
                       'platform': sys.platform,
                       'py_major': sys.version_info.major,
                       'py_minor': sys.version_info.minor,
                       'py_micro': sys.version_info.micro}
    return USER_AGENT_FORMAT.format(**user_agent_data)


def response_slug(response):
    # The slug we use to identify a request by method, url and request id
    # For ex, '"GET https://galaxy.ansible.com/api/v1/repositories" c48937f4e8e849828772c4a0ce0fd5ed'
    slug = '"%s %s" %s' % (response.request.method, response.url, response.request.headers['X-Request-Id'])
    return slug


def request_slug(request):
    slug = '"%s %s" %s' % (request.method, request.url, request.headers['X-Request-Id'])
    return slug


def g_connect(method):
    ''' wrapper to lazily initialize connection info to galaxy '''

    def wrapped(self, *args, **kwargs):
        if not self.initialized:
            log.debug("Initial connection to galaxy_server: %s", self._api_server)

            server_version = self._get_server_api_version()

            if server_version not in self.SUPPORTED_VERSIONS:
                raise exceptions.GalaxyClientError("Unsupported Galaxy server API version: %s" % server_version)

            self.initialized = True
        return method(self, *args, **kwargs)
    return wrapped


class RestClient(object):
    def __init__(self, http_context=None):
        self.http_context = http_context or {}

        log.debug('http_context: %s', http_context)

        # self._validate_certs = not galaxy_context.server['ignore_certs']
        self.initialized = False
        self.initialized = False

        self.user_agent = user_agent()
        log.debug('User Agent: %s', self.user_agent)

        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})

        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    @property
    def validate_certs(self):
        return not self.http_context['server']['ignore_certs']


class GalaxyAPI(object):
    ''' This class is meant to be used as a API client for an Ansible Galaxy server '''

    SUPPORTED_VERSIONS = ['v1', 'v2']

    # FIXME: just pass in server_url
    def __init__(self, galaxy_context):
        self.galaxy_context = galaxy_context

        log.debug('Using galaxy server URL %s with ignore_certs=%s', galaxy_context.server['url'], galaxy_context.server['ignore_certs'])

        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        # set the API server
        self._api_server = galaxy_context.server['url']

        # self.log.debug('Validate TLS certificates for %s: %s', self._api_server, self._validate_certs)

    # TODO: raise an API/net specific exception?
    @g_connect
    def __call_galaxy(self, url, args=None, headers=None, http_method=None):
        http_method = http_method or 'GET'

        request_headers = headers or {}
        request_id = uuid.uuid4().hex
        request_headers['X-Request-ID'] = request_id

        # The slug we use to identify a request by method, url and request id
        # For ex, '"GET https://galaxy.ansible.com/api/v1/repositories" c48937f4e8e849828772c4a0ce0fd5ed'
        request_slug = '"%s %s" %s' % (http_method, url, request_id)

        log.debug('self.session: %s', self.session)

        try:
            # log the http request_slug with request_id to the main log and
            # to the http log, both at INFO level for now.
            http_log.info('%s', request_slug)
            self.log.info('%s', request_slug)

            request_log.debug('%s args=%s', request_slug, args)
            request_log.debug('%s headers=%s', request_slug, request_headers)

            resp = self.session.request(http_method, url, data=args, headers=request_headers,
                                        verify=self._validate_certs)
            log.debug('resp: %s', resp)
            log.debug('resp.request: %s', resp.request)
            log.debug('resp.request.headers: %s', resp.request.headers)

            response_log.info('%s http_status=%s', request_slug, resp.status_code)
            response_log.debug('%s reason=%s', request_slug, resp.reason)
            response_log.debug('%s headers=%s', request_slug, resp.headers)
            response_log.debug('%s history=%s', request_slug, resp.history)

            if resp.history:
                for redirect in resp.history:
                    log.debug('%s Redirected. %s is redirected to %s',
                              request_slug, redirect.url, redirect.headers['Location'])

            response_log.debug('%s resp repr:\n%r', request_slug, resp)

            # FIXME: making the request and loading the response should be sep try/except blocks
            response_body = resp.text

            # debug log the raw response body
            response_log.debug('%s response body:\n%s', request_slug, response_body)

            # TODO/FIXME: Move the loading/parsing of json up a layer, since we don't always need it
            try:
                data = resp.json()
            except ValueError as e:
                log.exception(e)
                data = {}

            # debug log a json version of the data that was created from the response
            response_log.debug('%s data:\n%s', request_slug, json.dumps(data, indent=2))

        except requests.exceptions.RequestException as http_exc:
            self.log.debug('Exception on %s', request_slug)
            self.log.exception("%s: %s", request_slug, http_exc)

            http_log.error('%s data from server error response:\n%s', request_slug, http_exc.response)

            if http_exc.response:
                # FIXME: probably need a try/except here if the response body isnt json which
                #        can happen if a proxy mangles the response
                try:
                    error_msg = 'HTTP error on request %s: %s' % (request_slug,
                                                                  http_exc.response.json()['detail'])
                    raise exceptions.GalaxyClientError(error_msg)
                except (ValueError, KeyError, TypeError) as detail_parse_exc:
                    self.log.exception("%s: %s", request_slug, detail_parse_exc)
                    self.log.warning('Unable to parse error detail from response for request: %s response:  %s', request_slug, detail_parse_exc)

            # TODO: great place to be able to use 'raise from'
            raise exceptions.GalaxyClientError(http_exc)
        except (ssl.SSLError, socket.error) as e:
            self.log.debug('Connection error to Galaxy API for request %s: %s', request_slug, e)
            self.log.exception("%s: %s", request_slug, e)

            raise exceptions.GalaxyClientAPIConnectionError('Connection error to Galaxy API for request %s: %s' % (request_slug, e))

        return data

    @property
    def api_server(self):
        return self._api_server

    @property
    def base_api_url(self):
        return '%s/api' % self._api_server


    def _get_server_api_version(self):
        """
        Fetches the Galaxy API current version to ensure
        the API server is up and reachable.
        """
        url = '%s/api/' % self._api_server

        try:
            resp = self.session.get(url, verify=self._validate_certs)
        except requests.exceptions.RequestException as e:
            raise exceptions.GalaxyClientError("Failed to get data from the API server (%s): %s " % (url, to_native(e)))

        try:
            # data = json.loads(to_text(return_data.read(), errors='surrogate_or_strict'))
            data = resp.json()
        except Exception as e:
            raise exceptions.GalaxyClientError("Could not process data from the API server (%s): %s " % (url, to_native(e)))

        # Don't raise connection indicating errors unless we dont have valid error json
        try:
            resp.raise_for_status()
        except Exception as e:
            raise exceptions.GalaxyClientError("Failed to get data from the API server (%s): %s " % (url, to_native(e)))

        if 'current_version' not in data:
            raise exceptions.GalaxyClientError("missing required 'current_version' from server response (%s)" % url)

        self.log.debug('Server API version of URL %s is "%s"', url, data['current_version'])

        return data['current_version']

    @g_connect
    def _get_paginated_list(self, list_url, page_size=None):
        """
        Fetch the list of related items for the given role.
        The url comes from the 'related' field of the role.
        """
        self.log.debug('related_url=%s', list_url)

        page_size = page_size or 50
        # param_dict = {'page_size': 50}
        param_dict = {}
        params = urlencode(param_dict)
        url = list_url
        if params:
            url = '%s?%s' % (list_url, params)
        log.debug('url: %s params: %s', url, params)

        # can raise a GalaxyClientError
        data = self.__call_galaxy(url, http_method='GET')

        # empty list for return value if there are no results
        results = data.get('results', [])

        done = (data.get('next_link', None) is None)

        while not done:
            url = '%s%s' % (self._api_server, data['next_link'])
            data = self.__call_galaxy(url, http_method='GET')

            # if no results, default to a empty list
            results += data.get('results', [])

            done = (data.get('next_link', None) is None)

        return results

    @g_connect
    def get_collection_detail(self, namespace, name):
        namespace = urlquote(namespace)
        name = urlquote(name)
        url = "%s%s" % (self.base_api_url,
                        '/v2/collections/{namespace}/{name}'.format(namespace=namespace, name=name))

        data = self.__call_galaxy(url, http_method='GET')
        return data

    @g_connect
    def get_object(self, href=None):
        '''Get a full url and return deserialized results'''
        url = href
        # url = "%s%s" % (self.api_server, href)

        data = self.__call_galaxy(url, http_method='GET')
        return data

    @g_connect
    def publish_file(self, data, archive_path, publish_api_key):
        form = MultiPartForm()

        for key in data:
            form.add_field(key, data[key])

        form.add_file('file', os.path.basename(archive_path),
                      fileHandle=codecs.open(archive_path, "rb"),
                      mimetype='application/octet-stream')

        # TODO: figure out how to track API versions finer grained? Ideally
        #       simple enough to not end up with adhoc HATEAOS imp
        #       Maybe just hardcode api ver in calls?
        collection_url_ver = 'v2'
        url = '%s/%s/collections/' % (self.base_api_url, collection_url_ver)

        request_headers = {}

        # TODO: create or use a request.Auth impl
        if publish_api_key:
            request_headers['Authorization'] = 'Token %s' % publish_api_key

        form_buffer = form.get_binary().getvalue()

        request_headers['Content-type'] = form.get_content_type()
        request_headers['Content-length'] = str(len(form_buffer))

        try:

            # TODO: pass in a file-like object and use stream=True
            resp = self.session.post(url, data=form_buffer,
                                     headers=request_headers, verify=self._validate_certs)

        except socket.error as exc:
            log.exception(exc)
            raise exceptions.GalaxyPublishError(
                'Network error while transferring file "%s" to Galaxy server (%s): %s' %
                (archive_path, self.galaxy_context.server['url'], str(exc)),
                archive_path=archive_path
            )

        # 202 'Accepted'
        if resp.status_code == 202:
            # FIXME: return the data instead of the text, ie return resp.json()
            return resp.text
        else:
            raise exceptions.GalaxyPublishError(
                'Error transferring file "%s" to Galaxy server (%s): %s - %s' %
                (archive_path, self.galaxy_context.server['url'], resp.status_code, resp.reason),
                archive_path=archive_path
            )
