import logging

import pytest

from ansible_galaxy import content_spec
from ansible_galaxy.models.content_spec import ContentSpec

log = logging.getLogger(__name__)

content_spec_from_string_cases = \
    [
        {'spec': 'geerlingguy.apache',
         'expected': ContentSpec(name='apache', namespace='geerlingguy')},
        {'spec': 'testing.ansible-testing-content',
         'expected': ContentSpec(name='ansible-testing-content', namespace='testing')},
        {'spec': 'alikins.awx',
         'expected': ContentSpec(name='awx', namespace='alikins')},
        # 'foo',
        # 'foo,1.2.3',
        # 'foo,version=1.2.3',
        # 'foo,1.2.3,somename',
        # 'foo,1.2.3,name=somename',
        # 'foo,1.2.3,somename,somescm',
        # 'foo,1.2.3,somename,somescm,someextra'
    ]


@pytest.fixture(scope='module',
                params=content_spec_from_string_cases,
                ids=[x['spec'] for x in content_spec_from_string_cases])
def content_spec_case(request):
    yield request.param


def test_content_spec_from_string(content_spec_case):
    result = content_spec.content_spec_from_string(content_spec_case['spec'])
    log.debug('spec=%s result=%s exp=%s', content_spec_case['spec'], result, content_spec_case['expected'])

    assert result == content_spec_case['expected']
