from .bandcamp import Bandcamp, AsyncIOSession
import asyncio

EMAIL = "[email]"
PASSWORD = "[password]"


async def main():
    bc = Bandcamp(client=AsyncIOSession())
    await bc.bootstrap()
    accounts = await bc.get_accounts(EMAIL, PASSWORD)
    await bc.login_account(accounts[0]['user_id'], PASSWORD)
    print(await bc.get_collection_sync())


asyncio.get_event_loop().run_until_complete(main())
