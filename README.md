# bandcamp-wishlist [![Python package](https://github.com/edwardgeorge/bandcamp-wishlist/actions/workflows/python-package.yml/badge.svg)](https://github.com/edwardgeorge/bandcamp-wishlist/actions/workflows/python-package.yml)

Open random items from your Bandcamp wishlist in a browser. Based on and modified from the code from [https://github.com/easlice/bandcamp-downloader](https://github.com/easlice/bandcamp-downloader).

Download your Bandcamp wishlist to a local JSON file and then query it for random recommendations which it will open in your browser to listen to.

_The motivation for this script came from having a lengthy wishlist spanning many years yet when looking for new music to buy the bandcamp UI biases me into only purchasing music wishlisted in the recent past with older wishlisted items being essentially forgotten. I created this script to surface older items by opening a random item from my wishlist whenever run._

It requires you to have a browser with a logged in session of bandcamp open. Cookies from the browser will be used to authenticate with Bandcamp.

Supported browsers are the same as in [browser_cookie3](https://github.com/borisbabic/browser_cookie3): Chrome, Chromium, Firefox, Brave, Opera, and Edge

Alternatively, you can use a [Netscape format cookies](https://curl.se/docs/http-cookies.html) file.

## Usage

First download your wishlist to a file, eg:
```
bandcamp-wishlist.py download -b firefox -o wishlist.json <bandcamp-username>
```

Then run to open a random album in your browser:
```
bandcamp-wishlist.py random -i wishlist.json
```

The `random` subcommand also supports a number of useful filters to narrow-down the random space, such as only picking 'name your price' items:
```
bandcamp-wishlist.py random -i wishlist.json --no-price
```

The full list of filters can be seen with the `--help` option:

```
usage: bandcamp-wishlist.py random [-h] --input INPUT [--first N | --after-first N | --last N | --before DATE | --since DATE] [--only-albums] [--download-available] [--is-purchasable] [--min-also-collected MIN_ALSO_COLLECTED]
                                   [--max-also-collected MAX_ALSO_COLLECTED]
                                   [--genre {electronic,rock,metal,alternative,hip-hop-rap,experimental,punk,folk,pop,ambient,soundtrack,world,jazz,acoustic,funk,r-b-soul,devotional,classical,reggae,podcasts,country,spoken-word,comedy,blues,kids,audiobooks,latin}]
                                   [--bands BANDS_JSON] [--only-followed | --no-followed | --followed-since DATE | --followed-before DATE] [--no-price]

options:
  -h, --help            show this help message and exit
  --input INPUT, -i INPUT
  --first N             Limit to first N items
  --after-first N       Limit to items after first N
  --last N              Limit to last N items
  --before DATE
  --since DATE
  --only-albums
  --download-available
  --is-purchasable
  --min-also-collected MIN_ALSO_COLLECTED
  --max-also-collected MAX_ALSO_COLLECTED
  --genre {electronic,rock,metal,alternative,hip-hop-rap,experimental,punk,folk,pop,ambient,soundtrack,world,jazz,acoustic,funk,r-b-soul,devotional,classical,reggae,podcasts,country,spoken-word,comedy,blues,kids,audiobooks,latin}, -g {electronic,rock,metal,alternative,hip-hop-rap,experimental,punk,folk,pop,ambient,soundtrack,world,jazz,acoustic,funk,r-b-soul,devotional,classical,reggae,podcasts,country,spoken-word,comedy,blues,kids,audiobooks,latin}
  --bands BANDS_JSON, -b BANDS_JSON
  --only-followed
  --no-followed
  --followed-since DATE
  --followed-before DATE
  --no-price
```

## Known Issues

### Running the script on WSL crashes with a `DBUS_SESSION_BUS_ADDRESS` error

This is seems to be a WSL issue. The browser_cookie3 module  tries to get a secret from your keyring via dbus, but WSL may not have dbus installed, or may not have it set up as expected. As such, you may see the following error:

`secretstorage.exceptions.SecretServiceNotAvailableException: Environment variable DBUS_SESSION_BUS_ADDRESS is unset`

Please either check your WSL dbus installation/configuration, or run the script nativity on windows.

### "Unable to get key for cookie decryption" error, especially in Chrome

There is currently an issue with [browser_cookie3](https://github.com/borisbabic/browser_cookie3). This has been reported within this repo [here](https://github.com/easlice/bandcamp-downloader/issues/17) and you can see the status of it upstream [here](https://github.com/borisbabic/browser_cookie3/issues/141).

### "Failed to find <browser> cookie" even though you have the browser installed and are logged in.

Sometimes a browser does not put its files in the expected location. This is especially true if the browser is installed as a flatpack or snap. As such, browser_cookie3 doesn't know where to look for the cookie store.

You can fix this by using the `--cookies` flag and giving it the path to your browser's cookie store, usually a file named something like `Cookies` or `cookies.sqlite`. Note: You still need to give the correct `--browser` flag.

Another option is to symlink the directory to the correct place. For example, the package `chromium-bin` often installs to the directory `~/.chromium-bin` but it is expected to be at `~.chromium`. You can run:
`symlink -s ~/.chromium-bin ~/.chromium`
and then browser_cookie3 will be able to find the cookies as expected and you will not need to use the `--cookies` flag.

## Manual Setup

Install the script dependencies by running:

```
pip install .
```

Run the program:

```
bandcamp-wishlist.py [arguments]
```

If you run into errors or dependency issues, you can try installing exact dependency versions by running:

```
pip install -r requirements.txt
```

## Setup via Poetry

Install requirements using [Python Poetry](https://python-poetry.org/). [Installation instructions here](https://python-poetry.org/docs/#installation).

```
poetry install
```

Run the script within the poetry shell:

```
poetry shell
python bandcamp-wishlist.py [arguments]
```

or directly through `poetry run`:

```
poetry run python bandcamp-wishlist.py [arguments]
```
