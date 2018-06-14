import logging

from ansible_galaxy import exceptions

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


def parse_string(content_spec_text, valid_keywords=None):
    '''Given a text/str object describing a galaxy content, parse it.

    And return a dict with keys: 'name', 'src', 'scm', 'version'
    '''

    valid_keywords = valid_keywords or ('src', 'version', 'name', 'scm')
    data = {'src': None,
            'name': None,
            # 'sub_name': None,
            'version': None,
            'scm': None}
    split_data = split_content_spec(content_spec_text, valid_keywords)

    data.update(split_data)

    if data['name'] is None:
        scm_name = repo_url_to_repo_name(data['src'])
        data['name'] = scm_name
        if '+' in data['src']:
            (scm_url, scm_src) = data['src'].split('+', 1)
            data['scm'] = scm_url
            data['src'] = scm_src

    # split the name on '.' and recombine the first 1 or 2
    name_parts = data['name'].split('.')
    new_name_parts = []
    new_name_parts.append(name_parts.pop(0))

    # we may not have a second part to the name
    try:
        new_name_parts.append(name_parts.pop(0))
    except IndexError:
        pass

    # combine the name parts, which may be one or two parts
    data['name'] = '.'.join(new_name_parts)

    return data
