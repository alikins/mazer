import logging

import attr

from ansible_galaxy.models.repository_spec import ContentSpec

log = logging.getLogger(__name__)

EXAMPLE = '''
# from galaxy
- src: yatesr.timezone

# from GitHub
- src: https://github.com/bennojoy/nginx

# from GitHub, overriding the name and specifying a specific tag
- src: https://github.com/bennojoy/nginx
  version: master
  name: nginx_role

# from a webserver, where the role is packaged in a tar.gz
# - src: https://some.webserver.example.com/files/master.tar.gz
#  name: http-role

# from Bitbucket
# - src: git+https://bitbucket.org/willthames/git-ansible-galaxy
#  version: v1.4

# from Bitbucket, alternative syntax and caveats
# - src: https://bitbucket.org/willthames/hg-ansible-galaxy
#  scm: hg

# from GitLab or other git-based scm, using git+ssh
# - src: git@gitlab.company.com:mygroup/ansible-base.git
#   scm: git
#  version: "0.1"  # quoted, so YAML doesn't parse this as a floating-point value
'''


@attr.s(frozen=True)
class Requirement(object):
    name = attr.ib()
    version = attr.ib(default=None)
    src = attr.ib(default=None)
    scm = attr.ib(default=None)


@attr.s(frozen=True)
class RequirementSpec(ContentSpec):
    pass
