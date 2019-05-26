import logging

import attr

from ansible_galaxy.models.requirement import Requirement
from ansible_galaxy.fetch.base import BaseFetch

log = logging.getLogger(__name__)


@attr.s(frozen=True)
class FetchableRequirement(object):
    '''Associated a Requirement with a fetcher that can fetch it'''
    requirement = attr.ib(type=Requirement,
                          validator=attr.validators.instance_of(Requirement))

    fetcher = attr.ib(type=BaseFetch,
                      validator=attr.validators.instance_of(BaseFetch))
