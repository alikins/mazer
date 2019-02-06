import logging

log = logging.getLogger(__name__)


# TODO: abc?
class Match(object):
    '''A callable condition/match

    self.match(other) should return a bool'''

    def __call__(self, other):
        return self.match(other)

    def match(self, other):
        return True


class MatchAll(Match):
    def match(self, other):
        return True


class MatchNone(Match):
    def match(self, other):
        return False


class MatchNames(Match):
    def __init__(self, names):
        self.names = names

    def match(self, other):
        return other.repository_spec.name in self.names


class MatchLabels(Match):
    def __init__(self, labels):
        self.labels = labels

    def match(self, other):
        return other.repository_spec.label in self.labels


class MatchRepositoryToRequirementSpec(Match):
    def __init__(self, requirement_specs):
        self.requirement_specs = requirement_specs
        log.debug('req_specs: %s', self.requirement_specs)

    def match(self, other):
        for req_spec in self.requirement_specs:
            if other.repository_spec.namespace != req_spec.namespace or \
                    other.repository_spec.name != req_spec.name or \
                    not req_spec.version_spec.match(other.repository_spec.version):
                log.debug('other: %s did not match %s', other, req_spec)
                return False
        return True
        # return other.requirement_spec in self.requirement_specs


class MatchRepositorySpec(Match):
    def __init__(self, repository_specs):
        self.repository_specs = repository_specs or []
        log.debug('repo_specs: %s', self.repository_specs)

    def match(self, other):
        res = other.repository_spec in self.repository_specs
        return res


class MatchRepositorySpecNamespaceName(Match):
    def __init__(self, repository_specs):
        self.namespaces_names = [(x.namespace, x.name) for x in repository_specs] or []

    def match(self, other):
        ns_n_match_res = False
        other_ns_n = (other.repository_spec.namespace, other.repository_spec.name)
        ns_n_match_res = other_ns_n in self.namespaces_names

        return ns_n_match_res


class MatchRepositorySpecNamespaceNameVersion(Match):
    def __init__(self, repository_specs):
        self.namespaces_names_versions = [(x.namespace, x.name, x.version) for x in repository_specs] or []
        self.namespaces_names = [(x.namespace, x.name) for x in repository_specs] or []

    def match(self, other):
        ns_n_v_match_res = False

        other_ns_n_v = (other.repository_spec.namespace, other.repository_spec.name, other.repository_spec.version)

        ns_n_v_match_res = other_ns_n_v in self.namespaces_names_versions

        return ns_n_v_match_res


class MatchNamespace(Match):
    def __init__(self, namespaces_to_match):
        self.namespaces_to_match = namespaces_to_match or []

    def match(self, other):
        res = other.namespace in self.namespaces_to_match
        return res


class MatchNamespacesOrLabels(Match):
    def __init__(self, namespaces_or_labels):
        self.namespaces_or_labels = namespaces_or_labels or []

    def match(self, other):
        # TODO: should this matcher require a namespace string or a namespace object? either?
        return any([other.repository_spec.label in self.namespaces_or_labels,
                    other.repository_spec.namespace in self.namespaces_or_labels])
