from .bandcamp import Bandcamp, AsyncIOSession
import asyncio
from json import dumps
import os

EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')


async def main():
    bc = Bandcamp(client=AsyncIOSession())
    bc.client.proxies = {
        'https': os.getenv('HTTPS_PROXY')
    }
    await bc.bootstrap()
    accounts = await bc.get_accounts(EMAIL, PASSWORD)
    await bc.login_account(accounts[0]['user_id'], PASSWORD)
    with open('./dump.json', 'w') as f:
        f.write(dumps(
            await bc.get_collection_items(count=400, older_than_token="1:1549881632:792788008:a", fan_id=str(198156)),
            indent=4))


asyncio.get_event_loop().run_until_complete(main())
