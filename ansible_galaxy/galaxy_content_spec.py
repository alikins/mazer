import logging

from ansible_galaxy import exceptions
from ansible_galaxy import content_spec_parse

log = logging.getLogger(__name__)


def parse_string(content_spec_text, valid_keywords=None):
    '''Given a text/str object describing a galaxy content, parse it.

    And return a dict with keys: 'name', 'namespace_and_name', 'version'
    '''

    valid_keywords = valid_keywords or ('namespace_and_name', 'version', 'name')
    data = {'src': None,
            'name': None,
            'namespace': None,
            'version': None,
            'spec_string': None}

    # FIXME: string/text naming consistency
    data['spec_string'] = content_spec_text

    split_data = content_spec_parse.split_content_spec(content_spec_text, valid_keywords)
    log.debug('split_data: %s', split_data)

    namespace_and_name = split_data.pop('namespace_and_name')
    data.update(split_data)

    # split the name on '.' and recombine the first 1 or 2
    name_parts = namespace_and_name.split('.')

    # if we have namespace.name, pop off namespace and use rest for name
    if len(name_parts) < 2:
        # TODO: a GalaxyContentSpecError ?
        raise exceptions.GalaxyError('A galaxy content spec must have at least a namespace, a dot, and a name but "%s" does not.'
                                     % content_spec_text)

    data['namespace'] = name_parts[0]

    # use the second part of namespace.name if there wasnt an explicit name=foo
    if not data['name']:
        data['name'] = name_parts[1]

    data['src'] = '%s.%s' % (data['namespace'], data['name'])
    log.debug('parsed content_spec_text="%s" into: %s', content_spec_text, data)
    return data
