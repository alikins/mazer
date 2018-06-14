import logging

from ansible_galaxy.models.content_spec import ContentSpec
from ansible_galaxy.utils import yaml_parse

log = logging.getLogger(__name__)


def content_spec_from_string(content_spec_string):
    content_spec_data = yaml_parse.parse_content_spec_string(content_spec_string)

    log.debug('content_spec_data: %s', content_spec_data)

    content_spec_ = ContentSpec(**content_spec_data)

    log.debug('content_spec_: %s', content_spec_)

    return content_spec_
