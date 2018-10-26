
import logging

from ansible_galaxy import display
from ansible_galaxy import matchers
from ansible_galaxy.models.content_spec import ContentSpec
from ansible_galaxy import installed_repository_db
from ansible_galaxy.utils.content_name import parse_content_name
from ansible_galaxy.utils.text import to_text

log = logging.getLogger(__name__)

SKIP_INFO_KEYS = ("name", "description", "readme_html", "related", "summary_fields", "average_aw_composite", "average_aw_score", "url")

GALAXY_REPOSITORY_TEMPLATE = """
label: {repo_label}
namespace: {repo_namespace}
name: {repo_name}
format: {repo_format}
latest_version: {repo_latest_version}
description: {repo_description}
scm: {repo_clone_url}

{repo_contents}"""

INSTALLED_REPOSITORY_TEMPLATE = """namespace: {repository.content_spec.namespace}
name: {repository.content_spec.name}
version: {repository.content_spec.version}
path: {repository.path}
scm: {repository.content_spec.scm}
"""


CONTENT_TEMPLATE = """    content_name: {content_name}
    content_type: {content_type}
    description: {content_description}
"""


INSTALLED_CONTENT_TEMPLATE = """
name: {name}
version: {version}"""


# FIXME: format?
def _repr_remote_repo(remote_data):
    # log.debug('remote_data: %s', remote_data)

    # flatten some info for format simplicity
    repo_namespace = remote_data['summary_fields']['namespace']['name']
    repo_name = remote_data['name']
    remote_data['repo_label'] = "{namespace}.{name}".format(namespace=repo_namespace, name=repo_name)
    remote_data['repo_namespace'] = remote_data['summary_fields']['namespace']['name']
    remote_data['repo_description'] = remote_data['description']
    remote_data['repo_clone_url'] = remote_data['clone_url']
    # remote_data['repo_name'] = remote_data['summary_fields']['repository']['original_name']
    remote_data['repo_name'] = remote_data['name']
    remote_data['repo_format'] = remote_data['format']

    content_info_parts = []
    content_objects = remote_data['summary_fields']['content_objects']
    for content_object in content_objects:
        content_data = {}
        content_data['content_name'] = content_object['name']
        content_data['content_type'] = content_object['content_type']
        content_data['content_description'] = content_object['description']

        content_str = CONTENT_TEMPLATE.format(**content_data)
        # log.debug('content_str: %s', content_str)
        content_info_parts.append(content_str)

    versions = remote_data['summary_fields']['versions']
    try:
        latest_version = versions[0].get('version', 'N/A')
    except IndexError:
        latest_version = ""

    remote_data['repo_latest_version'] = latest_version

    remote_data['repo_contents'] = '\n'.join(content_info_parts)

    return GALAXY_REPOSITORY_TEMPLATE.format(**remote_data)


def _repr_installed_repository(installed_repository):
    return INSTALLED_REPOSITORY_TEMPLATE.format(repository=installed_repository)


def _repr_installed_content(installed_content):
    installed_data = {'name': installed_content['installed_repository'].name,
                      'version': installed_content['version'],
                      'path': installed_content['installed_repository'].path}
    return INSTALLED_CONTENT_TEMPLATE.format(**installed_data)


def _repr_unmatched_label(unmatched_label):
    return '{0}'.format(unmatched_label)


# TODO: move to a repr for Role?
def _repr_role_info(role_info):

    text = [u"", u"Role: %s" % to_text(role_info['name'])]
    text.append(u"\tdescription: %s" % role_info.get('description', ''))

    for k in sorted(role_info.keys()):

        if k in SKIP_INFO_KEYS:
            continue

        if isinstance(role_info[k], dict):
            text.append(u"\t%s:" % (k))
            for key in sorted(role_info[k].keys()):
                if key in SKIP_INFO_KEYS:
                    continue
                text.append(u"\t\t%s: %s" % (key, role_info[k][key]))
        else:
            text.append(u"\t%s: %s" % (k, role_info[k]))

    return u'\n'.join(text)


def info_content_specs(galaxy_context,
                       api,
                       content_spec_strings,
                       display_callback=None,
                       offline=None):

    online = not offline

    display_callback = display_callback or display.display_callback

    offline = offline or False

    irdb = installed_repository_db.InstalledRepositoryDatabase(galaxy_context)

    labels_to_match = []

    all_labels_to_match = []
    for content_spec_string in content_spec_strings:
        galaxy_namespace, repository_name, content_name = parse_content_name(content_spec_string)

        log.debug('showing info for content spec: %s', content_spec_string)

        repository_name = repository_name or content_name

        if online:
            remote_data = api.lookup_repo_by_name(galaxy_namespace, repository_name)
            if remote_data:
                display_callback(_repr_remote_repo(remote_data))

        label_to_match = '%s.%s' % (galaxy_namespace, repository_name)
        all_labels_to_match.append(label_to_match)

        labels_to_match.append((label_to_match, ContentSpec(namespace=galaxy_namespace,
                                                            name=repository_name)))

    matcher = matchers.MatchContentSpec([label_and_spec[1] for label_and_spec in labels_to_match])

    matched_repositories = irdb.select(repository_match_filter=matcher)

    remote_data = False

    matched_labels = []
    for matched_repository in matched_repositories:
        display_callback(_repr_installed_repository(matched_repository))
        matched_labels.append(matched_repository.content_spec.label)

    unmatched_labels = set(all_labels_to_match).difference(set(matched_labels))

    if unmatched_labels:
        display_callback('These repositories were not found:')

        for unmatched_label in sorted(unmatched_labels):
            display_callback(_repr_unmatched_label(unmatched_label))

    return
