import logging

from ansible_galaxy.models.context import GalaxyContext
from ansible_galaxy import rest_api

log = logging.getLogger(__name__)


def test_galaxy_api_init():

    gc = GalaxyContext()
    api = rest_api.GalaxyAPI(gc)

    assert isinstance(api, rest_api.GalaxyAPI)
    assert api.galaxy == gc
