import logging

from ansible_galaxy import exceptions
from ansible_galaxy.models.content_spec import ContentSpec

log = logging.getLogger(__name__)


def split_kwarg(spec_string, valid_keywords):
    if '=' not in spec_string:
        return (None, spec_string)

    parts = spec_string.split('=', 1)

    if parts[0] in valid_keywords:
        return (parts[0], parts[1])

    raise exceptions.GalaxyClientError('The content spec uses an unsuppoted keyword: %s' % spec_string)


def split_comma(spec_string, valid_keywords):
    # res = []
    comma_parts = spec_string.split(',')
    for comma_part in comma_parts:
        kw_parts = split_kwarg(comma_part, valid_keywords)
        log.debug('kw_parts: %s', kw_parts)
        yield kw_parts


def split_content_spec(spec_string, valid_keywords):
    comma_splitter = split_comma(spec_string, valid_keywords)
    info = {}
    for kw in valid_keywords:
        try:
            key, value = next(comma_splitter)
        except StopIteration:
            return info

        if key:
            info[key] = value
        else:
            info[kw] = value

    return info


def parse_content_spec_string(content_spec_text, valid_keywords=None):
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

    split_data = split_content_spec(content_spec_text, valid_keywords)
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

    log.debug('parsed content_spec_text="%s" into: %s', content_spec_text, data)
    return data


def content_spec_from_string(content_spec_string):
    content_spec_data = parse_content_spec_string(content_spec_string)

    log.debug('content_spec_data: %s', content_spec_data)

    content_spec_ = ContentSpec(**content_spec_data)

    log.debug('content_spec_: %s', content_spec_)

    return content_spec_
