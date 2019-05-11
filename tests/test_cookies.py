from aninja.cookies import CookiesManager
from http import cookies
from pyppeteer import launch
from pathlib import Path
import requests
import asyncio
import aiohttp
import pytest


def httpbin(interface=''):
    return 'http://httpbin.org'+interface


mng = CookiesManager()
mng.update({'some_name': 'some_value'})


def test_output():
    assert mng.output_header_string() == 'some_name=some_value'
    assert mng.output_dict() == {
        'some_name': 'some_value'
    }
    assert mng.output_detailed() == [{
        'name': 'some_name',
        'value': 'some_value',
        'domain': '',
        'path': '/'
    }]


def test_save(tmp_path):
    m = mng.copy()
    p = Path(tmp_path)
    m.save(p/'test.cookiejar')
    new_m = CookiesManager()
    new_m.load(p/'test.cookiejar')
    assert m.output_detailed() == new_m.output_detailed()


def test_work_with_cookiejar():
    m = mng.copy()
    s = requests.session()
    s.get(httpbin('/cookies'))

    m.update(s.cookies)
    m.sync_to_cookiejar(s.cookies)
    s.get(httpbin('/cookies'))
    assert s.cookies.get_dict() == m._jar.get_dict()

    s.get(httpbin('/cookies/set?k1=v1&k2=v2'))
    m.update(s.cookies)
    assert m.output_dict() == {'k1': 'v1',
                               'k2': 'v2', 'some_name': 'some_value'}


@pytest.mark.asyncio
async def test_work_aiohttp_session():
    m = mng.copy()
    async with aiohttp.ClientSession() as session:

        m.sync_to_aiohttp_session(session)
        assert session.cookie_jar.filter_cookies(
            httpbin()).output() == 'Set-Cookie: some_name=some_value'

        await session.get(httpbin('/cookies/set?k1=v1&k2=v2'))
        m.update_from_aiohttp_session(session)
        assert m.output_dict() == {
            'some_name': 'some_value', 'k1': 'v1', 'k2': 'v2'}


@pytest.mark.asyncio
async def test_work_with_pyppeteer():
    m = mng.copy()
    b = await launch()
    page = await b.newPage()
    await page.goto(httpbin('/cookies/set?k1=v1&k2=v2'))
    await m.update_from_pyppeteer(page)
    assert m.output_dict() == {
        'some_name': 'some_value', 'k1': 'v1', 'k2': 'v2'}
    m.update({'name': 'ciri'})
    await m.sync_to_pyppeteer(page)
    cookies = await page.cookies()
    await b.close()
    assert len(cookies) == 4
