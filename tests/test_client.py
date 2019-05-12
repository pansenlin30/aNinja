from aninja.client import Client
import pytest


def httpbin(interface=''):
    return 'http://httpbin.org'+interface



@pytest.mark.asyncio
async def test_page_client():
    client = Client()
    client.cookies_manager.set('user', 'ciri', domain='httpbin.org')
    client.cookies_manager.set('ds', 'ciweri', domain='baidu.com')

    devtools = False
    await client.prepare_page({'devtools':devtools})
    await client.goto(httpbin('/cookies/set?k1=v1&k2=v2'))
    await client.close(mode=0)
    await client.prepare_page({'devtools':devtools})
    r = await client.goto(httpbin('/cookies'))
    assert '"k1": "v1"' in await r.text()
    assert await client.page_check('k2', by_selector=False)
    await client.close(mode=0)


@pytest.mark.asyncio
async def test_session_client():
    client = Client()
    await client.prepare_session()

    resp = await client.get(httpbin('/cookies/set?k1=v1&k2=v2'))
    assert client.cookies_manager.output_header_string() == 'k1=v1; k2=v2'
    assert '"k1": "v1"' in await resp.text()
    assert await client.session_check('k2',url=httpbin('/cookies/set?k1=v1&k2=v2'))
    await client.close()

