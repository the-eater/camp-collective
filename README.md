# Camp Collective

A bandcamp python toolset


Camp collective currently gives you a useless API and a cli tool to download your whole bandcamp collection.

# How to use

```
pyenv install 3.6.1 # or you equivalent
pyenv local 3.6.1
pip install -r requirements.txt
python -m camp-collective -c "$COOKIE_STRING" -p 10 download-collection ~/bandcamp
```

To authenticate with bandcamp you need to provide a cookie string, you can retrieve this by logging in in a webbrowser, opening the web console and running `document.cookie`, use this as the cooking string

Bandcamp uses a captcha on the login page, so we can't use the conventional username/password authentication

---
I have no connection with Bandcamp, except 1 support ticket on which the answer was "we'll think about it"