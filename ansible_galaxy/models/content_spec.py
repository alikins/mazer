
class ContentSpec(object):
    '''The info used to identify and reference a galaxy content.

    For ex, 'testing.ansible-testing-content' will result in
    a ContentSpec(name=ansible-testing-content, repo=ansible-testing-content,
                  namespace=testing, raw=testing.ansible-testing-content)'''
    def __init__(self,
                 name=None,
                 sub_name=None,  # FIXME: rm
                 spec_string=None,
                 src=None,       # FIXME: rm
                 namespace=None,
                 repo=None,
                 version=None,
                 scm=None):
        self.name = name
        self.spec_string = spec_string
        self.namespace = namespace
        self.repo = repo
        self.version = version
        self.scm = scm
        self.src = src
        self.sub_name = sub_name

    def __eq__(self, other):
        return (self.name, self.namespace, self.version, self.src, self.scm) == \
            (other.name, other.namespace, other.version, other.src, other.scm)

    def __repr__(self):
        format_ = 'ContentSpec(name=%s, namespace=%s, version=%s, src=%s, scm=%s, spec_string=%s)'

        return format_ % (self.name, self.namespace, self.version, self.src, self.scm, self.spec_string)
