import asyncio
from aninja.browser import launch, BrowserClient, NinjaPage


class Loginer:
    url = "Not determined"
    login_mark = "Not determined"

    def __init__(self, client, username: str = "", password: str = ""):
        self.username = username
        self.password = password
        self.client: BrowserClient = client
        self.cookies_manager = self.client.cookies_manager
        self.page: NinjaPage = None

    @classmethod
    async def launch(
        cls,
        browser=None,
        cookies_manager=None,
        options: dict = None,
        username="",
        password="",
        **kwargs
    ):
        client = await launch(browser, cookies_manager, options, **kwargs)
        loginer = cls(client, username, password)
        loginer.page = await loginer.client.newPage()
        return loginer

    def config(self, username: str = "", password: str = ""):
        self.username = username
        self.password = password

    async def has_logged_in(self):
        return await self.login_by_browser(only_check=True)

    async def login_by_browser(
        self, only_check=False, qr_login: bool = False
    ) -> bool:
        self.page: NinjaPage = await self.client.newPage()
        await self.page.goto(self.url, options={"waitUtil": "networkidle0"})
        login = bool(await self.page.check(check_flag=self.login_mark))

        if not only_check and not login:
            if qr_login:
                await self.login_with_qrcode()
            else:
                await self.login_with_password()
            login = bool(await self.page.check(check_flag=self.login_mark))

        self.cookies_manager.never_expires()
        return login

    async def close(self):
        await self.page.close()
        await self.client.close()

    async def login_with_qrcode(self):
        raise NotImplementedError

    async def login_with_password(self):
        raise NotImplementedError
