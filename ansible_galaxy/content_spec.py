import logging
import os

from ansible_galaxy import galaxy_content_spec
from ansible_galaxy.models.galaxy_content_spec import GalaxyContentSpec
from ansible_galaxy.utils import yaml_parse

log = logging.getLogger(__name__)


def repo_url_to_repo_name(repo_url):
    # gets the role name out of a repo like
    # http://git.example.com/repos/repo.git" => "repo"

    if '://' not in repo_url and '@' not in repo_url:
        return repo_url
    trailing_path = repo_url.split('/')[-1]
    if trailing_path.endswith('.git'):
        trailing_path = trailing_path[:-4]
    if trailing_path.endswith('.tar.gz'):
        trailing_path = trailing_path[:-7]
    if ',' in trailing_path:
        trailing_path = trailing_path.split(',')[0]
    return trailing_path


def is_scm(content_spec_string):
    if '://' in content_spec_string or '@' in content_spec_string:
        return True

    return False


def determine_content_spec_type(content_spec_string):
    pass


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

    if os.path.isfile(content_spec_string):
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
        spec_data = galaxy_content_spec.parse_content_spec_string(content_spec_string)
    else:
        spec_data = yaml_parse.parse_content_spec_string(content_spec_string)

    spec_data['fetch_method'] = fetch_method
    return GalaxyContentSpec(**spec_data)
