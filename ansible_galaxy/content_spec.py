import logging
import os

from ansible_galaxy import galaxy_content_spec
from ansible_galaxy import content_spec_parse
from ansible_galaxy.models.content_spec import ContentSpec

log = logging.getLogger(__name__)


def is_scm(content_spec_string):
    if '://' in content_spec_string or '@' in content_spec_string:
        return True

    return False


# FIXME: do we have an enum like class for py2.6? worth a dep?
class FetchMethods(object):
    SCM_URL = 'SCM_URL'
    LOCAL_FILE = 'LOCAL_FILE'
    REMOTE_URL = 'REMOTE_URL'
    GALAXY_URL = 'GALAXY_URL'


def choose_content_fetch_method(content_spec_string):
    log.debug('content_spec_string: %s', content_spec_string)

    if is_scm(content_spec_string):
        # create tar file from scm url
        return FetchMethods.SCM_URL

    comma_parts = content_spec_string.split(',', 1)
    potential_filename = comma_parts[0]
    if os.path.isfile(potential_filename):
        # installing a local tar.gz
        return FetchMethods.LOCAL_FILE

    if '://' in content_spec_string:
        return FetchMethods.REMOTE_URL

    # if it doesnt look like anything else, assume it's galaxy
    return FetchMethods.GALAXY_URL


def content_spec_from_string(content_spec_string):
    fetch_method = choose_content_fetch_method(content_spec_string)

    log.debug('fetch_method: %s', fetch_method)

    if fetch_method == FetchMethods.GALAXY_URL:
        spec_data = galaxy_content_spec.parse_string(content_spec_string)
    else:
        spec_data = content_spec_parse.parse_string(content_spec_string)

    spec_data['fetch_method'] = fetch_method
    return ContentSpec(**spec_data)
