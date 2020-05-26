import asyncio
import json
from unittest.mock import patch

import pytest
from asynctest import CoroutineMock
from aiohttp_utils import CaseControlledTestServer, http_redirect
from certificate_utils import ssl_certificate

from antsibull.galaxy import GalaxyClient


SAMPLE_VERSIONS = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {
            "version": "0.1.1",
            "href": "https://galaxy.ansible.com/api/v2/collections/community/general/versions/0.1.1/"
        }
    ]
}


@pytest.mark.asyncio
async def test_get_collection_version_info(http_redirect, ssl_certificate):
    async with CaseControlledTestServer(ssl=ssl_certificate.server_context()) as server:
        http_redirect.add_server('galaxy.ansible.com', 443, server.port)
        gc = GalaxyClient(aio_session=http_redirect.session)
        task = asyncio.ensure_future(gc.get_versions('community.general'))

        request = await server.receive_request(timeout=5)
        assert request.path_qs == '/api/v2/collections/community/general/versions/?format=json'

        server.send_response(request, text=json.dumps(SAMPLE_VERSIONS),
                             headers={'Content-Type': 'application/json'})
        assert await task == ['0.1.1']
