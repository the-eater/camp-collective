from docopt import docopt

import asyncio

from colorama import Fore, ansi

from .bandcamp import Bandcamp

DOC = """
Camp Collective.

Usage:
    camp-collective -c=<cookie>... download-collection [--parallel=<amount>] [<target-directory>]

Options:
    --cookie=<cookie> -c  Cookies used to authenticate with Bandcamp (split by ; and content url encoded)
    --parallel=<amount>   Amount of items that should be downloaded parallel [default: 5]
"""
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

    await bc.load_user_data()

    if not bc.is_logged_in():
        print(Fore.RED + "No user logged in with given cookies" + Fore.RESET)
        exit(1)

    print(Fore.GREEN + 'Logged in as ' + Fore.BLUE + bc.user['name'] + Fore.GREEN + ' (' + Fore.CYAN + bc.user[
        'username'] + Fore.GREEN + ')' + Fore.RESET)

    if data['download-collection']:
        if data['<target-directory>']:
            bc.download_directory = data['<target-directory>']

        await download_collection(bc, parallel=int(data['--parallel']))


async def download_collection(bc, parallel):
    coll = await bc.load_own_collection(full=True)
    working = 0
    done = 0
    queue = list(coll.items.values())

    async def print_progress():
        nonlocal working, done
        last_height = 0
        step = 0
        # But it looks sexy in the console!
        while len(queue) > 0 or working > 0:
            message = ((ansi.clear_line() + ansi.Cursor.UP(
                1)) * last_height) + '\r' + Fore.YELLOW + "Queued: " + Fore.GREEN + str(
                len(queue)) + Fore.YELLOW + " Working: " + Fore.GREEN + str(
                working) + Fore.YELLOW + " Done: " + Fore.GREEN + str(
                done) + Fore.RESET + "\n\n"

            for val in bc.download_status.values():
                if val['status'] not in ['downloading', 'converting']:
                    continue

                message += Fore.YELLOW + '['
                if val['status'] == 'converting':
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

    async def download_item(item):
        nonlocal done
        await bc.download_item(item)
        done += 1

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

    await asyncio.gather(*downloaders, print_progress())


loop = asyncio.get_event_loop()
loop.run_until_complete(_main(data))
loop.close()
