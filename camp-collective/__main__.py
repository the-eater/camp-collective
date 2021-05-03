from docopt import docopt
from os.path import isfile


from datetime import datetime
import locale

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
    --after=<date>             Only download tralbums that are purchased after given date, given in YYYY-MM-DD
""" % ', '.join(Bandcamp.FORMATS.keys())
data = docopt(DOC)


async def _main(data):
    # fuck you, unlocales you locale
    locale.setlocale(locale.LC_ALL, 'C')

    cookie_string = ';'.join(data['--cookie']).strip(' ;')

    def parse_cookie(string):
        kv = string.split('=', maxsplit=1)

        if len(kv) == 1:
            kv.append(None)

        return kv

    cookie_dict = dict([parse_cookie(cookie_comb)
                        for cookie_comb in cookie_string.split(';')])
    bc = Bandcamp(cookies=cookie_dict)

    after = None
    if data['--after']:
        after = datetime.strptime(data['--after'], '%Y-%m-%d')

    if data['download-collection']:
        if data['<target-directory>']:
            bc.download_directory = data['<target-directory>']

        await download_collection(bc, parallel=int(data['--parallel']), status_file=data['--status'],
                                  file_format=data['--format'], after=after)


async def do_login(bc):
    await bc.load_user_data()

    if not bc.is_logged_in():
        print(Fore.RED + "No user logged in with given cookies" + Fore.RESET)
        exit(1)

    print("{cg}Logged in as {cb}{bc.user[name]}{cg} ({cc}{bc.user[username]}{cg}){r}".format(
        cy=Fore.YELLOW, cc=Fore.CYAN, cg=Fore.GREEN, cb=Fore.BLUE, r=Fore.RESET, bc=bc
    ))


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


async def download_collection(bc, parallel, status_file=None, file_format=None, after=None):
    file_format = file_format.lower()

    if file_format not in Bandcamp.FORMATS.keys():
        print(Fore.RED + "Please use one of the following formats: " + Fore.CYAN
              + (Fore.RED + ', ' + Fore.CYAN).join(Bandcamp.FORMATS.keys()) + Fore.RESET)
        exit(1)

    await do_login(bc)

    coll = await bc.load_own_collection(full=True)
    working = 0
    done = 0
    failed = 0
    failed_items = []

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
    else:
        status = {}

    queue = [item for item in coll.items.values()
             if (item.id not in status or not status[item.id]) and (after is None or item.purchased is None or after < item.purchased)]

    async def print_progress():
        nonlocal working, done, failed
        last_height = 0
        step = 0
        # But it looks sexy in the console!
        while len(queue) > 0 or working > 0:
            message = (ansi.clear_line() + ansi.Cursor.UP(1)) * last_height
            message += '{clear}\r{cy}Queued: {cg}{nq}{cy} Working: {cg}{nw}' \
                       '{cy} Done: {cg}{nd}{cy} Failed: {cr}{nf}{r}\n\n'.format(
                           clear=ansi.clear_line(), cy=Fore.YELLOW,
                           cg=Fore.GREEN, cr=Fore.RED, r=Fore.RESET,
                           nq=len(queue), nw=working, nd=done, nf=failed)

            for val in bc.download_status.values():
                if val['status'] not in ('downloading', 'converting', 'requested'):
                    continue

                message += Fore.YELLOW + '[' + Fore.BLUE
                if val['status'] in ('converting', 'requested'):
                    bar = '.. .. ..'
                    message += bar[step:step + 4]

                elif val['status'] == 'downloading':
                    message += "{:>4.0%}".format(val['downloaded_size'] / val['size'])

                message += "{cy}] {cc}{v[item].name}{cy} by {cg}{v[item].artist}{r}\n".format(
                    cy=Fore.YELLOW, cc=Fore.CYAN, cg=Fore.GREEN, r=Fore.RESET, v=val
                )

            last_height = message.count("\n")
            print(message, end="")
            step = (step + 1) % 3
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
            failed_items.append(item)
        else:
            item_dict = item.as_dict()
            del item_dict['download_url']
            item_dict['file'] = res
            item_dict['quality'] = file_format
            status[item.id] = item_dict

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

    if failed > 0:
        print(Fore.YELLOW + '\nThe following items failed:')
        for item in failed_items:
            print("{cc}{i.name}{cy} by {cg}{i.artist}{cy}: {cb}{i.url}{r}".format(
                cy=Fore.YELLOW, cc=Fore.CYAN, cg=Fore.GREEN, cb=Fore.BLUE, r=Fore.RESET, i=item,
            ))

    print(Fore.GREEN + 'Done!' + Fore.RESET)


loop = asyncio.get_event_loop()
loop.run_until_complete(_main(data))
loop.close()
