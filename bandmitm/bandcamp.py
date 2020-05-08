from requests import Session, Request
import asyncio
from hashlib import sha1
import hmac
import string

from bandmitm.dissambled import scramble_pow, PoWHandler


class Bandcamp:
    HOST = 'https://bandcamp.com'
    CLIENT_ID = 134
    CLIENT_SECRET = "1myK12VeCL3dWl9o/ncV2VyUUbOJuNPVJK6bZZJxHvk="
    SECRET_DM_HMAC_KEY = b'dtmfa'
    LOCALES = [
        "en-GB"
    ]
    PLATFORM = 'a'
    VERSION_CODE = 172734

    def __init__(self, client):
        self.client = client
        self.current_dm = None
        self.magic_dm_prefix = None
        self.did_bootstrap = False
        self.client.headers[
            'User-Agent'
        ] = 'Dalvik/2.1.0 (Linux; U; Android 8.1.0; ONEPLUS A5010 Build/OPM7.181205.001)'
        self.access_token = None
        self.refresh_token = None
        self.pow_handler = PoWHandler()

    async def get_accounts(self, user: str, password: str):
        data = await self.check_login(user, password)

        if not data['ok']:
            raise RuntimeError("check_login returned not ok")

        return data['accounts']

    async def login_account(self, user_id: str, password: str):
        tokens = await self.oauth_login_password(user_id, password)

        if not tokens['ok']:
            raise RuntimeError("oauth_login returned not ok")

        self.refresh_token = tokens['refresh_token']
        self.access_token = tokens['access_token']
        self.client.headers['Authorization'] = 'Bearer ' + self.access_token

    def get_platform_params(self):
        return {
            "platform": self.PLATFORM,
            "version": self.VERSION_CODE,
            "locales": self.LOCALES,
        }

    async def get_collection_info(self):
        params = self.get_platform_params()
        return (await self.client.get(self.HOST + '/api/mobile/20/collectioninfo', params=params)).json()

    async def get_collection_sync(self, page_size: int = 20, offset: str = None):
        query = {
            "page_size": page_size
        }

        if offset is not None:
            query['offset'] = offset

        return (await self.client.get(self.HOST + '/api/collectionsync/1/collection', params=query)).json()

    async def check_login(self, username: str, password: str):
        resp = await self.dm_post(self.HOST + "/api/mobile/24/check_login", json={
            "email": username,
            "password": password
        })

        return resp.json()

    async def bootstrap(self):
        bootstrap = await self.client.post(self.HOST + '/api/mobile/24/bootstrap_data', headers={
            'X-Requested-With': 'com.bandcamp.android'
        }, json=self.get_platform_params())

        self.pow_handler.set_pow(bootstrap.headers['X-Bandcamp-PoW'])

    async def get_collection_items(self, fan_id: str, older_than_token: str = None, count: int = 20):
        obj = {
            "fan_id": fan_id,
            "count": count,
            "older_than_token": older_than_token
        }

        #  if older_than_token is not None:
        #     obj['older_than_token'] = older_than_token

        return (await self.client.post('https://bandcamp.com/api/fancollection/1/collection_items', json=obj)).json()

    def handle_dm_feedback(self, dm):
        pla = int(dm[-1], 16)
        plb = int(dm[pla], 16)
        if plb == 1:
            self.magic_dm_prefix = dm[:19] + dm[22:]

    def create_magic_dm(self, body: bytes):
        if isinstance(body, str):
            body = body.encode('utf-8')

        if self.magic_dm_prefix is not None:
            body = self.magic_dm_prefix.encode('utf-8') + body

        return hmac.new(self.SECRET_DM_HMAC_KEY, body, sha1) \
            .digest() \
            .hex()

    async def oauth_login_password(self, user_id: str, password: str):
        return (await self.dm_post(self.HOST + "/oauth_login", data={
            "grant_type": "password",
            "username": user_id,
            "password": password,
            "username_is_user_id": 1,
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET
        })).json()

    async def dm_post(self, *args, _try: int = 0, **kwargs):
        req = Request('POST', *args, **kwargs)

        prepped = self.client.prepare_request(req)

        prepped.headers['X-Bandcamp-DM'] = self.create_magic_dm(prepped.body)
        prepped.headers['X-Bandcamp-PoW'] = str(self.pow_handler.create_pow(prepped.body))

        resp = self.client.send(prepped)
        if 'X-Bandcamp-DM' in resp.headers:
            self.handle_dm_feedback(resp.headers['X-Bandcamp-DM'])

        if _try < 2 and resp.status_code == 418:
            await asyncio.sleep(_try + 1)
            return await self.dm_post(*args, _try=_try + 1, **kwargs)

        return resp

    def make_pow(self, input: str):
        scramble_pow(input, 1, 10, "")


class AsyncIOSession(Session):
    loop = None

    def __init__(self, loop=None):
        super().__init__()
        self.loop = loop if loop is not None else asyncio.get_event_loop()

    def request(self, *args, **kwargs):
        def do_request(soup):
            return soup.request(*args, **kwargs)

        return self.loop.run_in_executor(None, do_request, super())
