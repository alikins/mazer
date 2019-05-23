import logging

from ansible_galaxy import collection_artifact
from ansible_galaxy import download
from ansible_galaxy import repository_spec_parse
from ansible_galaxy.models.repository_spec import FetchMethods
from ansible_galaxy.models.requirement_spec import RequirementSpec

log = logging.getLogger(__name__)


def requirement_spec_from_string(requirement_spec_string,
                                 namespace_override=None,
                                 editable=False):
    fetch_method = \
        repository_spec_parse.choose_repository_fetch_method(requirement_spec_string,
                                                             editable=editable)
    log.debug('fetch_method: %s', fetch_method)

    if fetch_method == FetchMethods.LOCAL_FILE:
        # Since we only know this is a local file we vaguely recognize, we have to
        # open it up to get any more details. We _could_ attempt to parse the file
        # name, but that rarely ends well. Filename could also be arbitrary for downloads
        # from remote urls ('mazer install http://myci.example.com/somebuildjob/latest' etc)
        spec_data = collection_artifact.load_data_from_collection_artifact(requirement_spec_string)
        spec_data['fetch_method'] = fetch_method
    elif fetch_method == FetchMethods.REMOTE_URL:
        # download the url
        # hope it is a collection artifact and use load_data_from_collection_artifact() for the
        # rest of the repo_spec data
        log.debug('requirement_spec_string: %s', requirement_spec_string)

        tmp_downloaded_path = download.fetch_url(requirement_spec_string,
                                                 # This is for random remote_urls, so always validate_certs
                                                 validate_certs=True)
        spec_data = collection_artifact.load_data_from_collection_artifact(tmp_downloaded_path)

        # pretend like this is a local_file install now
        spec_data['fetch_method'] = FetchMethods.LOCAL_FILE
    else:
        spec_data = repository_spec_parse.spec_data_from_string(requirement_spec_string,
                                                                namespace_override=namespace_override,
                                                                editable=editable)

        spec_data['fetch_method'] = fetch_method

    log.debug('spec_data: %s', spec_data)

    req_spec = RequirementSpec.from_dict(spec_data)

    return req_spec
