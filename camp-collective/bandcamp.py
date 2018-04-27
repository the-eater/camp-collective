import json

from random import random
import datetime
import re
from urllib.parse import unquote
import asyncio
from .collection import Collection
import os
from requests.cookies import cookiejar_from_dict
from requests import Session
from bs4 import BeautifulSoup


class Bandcamp:
    FORMATS = [
        'wav',
        'forbis',
        'flac',
        'mp3-v0',
        'mp3-320',
        'alac',
        'aiff-lossless',
        'aac-hi'
    ]

    session = None
    file_format = None
    user = None
    download_status = None
    download_directory = None

    def __init__(self, cookies, file_format='flac', download_directory=None):
        self.session = AsyncIOSession()
        self.session.cookies = cookiejar_from_dict(cookies)
        self.file_format = file_format
        self.download_status = {}
        self.download_directory = download_directory if download_directory is not None else os.getcwd()

    async def load_user_data(self):
        data = await self.get_page_data('https://bandcamp.com')

        if data is None:
            return False

        if data['identities']['fan'] is None:
            return False

        self.user = data['identities']['fan']

        return True

    def is_logged_in(self):
        return self.user is not None

    async def load_own_collection(self, full=False):
        if not self.is_logged_in():
            raise RuntimeError("Need to be logged in to load own collection")

        collection_seed = await self.get_page_data(self.user['url'])

        collection = Collection()
        collection.amount = collection_seed['collection_data']['item_count']
        collection.last_token = collection_seed['collection_data']['last_token']
        collection.extend(collection_seed['item_cache']['collection'].values(),
                          collection_seed['collection_data']['redownload_urls'])

        has_more = not collection_seed['collection_data']['small_collection']

        while full and has_more:
            data = await self.get_collection_part(self.user['id'], last_token=collection.last_token, count=100)

            if data is None:
                break

            collection.last_token = data['last_token']
            collection.extend(data['items'], data['redownload_urls'])
            has_more = data['more_available']

        return collection

    async def get_collection_part(self, fan_id, last_token, count=45):
        resp = await self.session.post('https://bandcamp.com/api/fancollection/1/collection_items', json={
            "fan_id": fan_id,
            "older_than_token": last_token,
            "count": count
        })

        if resp.status_code != 200:
            print("Failed retrieving collection for Fan[id=%s] after token %s" % (
                fan_id, last_token))
            return None

        return resp.json()

    async def download_item(self, item, file_format=None):
        file_format = file_format if file_format is not None else self.file_format

        if file_format not in Bandcamp.FORMATS:
            raise RuntimeError('File format %s is not supported by bandcamp' % file_format)

        self.download_status[item.id] = {
            "item": item,
            "status": "requested"
        }

        data = await self.get_page_data(item.download_url)

        if data is None or data['digital_items'][0] is None or 'downloads' not in data['digital_items'][0]:
            self.download_status[item.id]['status'] = 'failed'
            return None

        info = data['digital_items'][0]

        final_download_url = str(info['downloads'][file_format]['url'])

        # this is hacky af imo, but this is also what the JS does, so w/e
        stat_url = final_download_url.replace(
            '/download/', '/statdownload/', 1)

        converted = False

        self.download_status[item.id]['status'] = 'converting'
        while not converted:
            rand = random()
            now = datetime.datetime.now()

            rand *= (now.timestamp() * 1000) + \
                round(now.time().microsecond / 1000)

            rand_stat_url = stat_url + '&.rand=' + str(rand) + '&.vrs=1'
            resp = await self.session.get(rand_stat_url, headers={
                "Accept": "application/json, text/javascript, */*; q=0.01"
            })

            if resp.status_code != 200:
                print("Failed to get status via %s" % rand_stat_url)
                continue

            data = resp.json()
            converted = data['result'] == 'ok'

        resp = await self.session.get(final_download_url, stream=True)
        if resp.status_code != 200:
            print('Failed to download ZIP')
            self.download_status[item.id]['status'] = 'failed'

        match = re.search(r"filename\*=UTF-8''(.+)",
                          resp.headers.get('content-disposition'))

        if match:
            file = os.path.join(self.download_directory,
                                unquote(str(match.group(1))))
        else:
            file = os.path.join(self.download_directory, item.id + '.zip')

        self.download_status[item.id]['status'] = 'downloading'
        self.download_status[item.id]['size'] = int(
            resp.headers.get('content-length'))
        self.download_status[item.id]['downloaded_size'] = 0

        def writeFileToFile(resp, filename):
            with open(filename, 'wb') as fd:
                for chunk in resp.iter_content(chunk_size=128):
                    self.download_status[item.id]['downloaded_size'] += len(
                        chunk)
                    fd.write(chunk)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, writeFileToFile, resp, file)
        self.download_status[item.id]['status'] = 'done'

        return file

    async def get_page_data(self, url):
        resp = await self.session.get(url)
        if resp.status_code != 200:
            print("Failed retrieving `%s`" % url)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        json_data = soup.select_one('#pagedata')['data-blob']
        return json.loads(json_data)


class AsyncIOSession(Session):
    loop = None

    def __init__(self, *args, loop=None, **kwargs):
        self.loop = loop if loop is not None else asyncio.get_event_loop()
        super().__init__(*args, **kwargs)

    def request(self, *args, **kwargs):
        def do_request(soup):
            return soup.request(*args, **kwargs)

        return self.loop.run_in_executor(None, do_request, super())
