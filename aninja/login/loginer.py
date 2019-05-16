import asyncio
from ..client import BrowserClient as Client


# Typing
from typing import Optional
_Client = Optional['Client']


class Loginer:
    url = 'Not determined'
    login_mark = 'Not determined'

    def __init__(self,
                 client: _Client = None,
                 username: str = '',
                 password: str = '',
                 devtools: bool = False):
        self.config(username, password, )
        self.devtools = devtools
        self._external_client = True
        if client is None:
            self._external_client = False
            self.client = Client()
        else:
            self.client = client

        self.cookies_manager = self.client.cookies_manager

    def config(self,
               username: str = '',
               password: str = '',):
        self.username = username
        self.password = password

    async def has_logged_in(self):
        return await self.login_by_page(only_check=True)

    async def login_by_page(self, only_check=False, qr_login: bool = False,) -> bool:
        await self.client.prepare_page({'devtools': self.devtools})
        await self.client.goto(self.url)
        login = bool(await self.client.page_check(check_flag=self.login_mark))

        if not only_check and not login:
            if qr_login:
                await self.login_with_qrcode()
            else:
                await self.login_with_password()
            login = bool(await self.client.page_check(check_flag=self.login_mark))
        if self._external_client:
            await self.client.close(mode=0, page=self.client.page)
        else:
            await self.client.close(mode=0)
        return login

    async def login_with_qrcode(self):
        raise NotImplementedError

    async def login_with_password(self):
        raise NotImplementedError
