import requests
import asyncio
import pyppeteer
import logging
from pyppeteer.page import Page
from aiohttp import ClientSession, ClientRequest

from io import BytesIO
from PIL import Image
import inspect
from .utils import goto_js_list, random_delay, get_user_agent
from .cookies import CookiesManager
from . import conf

# typing
from types import TracebackType
from typing import Any, Optional, Tuple, Union, Dict, List, Type
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass
_Page = Optional['Page']
_Client = 'Client'
_CSSSelector = str
_TypeIn = Tuple[_CSSSelector, str]
_URL = Union[str, 'URL']

logger = logging.getLogger(__name__)

DEFUALT_HEADERS = {'User-Agent': get_user_agent()}


class HTTPClient:
    """A client uses aiohttp to make requests.
    """

    def __init__(self, cookies_manager=None, **kwargs):
        self.cookies_manager: CookiesManager = cookies_manager if cookies_manager else CookiesManager()
        self.session = None
        headers = kwargs.pop('headers', None)
        headers = headers if headers else DEFUALT_HEADERS

        self.session = ClientSession(headers=headers, **kwargs)
        self.cookies_manager.sync_to_aiohttp_session(self.session)

        self.logger = logging.getLogger('HTTP')
        self.level = self.logger.getEffectiveLevel()

    async def close(self):
        if self.session:
            await self.session.close()
        self.session = None

    async def request(self,
                      url: _URL,
                      method: str,
                      params=None,
                      data=None,
                      **kwargs: Any):
        if self.level == logging.DEBUG:
            func = inspect.stack()[2][3]
            msg = conf.DEBUG_REQ_FMT % (func, url, method,
                                        params, data)
            self.logger.debug(msg)
        resp = await self.session.request(method, url, params=params, data=data, **kwargs)
        self.cookies_manager.update_from_aiohttp_session(self.session)
        return resp

    async def get(self, url: _URL, params=None, **kwargs: Any):
        return await self.request(url, "GET", params=params, **kwargs)

    async def post(self, url: _URL, data: Any = None, params=None, **kwargs: Any):
        return await self.request(url, "POST", data=data, params=None, **kwargs)

    async def send(self, request, expect_json=True, ignore_content=False):
        r = await self.request(method=request.method,
                               url=request.url,
                               params=request.params,
                               data=request.data,
                               headers=request.headers)

        await self._debug_response(r)
        return r

    async def _debug_response(self, resp):
        if self.level == logging.DEBUG:
            func = inspect.stack()[4][3]
            msg = conf.DEBUG_RES_FMT % (func, resp.status, await resp.text())
            self.logger.debug(msg)

    async def check(self, check_flag: str, url: _URL = ""):
        resp = await self.get(url)
        if check_flag in await resp.text():
            return True
        return False

    def __enter__(self) -> None:
        raise TypeError("Use async with instead")

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None:
        # __exit__ should exist in pair with __enter__ but never executed
        pass  # pragma: no cover

    async def __aenter__(self) -> 'HTTPClient':
        return self

    async def __aexit__(self,
                        exc_type: Optional[Type[BaseException]],
                        exc_val: Optional[BaseException],
                        exc_tb: Optional[TracebackType]) -> None:
        await self.close()


class BrowserClient:
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

    def __init__(self, cookies_manager=None):
        self.cookies_manager = cookies_manager if cookies_manager else CookiesManager()
        self.browser = None
        self.page = None

    async def prepare(self, launch_option: Optional[Dict] = None) -> _Page:
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

    async def close(self, page: _Page = None):
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
            ele = await self.page.J(selector)
            if ele is None:
                return 0
            elif await ele.isIntersectingViewport():
                shot = await ele.screenshot(options, **kwargs)
            else:
                return -1
        if show:
            img = Image.open(BytesIO(shot))
            img.show()
        return shot

    async def check(self, check_flag: str, url: _URL = "", by_selector=True):
        if not url in self.page.url:
            self.page.goto(url)
        if by_selector:
            return await self.page.J(check_flag)
        else:
            return check_flag in await self.page.content()
