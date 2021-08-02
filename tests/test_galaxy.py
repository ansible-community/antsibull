import asyncio
import json
from collections import namedtuple

from semantic_version import Version

import pytest
from asynctest import CoroutineMock
from aiohttp_utils import CaseControlledTestServer, http_redirect
from certificate_utils import ssl_certificate

from antsibull.galaxy import GalaxyClient, NoSuchVersion


SAMPLE_VERSIONS = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {
            "version": "0.1.1",
            "href": "https://galaxy.ansible.com/api/v2/collections/community/general/versions/0.1.1/"
        },
        {
            "version": "2.0.0-b2",
            "href": "https://galaxy.ansible.com/api/v2/collections/community/general/versions/2.0.0-b2/"
        },
        {
            "version": "3.0.0-b2",
            "href": "https://galaxy.ansible.com/api/v2/collections/community/general/versions/3.0.0-b2/"
        },
        {
            "version": "3.1.0",
            "href": "https://galaxy.ansible.com/api/v2/collections/community/general/versions/3.1.0/"
        },
        {
            "version": "3.2.0-b1",
            "href": "https://galaxy.ansible.com/api/v2/collections/community/general/versions/3.1.0/"
        },
        {
            "version": "4.0.0",
            "href": "https://galaxy.ansible.com/api/v2/collections/community/general/versions/4.0.0/"
        },
    ]
}


FakeGalaxy = namedtuple('FakeGalaxy', ('session', 'server'))

@pytest.fixture
async def fake_galaxy(http_redirect, ssl_certificate):
    ''' An HTTP ClientSession fixture that redirects requests to local test servers '''
    async with CaseControlledTestServer(ssl=ssl_certificate.server_context()) as server:
        http_redirect.add_server('galaxy.ansible.com', 443, server.port)
        yield FakeGalaxy(session=http_redirect.session, server=server)


@pytest.mark.asyncio
async def test_get_collection_version_info(fake_galaxy):
    gc = GalaxyClient(aio_session=fake_galaxy.session)
    task = asyncio.ensure_future(gc.get_versions('community.general'))

    request = await fake_galaxy.server.receive_request(timeout=5)
    assert request.path_qs == '/api/v2/collections/community/general/versions/?format=json&page_size=100'

    fake_galaxy.server.send_response(request, text=json.dumps(SAMPLE_VERSIONS),
                                     headers={'Content-Type': 'application/json'})
    assert await task == ['0.1.1', '2.0.0-b2', '3.0.0-b2', '3.1.0', '3.2.0-b1', '4.0.0']


@pytest.mark.parametrize('pre, spec, version', ((True, '>=2.0.0-b1,<3.0.0', '2.0.0-b2'),
                                                (True, '>=2.0.0-b2,<3.0.0', '2.0.0-b2'),
                                                (False, '>=3.0.0-b1,<4.0.0', '3.1.0'),
                                                # Check that we prefer the non-prerelease
                                                (True, '>=3.0.0-b1,<4.0.0', '3.1.0'),
                                                ))
@pytest.mark.asyncio
async def test_get_latest_matching_version(fake_galaxy, pre, spec, version):
    """Test that we find the correct version."""
    gc = GalaxyClient(aio_session=fake_galaxy.session)
    task = asyncio.ensure_future(gc.get_latest_matching_version('community.general', spec, pre=pre))

    request = await fake_galaxy.server.receive_request(timeout=5)
    assert request.path_qs == '/api/v2/collections/community/general/versions/?format=json&page_size=100'

    fake_galaxy.server.send_response(request, text=json.dumps(SAMPLE_VERSIONS),
                            headers={'Content-Type': 'application/json'})
    assert await task == Version(version)


@pytest.mark.parametrize('pre, spec', ((False, '>=2.0.0-b1,<3.0.0'),
                                       (True, '>=1.0.0,<2.0.0'),
                                       ))
@pytest.mark.asyncio
async def test_get_latest_matching_version_no_match(fake_galaxy, pre, spec):
    """Test that NoSuchVersion is raised when there's no matching version."""
    gc = GalaxyClient(aio_session=fake_galaxy.session)
    task = asyncio.ensure_future(gc.get_latest_matching_version('community.general', spec, pre=pre))

    request = await fake_galaxy.server.receive_request(timeout=5)
    assert request.path_qs == '/api/v2/collections/community/general/versions/?format=json&page_size=100'

    fake_galaxy.server.send_response(request, text=json.dumps(SAMPLE_VERSIONS),
                            headers={'Content-Type': 'application/json'})
    with pytest.raises(NoSuchVersion):
        await task
