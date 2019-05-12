import requests
import asyncio
import pyppeteer
import logging
from pyppeteer.page import Page
from aiohttp import ClientSession

from io import BytesIO
from PIL import Image
from .utils import goto_js_list, random_delay, get_user_agent
from .cookies import CookiesManager

# typing
from typing import Any, Optional, Tuple, Union, Dict, List
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass
_Page = Optional['Page']
_Client = 'Client'
_CSSSelector = str
_TypeIn = Tuple[_CSSSelector, str]
_URL = Union[str, 'URL']

logger = logging.getLogger(__name__)


class BaseClient:
    def __init__(self):
        self.cookies_manager = CookiesManager()


class SessionClient(BaseClient):
    """A client uses aiohttp to make requests.
    """
    def __init__(self):
        super().__init__()
        self.session = None

    async def prepare_session(self):
        headers = {
            'User-Agent': get_user_agent()
        }
        if self.session is None:
            self.session = ClientSession(headers=headers)
            self.cookies_manager.sync_to_aiohttp_session(self.session)

    async def close_session(self):
        if self.session:
            await self.session.close()
        self.session = None

    async def request(self,
                method: str,
                url: _URL,
                **kwargs: Any):
        resp = await self.session.request(method, url, **kwargs)
        self.cookies_manager.update_from_aiohttp_session(self.session)
        return resp

    async def get(self, url: _URL, **kwargs: Any):
        return await self.request("GET", url, **kwargs)

    async def post(self, url: _URL, data: Any = None, **kwargs: Any):
        return await self.request("POST", data=data, **kwargs)

    async def session_check(self, check_flag: str, url:_URL=""):
        resp = await self.get(url)
        if check_flag in await resp.text():
            return True
        return False


class BrowserClient(BaseClient):
    """A client pretends itself as a real-world user agent using puppeteer.

    This client support a more explicit pyppeteer interface.


    Attributes:
        browser: a pyppeteer browser object, maintains itself before closing
        page: a pyppeteer page object. It is created by calling self.newPage()
            and delete itself by calling self.close_page(); You should always
            have this attributes before callling other methods related to page
            operation.
        cookies_manager: a CookiesManager synchronizing cookies between session and page.
    """

    def __init__(self):
        super().__init__()
        self.browser = None
        self.page = None

    async def prepare_page(self, launch_option: Optional[Dict] = None)->_Page:
        """Create a new page for the client's browser.If browser is None, it wich a new browser.
        """
        if self.browser is None:
            self.browser = await pyppeteer.launch(launch_option)
        current_page = await self.browser.newPage()
        await self.cookies_manager.sync_to_pyppeteer(current_page)
        self.set_current_page(current_page)
        return current_page

    def set_current_page(self, page: _Page):
        self.page = page

    async def close_page(self, page: _Page = None):
        """If arg page is not None, it will close the page. Otherwise it will close the whole browser.
        """
        if self.browser:
            if page:
                if page is self.page:
                    self.page = None
                await page.close()
            else:
                self.browser = await self.browser.close()
                self.page = None

    async def goto(self, url: str, options: dict = None, **kwargs: Any):
        """Go to the url
        Available options are: timeout, waitUtil. See ``pyppeteer.page.Page``
        """
        await self.cookies_manager.sync_to_pyppeteer(self.page)
        await self.page.setUserAgent(get_user_agent())
        for js in goto_js_list:
            await self.page.evaluateOnNewDocument(js)
        r = await self.page.goto(url, options=options, **kwargs)
        await self.cookies_manager.update_from_pyppeteer(self.page)
        return r

    async def type(self, *types: _TypeIn):
        """Simulate the action for typing username and password.

        Args:
            types: receive tuples with two elements. The first is css selector
                for the INPUT, the second is its value.
        """
        for css, value in types:
            await self.page.type(css, value, {'delay':  random_delay()})

    async def gather_for_navigation(self,   *aws, options: dict = None, **kwargs):
        """if coroutines in your aws can cause browser's navigation, use this function to wrap it and
        keep track of cookies.
        """
        result = await asyncio.gather(self.page.waitForNavigation(options, **kwargs), *aws)
        await self.cookies_manager.update_from_pyppeteer(self.page)
        return result

    async def click(self, selector: str, options: dict = None, **kwargs):
        return await self.page.click(selector, options, **kwargs)

    async def screenshot(self, selector: str = '', full_page=False,
                         hide_selectors: List[str] = None, show=True,
                         options: dict = None, **kwargs):
        if hide_selectors:
            if isinstance(hide_selectors, list):
                sels = ', '.join(hide_selectors)
            elif isinstance(hide_selectors, str):
                sels = hide_selectors
            style = sels+'{display: none !important}'
            await self.page.addStyleTag(content=style)
        if full_page:
            shot = await self.page.screenshot(options, **kwargs)
        else:
            await self.page.waitFor(selector)
            ele = await self.page.J(selector)
            shot = await ele.screenshot(options, **kwargs)
        if show:
            img = Image.open(BytesIO(shot))
            img.show()
        return shot

    async def page_check(self, check_flag: str, url:_URL="", by_selector=False):
        if not url in self.page.url:
            self.page.goto(url)
        if by_selector:
            return await self.page.J(check_flag)
        else:
            return check_flag in await self.page.content()


class Client(BrowserClient, SessionClient):
    def __init__(self):
        super().__init__()
        self.mode = -1

    async def prepare(self, mode=0, launch_option: Optional[Dict] = None):
        if mode == 0:
            await self.prepare_page(launch_option)
        elif mode == 1:
            await self.prepare_session()
        elif mode == 2:
            await self.prepare_page()
            await self.prepare_session()
        else:
            raise TypeError('Invalid mode, should be 0, 1 or 2')
        self.mode = mode

    async def close(self, mode=2, page: _Page = None):
        if mode == 2:
            await self.close_page(page)
            await self.close_session()
        elif mode == 1:
            await self.close_session()
        elif mode == 0:
            await self.close_page(page)
