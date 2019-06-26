from aninja.browser import launch
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
    assert '"k1": "v1"' in await r.text()
    assert await page.check('k2', by_selector=False)
    await client.close()
