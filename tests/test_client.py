from aninja.client import HTTPClient, BrowserClient, launch
import pytest


def httpbin(interface=''):
    return 'http://httpbin.org'+interface


@pytest.mark.asyncio
async def test_browserclient():
    devtools = False
    client = await launch(options={'devtools': devtools})
    client.cookies_manager.set('user', 'ciri', domain='httpbin.org')
    client.cookies_manager.set('ds', 'ciweri', domain='baidu.com')

    page = await client.newPage()
    await page.goto(httpbin('/cookies/set?k1=v1&k2=v2'))
    r = await page.goto(httpbin('/cookies'))
    print(await r.text())
    assert '"k1": "v1"' in await r.text()
    assert await page.check('k2', by_selector=False)
    await client.close()
    assert False


@pytest.mark.asyncio
async def test_httpclient():

    async with HTTPClient() as client:
        resp = await client.request('http://httpbin.org/cookies/set', method='GET', params={'k1': 'v1', 'k2': 'v2'})
        assert client.cookies_manager.output_header_string() == 'k1=v1; k2=v2'
        assert '"k1": "v1"' in await resp.text()
        assert await client.check('k2', url=httpbin('/cookies/set?k1=v1&k2=v2'))
