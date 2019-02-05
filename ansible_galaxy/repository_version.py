import logging

import semantic_version

from ansible_galaxy import exceptions
from ansible_galaxy.utils.version import normalize_version_string

log = logging.getLogger(__name__)


def sort_versions(versions):
    # list of tuples of loose_version and original string, the sort
    # will sort based on first value of tuple, then we return just the
    # original strings
    semver_versions = [(semantic_version.Version(a), a) for a in versions]
    semver_versions.sort()
    return [v[1] for v in semver_versions]


# TODO: somewhere we need to have a code path for the ordered version list returned from server
#       and another for the versions we got elsewhere.
def get_latest_version(available_normalized_versions, content_data):
    # and sort them to get the latest version. If there
    # are no versions in the list, we'll grab the head
    # of the master branch
    if available_normalized_versions:
        try:
            sorted_versions = sort_versions(available_normalized_versions)
        except (TypeError, ValueError) as e:
            log.exception(e)
            raise exceptions.GalaxyClientError(
                'Unable to compare content versions (%s) to determine the most recent version due to incompatible version formats. '
                'Please contact the content author to resolve versioning conflicts, or specify an explicit content version to install. '
                'The version error was: "%s"' % (', '.join(available_normalized_versions), e)
            )

        content_version = sorted_versions[-1]
    # FIXME: follow 'repository' branch and it's ['import_branch'] ?
    elif content_data.get('github_branch', None):
        content_version = content_data['github_branch']
    else:
        content_version = 'master'

    return content_version


def normalize_versions(content_versions):
    '''Return a list of tuples of (normalized_version, origin) for content_versions

    'normalized' in this case meaning stripping any leave 'v' from the version field.
    We have to support both for role requirements compat for now'''

    # a list of tuples of (normalized_version, original_version) for building
    # map of normalized version to original version
    normalized_versions = [(normalize_version_string(x), x) for x in content_versions]

    available_normalized_versions = [v[0] for v in normalized_versions]

    # map the 'normalized' version back to the original version string, we need it for
    # content archive download urls
    norm_to_orig_map = dict(normalized_versions)

    return (available_normalized_versions, norm_to_orig_map)


def validate_versions(content_versions):
    valid_versions = []
    invalid_versions = []
    for version in content_versions:
        if not semantic_version.validate(version):
            log.warning('The version string "%s" is not valid, skipping.', version)
            invalid_versions.append(version)
            continue
        valid_versions.append(version)

    return (valid_versions, invalid_versions)


def get_repository_version(repository_data, version_spec, repository_versions, content_content_name):
    '''find and compare repository version found in repository_data dict

    repository_data is a dict based on /api/v1/repositories/13 for ex
    content_content_data is the name of the content specified by user?
    version is the version string asked for by user
    content_versions is a list of version strings in order
    '''

    log.debug('%s wants ver: %s type: %s', content_content_name, version_spec, type(version_spec))
#    log.debug('%s vers avail: %s',
#              content_content_name, json.dumps(content_versions, indent=2))

    # normalize versions, but also build a map of the normalized version string to the orig string
    available_normalized_versions, norm_to_orig_map = normalize_versions(repository_versions)

    # verify that the normalized versions are valid semver now so that we dont worry about it
    # in the sort
    available_versions, dummy = \
        validate_versions(available_normalized_versions)

    # FIXME: support direct semver usage all the way through
    # str or semver to string, but leave None alone
    if version_spec:
        version_spec_str = str(version_spec)

    # TODO: remove all of this code. It doesn't make much sense to try to normalize
    # an implementation specific semver match spec string ('==1.0.0' or '>=1.2.3' etc)
    normalized_version_spec = normalize_version_string(version_spec_str)

    log.debug('normalized_version_spec: %s', normalized_version_spec)
#    log.debug('avail_normalized_versions: %s', json.dumps(available_normalized_versions, indent=4))

    # we specified a particular version is required so look for it in available versions
    # FIXME: remove all the logic for attempting to guess what the right default branch is
    #        since it doesn't mean anything for only collections
    #         # FIXME: should we show the actual available versions or the available
    #         #        versions we searched in?  act: ['v1.0.0', '1.1'] nor: ['1.0.0', '1.1']
    #         msg = "- The list of available versions for %s is empty (%s)." % \
    #             (content_content_name or 'content', available_versions)
    #         raise exceptions.GalaxyError(msg)

    #     # FIXME: convert to Spec.select()
    #     #     #       in actual version tags or ones we made up without the leading v'
    #     #     msg = "- the specified version (%s) of %s was not found in the list of available versions (%s)." % \
    #     #         (version, content_content_name or 'content', available_versions)
    #     #     raise exceptions.GalaxyError(msg)

    #     # if we get here, 'version' is in available_normalized_versions
    #     # return the exact match version since it was available

    #     # FIXME
    #     # orig_version = norm_to_orig_map[normalized_version]
    #     # log.debug('%s requested ver: %s, matched: %s, using real ver: %s ', content_content_name, version, normalized_version, orig_version)
    #     # return orig_version
    #     return normalized_version

    semver_available_versions = [semantic_version.Version(v) for v in available_versions]
    content_version = version_spec.select(semver_available_versions)
    # At this point, we have a list of the available versions. The available versions have
    # been normalized (leading 'v' or 'V' stripped off).
    # No specific version was requested, so we return the latest one.
    # content_version = get_latest_version(available_versions, repository_data)

    log.debug('%s using latest ver: %s', content_content_name, content_version)
    return content_version
