import logging

import pytest

from ansible_galaxy import galaxy_content_spec
from ansible_galaxy.models.galaxy_content_spec import GalaxyContentSpec

log = logging.getLogger(__name__)

content_spec_from_string_cases = \
    [
        {'spec': 'geerlingguy.apache',
         'expected': GalaxyContentSpec(name='apache', namespace='geerlingguy')},
        {'spec': 'geerlingguy.apache,2.1.1',
         'expected': GalaxyContentSpec(name='apache', namespace='geerlingguy', version='2.1.1')},
        {'spec': 'testing.ansible-testing-content',
         'expected': GalaxyContentSpec(name='ansible-testing-content', namespace='testing')},
        {'spec': 'testing.ansible-testing-content,name=testing-content',
         'expected': GalaxyContentSpec(name='testing-content', namespace='testing')},
        {'spec': 'alikins.awx',
         'expected': GalaxyContentSpec(name='awx', namespace='alikins')},
        {'spec': 'testing.ansible-testing-content,1.2.3,name=testing-content',
         'expected': GalaxyContentSpec(name='testing-content', namespace='testing', version='1.2.3')},
        {'spec': 'testing.ansible-testing-content,1.2.3,also-testing-content,stuff',
         'expected': GalaxyContentSpec(name='also-testing-content', namespace='testing', version='1.2.3')},
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
    result = galaxy_content_spec.content_spec_from_string(content_spec_case['spec'])
    log.debug('spec=%s result=%s exp=%s', content_spec_case['spec'], result, content_spec_case['expected'])

    assert result == content_spec_case['expected']
