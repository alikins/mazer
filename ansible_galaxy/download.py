import errno
import logging
import tempfile

from six.moves.urllib.error import URLError
from six import PY2

from ansible_galaxy import exceptions
from ansible_galaxy.flat_rest_api.urls import open_url

log = logging.getLogger(__name__)


# FIXME: let the archive_url be passed in
def fetch_url(archive_url, validate_certs=True):
    """
    Downloads the archived content from github to a temp location
    """

    log.debug('Downloading archive_url: %s', archive_url)
    # TODO: should probably be based on/shared with rest API client code, so that
    #       content downloads could support any thing the rest code does
    #       (ie, any TLS cert setup, proxy config, auth options, etc)
    # WHEN: if we change the underlying http client impl at least
    try:
        url_file = open_url(archive_url, validate_certs=validate_certs)

        temp_file = tempfile.NamedTemporaryFile(delete=False,
                                                prefix='tmp-ansible-galaxy-content-archive-',
                                                suffix='.tar.gz')

        data = url_file.read()
        while data:
            temp_file.write(data)
            data = url_file.read()
        temp_file.close()
        return temp_file.name
    except Exception as e:
        # FIXME: there is a ton of reasons a download and save could fail so could likely provided better errors here
        log.exception(e)
        raise exceptions.GalaxyDownloadError(e, url=archive_url)

    return False


def url_exists(archive_url, validate_certs=True):
    log.debug('Downloading archive_url: %s', archive_url)

    try:
        open_url(archive_url, validate_certs=validate_certs)
        return True
    except URLError as e:
        import pprint
        log.debug('e: %s', pprint.pformat(e.__dict__))
        log.debug('e.errno: %s', e.errno)
        log.debug('PY2: %s', PY2)
        if PY2:
            # On PY2 we get a URLError that is subclass of OSError with it's errno set
            # but on PY3 we get a URLError with a 'reason' attribute that is an OSError with errno
            # and the URLError itself doesn't have it's errno attribute set.
            # For file:// urls, we get an exception with errno 21 for 'is a directory'
            # but for this case, a directory that exists is fine, so return true
            if e.errno == errno.EISDIR:
                return True
            raise

        # For file:// urls, we get an exception with errno 21 for 'is a directory'
        # but for this case, a directory that exists is fine, so return true
        if e.reason and e.reason.errno == errno.EISDIR:
            log.debug('got URLError with a OSError with errno as its reason attr, returning True')
            return True
        raise
    except (IOError, OSError) as e:
        log.debug('e.errno: %s', e.errno)
        # For file:// urls, we get an exception with errno 21 for 'is a directory'
        # but for this case, a directory that exists is fine, so return true
        if e.errno == errno.EISDIR:
            return True

        raise
        # import pdb; pdb.set_trace()
        # log.exception(e)
        # raise exceptions.GalaxyDownloadError(e, url=archive_url)
    except Exception as e:
        # FIXME: there is a ton of reasons a download and save could fail so could likely provided better errors here
        log.exception(e)
        raise exceptions.GalaxyDownloadError(e, url=archive_url)
