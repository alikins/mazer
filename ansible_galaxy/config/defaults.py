import os


def get_config_path():
    paths = [
        'mazer.yml',
        '~/.ansible/mazer.yml',
        '/etc/ansible/mazer.yml'
    ]
    for path in paths:
        if os.path.exists(os.path.expanduser(path)):
            return path
    return paths[1]


# a list of tuples that is fed to an OrderedDict
DEFAULTS = [
    ('server',
     {'url': 'https://galaxy.ansible.com',
      'ignore_certs': False}
     ),

    # shelves are static sources of galaxy content.
    # The value of 'shelves' is a list of tuples. The tuples
    # are the name of the 'shelf' (like a yum repo name) and then
    # a dict of shelf info including the  uri it lives at.
    # TODO: If useful, this will likely move to it's own config file[s]
    # TODO: RHS of 'shelves' may make more sense as a ordered list of
    #       dicts that include 'name', 'label', 'uri', etc
    ('shelves', [('system', {'uri': 'file:///usr/share/ansible/shelf'})]),

    # In order of priority
    ('content_path', '~/.ansible/content'),
    ('global_content_path', '/usr/share/ansible/content'),

    # runtime options
    ('options',
     {'role_skeleton_path': None,
      'role_skeleton_ignore': ["^.git$", "^.*/.git_keep$"]}
     ),
    ('version', 1),
]

# FIXME: replace with logging config
VERBOSITY = 0
CONFIG_FILE = get_config_path()
