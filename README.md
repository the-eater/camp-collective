# Camp Collective

A bandcamp python toolset


Camp collective currently gives you a useless API and a cli tool to download your whole bandcamp collection.

# Usage

```
Camp Collective.

Usage:
    camp-collective -c=<cookie>... [options] download-collection [<target-directory>]

Options:
    --cookie=<cookie> -c       Cookies used to authenticate with Bandcamp (split by ; and content url encoded)
    --parallel=<amount> -p     Amount of items that should be downloaded parallel [default: 5]
    --status=<status-file> -s  Status file to save the status in of downloaded releases, so we don't over do it
    --format=<file-format> -f  File format to download (wav, forbis, flac, mp3-v0, mp3-320, alac, aiff-lossless, aac-hi) [default: flac]
```

# Quickstart

```
pyenv install 3.6.1 # or you equivalent
pyenv local 3.6.1
pip install -r requirements.txt
python -m camp-collective -c "$COOKIE_STRING" -p 10 download-collection ~/bandcamp -s "${STATUS_FILE}"
```

To authenticate with bandcamp you need to provide a cookie string, you can retrieve this by logging in in a webbrowser, opening the web console and running `document.cookie`, use this as the cookie string

Bandcamp uses a captcha on the login page, so we can't use the conventional username/password authentication

You can use the status file to keep track of already downloaded _tralbum_'s (as bandcamp calls it)

---
I have no connection with Bandcamp, except 1 support ticket on which the answer was "we'll think about it"