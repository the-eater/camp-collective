from docopt import docopt
from os.path import isfile

import asyncio
import json
from colorama import Fore, ansi

from .bandcamp import Bandcamp

DOC = """
Camp Collective.

Usage:
    camp-collective -c=<cookie>... [options] download-collection [<target-directory>]

Options:
    --cookie=<cookie> -c       Cookies used to authenticate with Bandcamp (split by ; and content url encoded)
    --parallel=<amount> -p     Amount of items that should be downloaded parallel [default: 5]
    --status=<status-file> -s  Status file to save the status in of downloaded releases, so we don't over do it
    --format=<file-format> -f  File format to download (%s) [default: flac]
""" % ', '.join(Bandcamp.FORMATS)
data = docopt(DOC)


async def _main(data):
    cookie_string = ';'.join(data['--cookie']).strip(' ;')

    def parse_cookie(str):
        kv = str.split('=', maxsplit=1)

        if len(kv) == 1:
            kv.append(None)

        return kv

    cookie_dict = dict([parse_cookie(cookie_comb)
                        for cookie_comb in cookie_string.split(';')])
    bc = Bandcamp(cookies=cookie_dict)

    if data['download-collection']:
        if data['<target-directory>']:
            bc.download_directory = data['<target-directory>']

        await download_collection(bc, parallel=int(data['--parallel']), status_file=data['--status'],
                                  file_format=data['--format'])


async def do_login(bc):
    await bc.load_user_data()

    if not bc.is_logged_in():
        print(Fore.RED + "No user logged in with given cookies" + Fore.RESET)
        exit(1)

    print(Fore.GREEN + 'Logged in as ' + Fore.BLUE + bc.user['name'] + Fore.GREEN + ' (' + Fore.CYAN + bc.user[
        'username'] + Fore.GREEN + ')' + Fore.RESET)


def on_executor(func):
    async def wrapper(*args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(None, lambda: func(*args, **kwargs))

    return wrapper


@on_executor
def read_file_in_memory(filename):
    with open(filename, 'r') as fp:
        return fp.read()


@on_executor
def write_contents_to_file(filename, data):
    with open(filename, 'w') as fp:
        fp.write(data)


async def download_collection(bc, parallel, status_file=None, file_format=None):
    file_format = file_format.lower()

    if file_format not in Bandcamp.FORMATS:
        print(Fore.RED + "Please use one of the following formats: " + Fore.CYAN + (Fore.RED + ', ' + Fore.CYAN).join(
            Bandcamp.FORMATS) + Fore.RESET)
        exit(1)

    await do_login(bc)

    coll = await bc.load_own_collection(full=True)
    working = 0
    done = 0
    failed = 0
    status = {}

    if status_file is not None:
        if not isfile(status_file):
            try:
                with open(status_file, 'w') as fp:
                    fp.write('{}')
            except RuntimeError as e:
                print("Can't write status file (%s)" % status_file)
                exit(1)

        json_status = await read_file_in_memory(status_file)
        status = json.loads(json_status)

    queue = [item for item in coll.items.values(
    ) if item.id not in status or not status[item.id]]

    async def print_progress():
        nonlocal working, done, failed
        last_height = 0
        step = 0
        # But it looks sexy in the console!
        while len(queue) > 0 or working > 0:
            message = ((ansi.clear_line() + ansi.Cursor.UP(
                1)) * last_height) + ansi.clear_line() + '\r' + Fore.YELLOW + "Queued: " + Fore.GREEN + str(
                len(queue)) + Fore.YELLOW + " Working: " + Fore.GREEN + str(
                working) + Fore.YELLOW + " Done: " + Fore.GREEN + str(
                done) + Fore.YELLOW + " Failed: " + Fore.RED + str(failed) + Fore.RESET + "\n\n"

            for val in bc.download_status.values():
                if val['status'] not in ['downloading', 'converting', 'requested']:
                    continue

                message += Fore.YELLOW + '['
                if val['status'] == 'converting' or val['status'] == 'requested':
                    bar = '.. .. ..'
                    message += Fore.BLUE + bar[step:step + 4]

                if val['status'] == 'downloading':
                    percent = str(round(
                        (val['downloaded_size'] / val['size']) * 100))

                    percent = (" " * (3 - len(percent))) + percent

                    message += Fore.BLUE + percent + '%'

                message += Fore.YELLOW + '] ' + Fore.CYAN + val[
                    'item'].name + Fore.YELLOW + ' by ' + Fore.GREEN + val[
                               'item'].artist + Fore.RESET + "\n"

            last_height = message.count("\n")
            print(message, end="")
            step = (step + 1) % 4
            await asyncio.sleep(0.5)

    async def write_status():
        while len(queue) > 0 or working > 0:
            json_data = json.dumps(status)
            await write_contents_to_file(status_file, json_data)
            await asyncio.sleep(5)

        json_data = json.dumps(status)
        await write_contents_to_file(status_file, json_data)

    async def download_item(item):
        nonlocal done, failed
        res = await bc.download_item(item, file_format)
        done += 1

        if res is None:
            failed += 1
        else:
            status[item.id] = True

    async def queue_download():
        nonlocal working

        working += 1
        while len(queue) > 0:
            item = queue.pop()
            await download_item(item)

        working -= 1

    downloaders = []
    for i in range(min(len(queue), parallel)):
        downloaders.append(queue_download())

    progress_checkers = [print_progress()]

    if status_file is not None:
        progress_checkers.append(write_status())

    await asyncio.gather(*downloaders, *progress_checkers)


loop = asyncio.get_event_loop()
loop.run_until_complete(_main(data))
loop.close()
