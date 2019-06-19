from aninja.login.zhihu import ZhihuLoginer
from aninja.login.pan115 import Pan115Loginer
import asyncio
import pytest
from pathlib import Path


# @pytest.mark.asyncio
# async def test_zhihuqr():
#     loginer = ZhihuLoginer(devtools=True)
#     assert await loginer.login_by_browser(qr_login=True)
#     loginer.cookies_manager.save('zhihu.cookiejar')


# @pytest.mark.asyncio
# async def test_zhihupw():
#     loginer = ZhihuLoginer(devtools=True)
#     loginer.config("panslsss15@gmail.com", "Pslstc975230@zhihuu")
#     assert await loginer.login_by_browser()
#     loginer.cookies_manager.save('zhihu.cookiejar')


# @pytest.mark.asyncio
# async def test_loadzhihu():
#     loginer = ZhihuLoginer(devtools=True)
#     loginer.cookies_manager.load('zhihu.cookiejar')
#     # loginer.cookies_manager.load('cookies.txt')
#     print(loginer.cookies_manager.output_dict())
#     assert await loginer.login_by_browser(only_check=True)


@pytest.mark.asyncio
async def test_115qr():
    loginer = await Pan115Loginer.launch(options={'devtools': True})
    assert await loginer.login_by_browser(qr_login=True)
    loginer.cookies_manager.save(Path.home() / '.115cookies')
    await loginer.close()


@pytest.mark.asyncio
async def test_115load():
    loginer = await Pan115Loginer.launch(options={'devtools': True})
    loginer.cookies_manager.load(Path.home() / '.115cookies')
    assert await loginer.login_by_browser(only_check=True)
    await loginer.close()
