import logging
import os

log = logging.getLogger(__name__)


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
