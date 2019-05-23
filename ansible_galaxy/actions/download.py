import logging
import os

from ansible_galaxy import exceptions
from ansible_galaxy import requirements
from ansible_galaxy.fetch import fetch_factory

log = logging.getLogger(__name__)


def download_collection(galaxy_context,
                        requirement_to_install,
                        display_callback=None):

    requirement_spec_to_install = requirement_to_install.requirement_spec

    fetcher = fetch_factory.get(galaxy_context=galaxy_context,
                                requirement_spec=requirement_spec_to_install)

    # Do a find/check first. We could skip straight to fetch, but in theory, server side
    # can do aliases and substitutions
    try:
        find_results = fetcher.find()
    except exceptions.GalaxyError as e:
        log.debug('requirement_to_install %s failed to be met: %s', requirement_to_install, e)
        log.warning('Unable to find metadata for %s: %s', requirement_spec_to_install.label, e)

        raise


def download(galaxy_context,
             requirements_list,
             display_callback=None):
    """API equilivent of 'mazer download' command"""

    results = {'errors': [],
               'success': True,
               }

    return results


def run(galaxy_context,
        requirement_spec_strings=None,
        requirement_specs_file=None,
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

    results = download(galaxy_context,
                       requirements_list,
                       display_callback=display_callback)

    if results['errors']:
        for error in results['errors']:
            # TODO: add 'error' level for display_callback
            display_callback(error)

    if results['success']:
        return os.EX_OK  # 0

    return os.EX_SOFTWARE  # 70
