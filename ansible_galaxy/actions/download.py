import logging
import os
import shutil

from ansible_galaxy import build  # For the artifact filename templates
from ansible_galaxy import exceptions
from ansible_galaxy import requirements
from ansible_galaxy import repository_spec
from ansible_galaxy.fetch import fetch_factory

log = logging.getLogger(__name__)


def artifact_filename(repository_spec):
    artifact_filename = \
        build.ARCHIVE_FILENAME_TEMPLATE.format(namespace=repository_spec.namespace,
                                               name=repository_spec.name,
                                               version=repository_spec.version,
                                               extension=build.ARCHIVE_FILENAME_EXTENSION)
    return artifact_filename


def download_requirement(galaxy_context,
                         requirement_to_install,
                         full_destination_path,
                         display_callback=None):

    requirement_spec_to_install = requirement_to_install.requirement_spec

    fetcher = fetch_factory.get(galaxy_context=galaxy_context,
                                requirement_spec=requirement_spec_to_install)

    # Do a find/check first. We could skip straight to fetch, but in theory, server side
    # can do aliases and substitutions
    try:
        # Note: This can mutate fetch.requirement_spec as a side effect
        find_results = fetcher.find()
    except exceptions.GalaxyError as e:
        log.debug('requirement_to_install %s failed to be met: %s', requirement_to_install, e)
        log.warning('Unable to find metadata for %s: %s', requirement_spec_to_install.label, e)

        raise

    repository_spec_to_install = \
        repository_spec.repository_spec_from_find_results(find_results,
                                                          requirement_spec_to_install)

    log.debug('repository_spec_to_install: %s', repository_spec_to_install)

    import pprint
    log.debug('find_results:\n%s', pprint.pformat(find_results))

    artifact_basename = artifact_filename(repository_spec_to_install)
    log.debug('artifact_basename: %s', artifact_basename)

    try:
        fetch_results = fetcher.fetch(find_results=find_results)

        log.debug('fetch_results: %s', fetch_results)

        # fetch_results will include a 'archive_path' pointing to where the artifact
        # was saved to locally.
    except exceptions.GalaxyError as e:
        # fetch error probably should just go to a FAILED state, at least until
        # we have to implement retries

        log.warning('Unable to fetch %s: %s',
                    repository_spec_to_install.name,
                    e)

        raise

    tmp_artifact_filename = fetch_results['archive_path']

    full_artifact_dest_filename = os.path.join(full_destination_path, artifact_basename)

    res = shutil.move(tmp_artifact_filename, full_artifact_dest_filename)
    log.debug('move res: %s', res)

    display_callback('Downloaded %s to %s' % (repository_spec_to_install, full_artifact_dest_filename))
    # copy/mv the tmp file to dest-dir/artifact_basename

    return full_artifact_dest_filename


def download(galaxy_context,
             requirements_list,
             full_destination_path,
             display_callback=None):
    """API equilivent of 'mazer download' command"""

    results = {'errors': [],
               'success': True,
               }

    for requirement in requirements_list:
        res = download_requirement(galaxy_context,
                                   requirement,
                                   full_destination_path,
                                   display_callback=display_callback)
        log.debug('res: %s', res)

    return results


def run(galaxy_context,
        requirement_spec_strings=None,
        requirement_specs_file=None,
        destination_path=None,
        display_callback=None):
    """Emulate running 'mazer download' from cli.

    Returns:
        0: Worked
    """

    # TODO: convert requirement_spec_strings and/or requirement_specs_file into
    #       a requirements_list
    requirements_list = []

    if requirement_spec_strings:
        requirements_list += \
            requirements.requirements_from_strings(repository_spec_strings=requirement_spec_strings)

    if requirement_specs_file:
        # TODO: implement req file
        pass

    real_destination_path = destination_path or os.getcwd()
    full_destination_path = os.path.abspath(os.path.expanduser(real_destination_path))

    results = download(galaxy_context,
                       requirements_list,
                       full_destination_path,
                       display_callback=display_callback)

    if results['errors']:
        for error in results['errors']:
            # TODO: add 'error' level for display_callback
            display_callback(error)

    if results['success']:
        return os.EX_OK  # 0

    return os.EX_SOFTWARE  # 70
