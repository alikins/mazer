import logging

from ansible_galaxy.fetch import base
# mv details of this here
from ansible_galaxy.utils import scm_archive


log = logging.getLogger(__name__)


class ScmUrlFetch(base.BaseFetch):
    fetch_method = 'scm_url'

    def __init__(self, requirement_spec):
        super(ScmUrlFetch, self).__init__()

        self.requirement_spec = requirement_spec

        self.remote_resource = requirement_spec.src

    # scm
    def find(self):
        results = {'content': {'galaxy_namespace': self.requirement_spec.namespace,
                               'repo_name': self.requirement_spec.name},
                   }

        # Could use something like:
        #    git ls-remote --refs --sort="version:refname" \
        #       --tags https://github.com/alikins/collection_ntp \*
        # To get a list of the tags on the target scm_url before cloning it,
        # and do some rudimentary version compares to find the matching version.
        #
        # And then include that version in scm_version.
        # Not sure what makes sense for cases with no version spec, that are likely
        # to match 'master'. Suppose it could always use the last tagged version, but
        # that may not be expected.
        #
        # We need some real version matched to the requirement spec version spec, so that
        # we can find the repo after it is installed. ie, 'you said any version, so I picked
        # version 1.2.3" so that (potentially) fetch() can use the version, but more importantly
        # so we know what version find() claims is _supposed_ to be install, so we can search the installed repos
        # and verify that particular version was installed. And versions/version specs have
        # to be semver, so 'master' etc doesn't work.

        # Or reintroduce special cases for 'master' or shasums etc.

        # Or we could do the scm clone during the find() step (that would verify that
        # scm url points to something).

        results['custom'] = {'scm_url': self.requirement_spec.src,
                             # TODO,maybe: In theory, we could see if we can match the
                             # version_spec against 'versions' we could try to get from scm
                             # ie, we could fetch the scm tags and consider them available
                             # versions. If we do that and find a matching version, we
                             # could return it in 'scm_version'.
                             #
                             # The semver 'version_spec' is kind of incompatible with
                             # specifying potential "versions" as things like
                             # 'the-stable-branch' or 'feab3de3a'
                             'scm_version_spec': self.requirement_spec.version_spec,
                             'scm_version': None,
                             'scm_version_aka': self.requirement_spec.version_aka}

        return results

    def fetch(self, find_results=None):
        log.debug('find_results: %s', find_results)
        find_results = find_results or {}

        # Check the find_results to see if it happened to resolve the version_spec to
        # a particular scm identifier <narrator>It did not.</a>
        scm_version = find_results['custom'].get('scm_version', None)

        repository_archive_path = scm_archive.scm_archive_content(src=self.requirement_spec.src,
                                                                  scm=self.requirement_spec.scm,
                                                                  name=self.requirement_spec.name,
                                                                  version=scm_version)
        self.local_path = repository_archive_path

        log.debug('repository_archive_path=%s', repository_archive_path)

        results = {'archive_path': repository_archive_path,
                   'download_url': self.requirement_spec.src,
                   'fetch_method': self.fetch_method}
        results['content'] = find_results['content']
        results['custom'] = find_results.get('custom', {})
        results['custom']['scm_url'] = self.requirement_spec.src

        # TODO: what the heck should the version be for a scm_url if one wasnt specified?
        return results
