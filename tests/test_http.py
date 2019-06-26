from aninja.http import HTTPClient
import pytest


def httpbin(interface=''):
    return 'http://httpbin.org'+interface


@pytest.mark.asyncio
async def test_httpclient():

    async with HTTPClient() as client:
        resp = await client.request(method='GET',
                                    url=httpbin('/cookies/set'),
                                    params={'k1': 'v1', 'k2': 'v2'})
        assert client.cookies_manager.output_header_string() == 'k1=v1; k2=v2'
        assert '"k1": "v1"' in await resp.text()
        assert await client.check('k2', url=httpbin('/cookies/set?k1=v1&k2=v2'))
