import asyncio
import inspect
import logging
from io import BytesIO
# typing
from types import TracebackType
from typing import Any, List, Optional, Tuple, Type, Union

import pyppeteer
from aiohttp import ClientSession
from PIL import Image
from pyppeteer.page import Page

import aninja.conf as conf
from aninja.cookies import CookiesManager
from aninja.utils import get_user_agent, pretend_js_list, random_delay

_Page = Optional[Page]
_Client = 'Client'
_CSSSelector = str
_TypeIn = Tuple[_CSSSelector, str]
_URL = Union[str, 'URL']

logger = logging.getLogger(__name__)

DEFUALT_HEADERS = {'User-Agent': get_user_agent()}


def patch_pyppeteer():
    import pyppeteer.connection
    original_method = pyppeteer.connection.websockets.client.connect

    def new_method(*args, **kwargs):
        kwargs['ping_interval'] = None
        kwargs['ping_timeout'] = None
        return original_method(*args, **kwargs)

    pyppeteer.connection.websockets.client.connect = new_method


patch_pyppeteer()


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


class NinjaPage(Page):

    def __init__(self, page: _Page, client: 'BrowserClient'):
        self._browser_client = client
        self._page = page
        self.__dict__.update(page.__dict__)

    @property
    def cookies_manager(self):
        return self._browser_client.cookies_manager

    async def text(self):
        return await self.evaluate('() => document.body.innerHTML')

    async def gather_for_navigation(self,   *aws, options: dict = None, **kwargs):
        """if coroutines in your aws can cause page's navigation, use this function to wrap it and
        keep track of cookies.
        """
        result = await asyncio.gather(self.waitForNavigation(options, **kwargs), *aws)
        await self.cookies_manager.update_from_pyppeteer(self)
        return result

    async def screenshot(self, selector: str = '',
                         hide_selectors: List[str] = None,
                         show=False,
                         options: dict = None,
                         **kwargs):
        """Another method to take a screen shot.

            Args:
                selector: take a screen shot of the element located by css 
                    selector. If it's not set, then take a screen shot of the 
                    full page.
                hide_selectors: before taking screenshot, some elements may be 
                    hided on purpose.
                show: if set to True, then image will be opened by `Pillow`
                options: same options of :meth:`screenshot`
        """
        if hide_selectors:
            if isinstance(hide_selectors, list):
                sels = ', '.join(hide_selectors)
            elif isinstance(hide_selectors, str):
                sels = hide_selectors
            style = sels+'{display: none !important}'
            await self.addStyleTag(content=style)
        if not selector:
            shot = await super().screenshot(options, **kwargs)
        else:
            ele = await self.J(selector)
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

    async def check(self, check_flag: str, by_selector=True):
        if by_selector:
            return await self.J(check_flag)
        else:
            return check_flag in await self.content()


class BrowserClient:
    """A client pretends itself as a real-world user agent using puppeteer.

    This client support a more explicit pyppeteer interface.


    Attributes:
        browser: a pyppeteer browser object; You can provide a browser, 
            otherwise it will create a new one; Diffierent BrowserClients can 
            work with same browser.
        context: a pyppeteer context; It will be automatically created as an 
            incogonitocontext. BrowerClient use the context to create page, 
            store session, work with cookies_manager.
        cookies_manager: a CookiesManager synchronizing cookies between session 
            and page.
    """

    def __init__(self,
                 cookies_manager=None,
                 browser=None,
                 context=None,
                 ):
        self.cookies_manager = cookies_manager
        self.browser = browser
        self.context = context
        self.user_agent = get_user_agent()
        viewport = {'width': 1280, 'height': 1024}
        self.emulate_options = {'viewport': viewport}

    async def newPage(self) -> _Page:
        page = NinjaPage(await self.context.newPage(), self)
        await self.cookies_manager.sync_to_pyppeteer(page)
        await page.emulate(options=self.emulate_options)
        for js in pretend_js_list:
            await page.evaluateOnNewDocument(js)
        return page

    async def close(self):
        return await self.browser.close()

    async def pages(self):
        return await self.browser.pages()


async def launch(browser=None, cookies_manager=None, options: dict = None, **kwargs) -> BrowserClient:
    browser = await pyppeteer.launch(options, **kwargs)
    context = await browser.createIncognitoBrowserContext()
    cookies_manager = CookiesManager() if cookies_manager is None else cookies_manager
    client = BrowserClient(cookies_manager, browser, context)
    return client
