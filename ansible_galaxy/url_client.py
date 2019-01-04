import json
import logging
import sys
import uuid

from six.moves.urllib.error import HTTPError
import socket
import ssl

from ansible_galaxy import __version__ as mazer_version
from ansible_galaxy import exceptions
from ansible_galaxy.flat_rest_api.urls import open_url
from ansible_galaxy.utils.text import to_text

log = logging.getLogger(__name__)
http_log = logging.getLogger('%s.(url).(general)' % __name__)
request_log = logging.getLogger('%s.(url).(request)' % __name__)
response_log = logging.getLogger('%s.(url).(response)' % __name__)

USER_AGENT_FORMAT = 'Mazer/{version} ({platform}; python:{py_major}.{py_minor}.{py_micro}) ansible_galaxy/{version}'


# TODO: mv to own module?
def user_agent():
    user_agent_data = {'version': mazer_version,
                       'platform': sys.platform,
                       'py_major': sys.version_info.major,
                       'py_minor': sys.version_info.minor,
                       'py_micro': sys.version_info.micro}
    return USER_AGENT_FORMAT.format(**user_agent_data)


class URLClient(object):
    ''' This class is meant to be used as a API client for an Ansible Galaxy server '''

    # FIXME: just pass in server_url
    def __init__(self, galaxy):
        self.galaxy = galaxy

        # log.debug('galaxy: %s', galaxy)
        log.debug('Using galaxy server URL %s with ignore_certs=%s', galaxy.server['url'], galaxy.server['ignore_certs'])

        self._validate_certs = not galaxy.server['ignore_certs']

        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        # set the API server
        self._api_server = galaxy.server['url']

        # self.log.debug('Validate TLS certificates for %s: %s', self._api_server, self._validate_certs)

        self.user_agent = user_agent()
        log.debug('User Agent: %s', self.user_agent)

    # TODO: raise an API/net specific exception?
    def request(self, url, args=None, headers=None, http_method=None):
        http_method = http_method or 'GET'
        headers = headers or {}
        request_id = uuid.uuid4().hex
        headers['X-Request-ID'] = request_id

        # The slug we use to identify a request by method, url and request id
        # For ex, '"GET https://galaxy.ansible.com/api/v1/repositories" c48937f4e8e849828772c4a0ce0fd5ed'
        request_slug = '"%s %s" %s' % (http_method, url, request_id)

        try:
            # log the http request_slug with request_id to the main log and
            # to the http log, both at INFO level for now.
            http_log.info('%s', request_slug)
            self.log.info('%s', request_slug)

            request_log.debug('%s args=%s', request_slug, args)
            request_log.debug('%s headers=%s', request_slug, headers)

            resp = open_url(url, data=args, validate_certs=self._validate_certs,
                            headers=headers, method=http_method,
                            http_agent=self.user_agent,
                            timeout=20)

            response_log.info('%s http_status=%s', request_slug, resp.getcode())

            final_url = resp.geturl()
            if final_url != url:
                request_log.debug('%s Redirected to: %s', request_slug, resp.geturl())

            resp_info = resp.info()
            response_log.debug('%s info:\n%s', request_slug, resp_info)

            data = resp
        except HTTPError as http_exc:
            self.log.debug('Exception on %s', request_slug)
            self.log.exception("%s: %s", request_slug, http_exc)

            # FIXME: probably need a try/except here if the response body isnt json which
            #        can happen if a proxy mangles the response
            res = json.loads(to_text(http_exc.fp.read(), errors='surrogate_or_strict'))

            http_log.error('%s data from server error response:\n%s', request_slug, res)

            try:
                error_msg = 'HTTP error on request %s: %s' % (request_slug, res['detail'])
                raise exceptions.GalaxyClientError(error_msg)
            except (KeyError, TypeError) as detail_parse_exc:
                self.log.exception("%s: %s", request_slug, detail_parse_exc)
                self.log.warning('Unable to parse error detail from response for request: %s response:  %s', request_slug, detail_parse_exc)

            # TODO: great place to be able to use 'raise from'
            # FIXME: this needs to be tweaked so the
            raise exceptions.GalaxyClientError(http_exc)
        except (ssl.SSLError, socket.error) as e:
            self.log.debug('Connection error to Galaxy API for request %s: %s', request_slug, e)
            self.log.exception("%s: %s", request_slug, e)
            raise exceptions.GalaxyClientAPIConnectionError('Connection error to Galaxy API for request %s: %s' % (request_slug, e))

        return data
