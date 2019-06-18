import asyncio
from .loginer import Loginer


class Pan115Loginer(Loginer):
    url = 'https://115.com/'
    login_mark = '.fans-modal'

    async def login_with_qrcode(self):
        await asyncio.sleep(1)
        await self.page.screenshot('#js_login_qrcode_img', show=True)
        # waiting 10 seconds to scan the qrcode manually
        await self.page.gather_for_navigation(asyncio.sleep(10))

    async def login_with_password(self):
        pass
