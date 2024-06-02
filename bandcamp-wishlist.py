#!/usr/bin/env python
import html
import http
import http.cookiejar
import json
import logging
import random
import time
import webbrowser
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import browser_cookie3
import requests
from bs4 import BeautifulSoup, SoupStrainer

log = logging.getLogger()

USER_URL = "https://bandcamp.com/{}"
WISHLIST_POST_URL = "https://bandcamp.com/api/fancollection/1/wishlist_items"
SUPPORTED_BROWSERS = ["firefox", "chrome", "chromium", "brave", "opera", "edge"]
GENRES = [
    {"id": 10, "label": "electronic", "slug": "electronic"},
    {"id": 23, "label": "rock", "slug": "rock"},
    {"id": 18, "label": "metal", "slug": "metal"},
    {"id": 2, "label": "alternative", "slug": "alternative"},
    {"id": 14, "label": "hip-hop/rap", "slug": "hip-hop-rap"},
    {"id": 11, "label": "experimental", "slug": "experimental"},
    {"id": 20, "label": "punk", "slug": "punk"},
    {"id": 12, "label": "folk", "slug": "folk"},
    {"id": 19, "label": "pop", "slug": "pop"},
    {"id": 3, "label": "ambient", "slug": "ambient"},
    {"id": 24, "label": "soundtrack", "slug": "soundtrack"},
    {"id": 26, "label": "world", "slug": "world"},
    {"id": 15, "label": "jazz", "slug": "jazz"},
    {"id": 1, "label": "acoustic", "slug": "acoustic"},
    {"id": 13, "label": "funk", "slug": "funk"},
    {"id": 21, "label": "r&b/soul", "slug": "r-b-soul"},
    {"id": 9, "label": "devotional", "slug": "devotional"},
    {"id": 5, "label": "classical", "slug": "classical"},
    {"id": 22, "label": "reggae", "slug": "reggae"},
    {"id": 27, "label": "podcasts", "slug": "podcasts"},
    {"id": 7, "label": "country", "slug": "country"},
    {"id": 25, "label": "spoken word", "slug": "spoken-word"},
    {"id": 6, "label": "comedy", "slug": "comedy"},
    {"id": 4, "label": "blues", "slug": "blues"},
    {"id": 16, "label": "kids", "slug": "kids"},
    {"id": 28, "label": "audiobooks", "slug": "audiobooks"},
    {"id": 17, "label": "latin", "slug": "latin"},
]


def main():
    parser = ArgumentParser()
    parser.add_argument("--verbose", "-v", action="count", default=0)
    subp = parser.add_subparsers(dest="action", required=True)
    dl = subp.add_parser("download")
    dl.add_argument(
        "--browser",
        "-b",
        type=str,
        default="firefox",
        choices=SUPPORTED_BROWSERS,
        help='The browser whose cookies to use for accessing bandcamp. Defaults to "firefox"',
    )
    dl.add_argument(
        "--cookies",
        "-c",
        type=Path,
        help="Path to a cookie file. First, we will try to use it as a mozilla cookie jar. If that fails, it'll be used as the path for your given browser's cookie store.",
    )
    dl.add_argument(
        "--output",
        "-o",
        type=Path,
    )
    dl.add_argument("username")

    ract = subp.add_parser("random")
    ract.add_argument("--input", "-i", type=Path, required=True)
    g = ract.add_mutually_exclusive_group()
    g.add_argument(
        "--first",
        type=int,
        metavar="N",
        help="Limit to first N items",
    )
    g.add_argument(
        "--after-first",
        type=int,
        dest="after_first",
        metavar="N",
        help="Limit to items after first N",
    )
    g.add_argument(
        "--last",
        type=int,
        metavar="N",
        help="Limit to last N items",
    )
    ract.add_argument(
        "--only-albums",
        action="store_true",
        default=False,
        dest="only_albums",
    )
    ract.add_argument(
        "--download-available",
        action="store_true",
        default=False,
        dest="download_available",
    )
    ract.add_argument(
        "--is-purchasable",
        action="store_true",
        default=False,
        dest="is_purchasable",
    )
    ract.add_argument(
        "--min-also-collected",
        type=int,
        dest="min_also_collected",
    )
    ract.add_argument(
        "--max-also-collected",
        type=int,
        dest="max_also_collected",
    )
    ract.add_argument(
        "--genre",
        "-g",
        type=str,
        default=None,
        choices=[i["slug"] for i in GENRES],
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose > 0 else logging.INFO)

    if args.action == "download":
        acc, d = get_user(args.username, args.browser, args.cookies)
        ic = d["wishlist_data"]["item_count"]
        print(f"getting {ic} wishlist items...")
        wl = acc.get_wishlist(ic)
        if args.output is not None:
            with args.output.open("w") as f:
                json.dump(wl, f)
        else:
            print(json.dumps(wl, indent=4))
    elif args.action == "random":
        with args.input.open() as f:
            wl = json.load(f)
        print("loaded {} items from {}".format(len(wl), args.input))

        filters = []
        if args.first:
            filters.append(lambda i, j: i < args.first)
        if args.after_first:
            filters.append(lambda i, j: i >= args.after_first)
        if args.last:
            ix = len(wl) - args.last
            filters.append(lambda i, j: i >= ix)
        if args.only_albums:
            filters.append(lambda i, j: j["item_type"] == "album")
        if args.download_available:
            filters.append(lambda i, j: j["download_available"] is True)
        if args.is_purchasable:
            filters.append(lambda i, j: j["is_purchasable"] is True)
        if args.min_also_collected:
            filters.append(
                lambda i, j: j["also_collected_count"] >= args.min_also_collected
            )
        if args.max_also_collected:
            filters.append(
                lambda i, j: j["also_collected_count"] <= args.max_also_collected
            )
        if args.genre is not None:
            gid = {i["slug"]: i["id"] for i in GENRES}[args.genre]
            filters.append(lambda i, j: j["genre_id"] == gid)
        # TODO: add preorder filter. add tracks filters. date filter
        # TODO: add filter based on when fanned artist

        if filters:
            filtered = [j for (i, j) in enumerate(wl) if all(f(i, j) for f in filters)]
            print(
                "applied {} filters, now {} items".format(len(filters), len(filtered))
            )
        else:
            filtered = wl

        chosen = random.choice(filtered)
        print(
            "Opening: {} '{}': {}\n(added on {})".format(
                chosen["band_name"],
                chosen["item_title"],
                chosen["item_url"],
                chosen["added"],
            )
        )
        webbrowser.open_new_tab(chosen["item_url"])


@dataclass
class Account:
    fan_id: int
    cookies: http.cookiejar.CookieJar

    def _api_post(self, url: str, count: int, last_token: str):
        payload = {
            "fan_id": self.fan_id,
            "count": count,
            "older_than_token": last_token,
        }
        with requests.post(
            url,
            data=json.dumps(payload),
            cookies=self.cookies,
        ) as response:
            response.raise_for_status()
            return json.loads(response.text)

    def get_wishlist(self, count: int = 20) -> List[dict]:
        return self._req_loop(
            WISHLIST_POST_URL, count=count, initial_token=default_token()
        )

    def _req_loop(self, url: str, count: int, initial_token: str):
        r = []
        tok = initial_token
        while True:
            d = self._api_post(url, count=count, last_token=tok)
            if "error" in d:
                raise Exception("Error from api request")
            items = d["items"]
            r.extend(items)
            tok = d["last_token"]
            log.debug(
                "got batch of %s items. total: %s. last token: '%s'. more available? %s",
                len(items),
                len(r),
                tok,
                d["more_available"],
            )
            if not d["more_available"]:
                break
        return r


def default_token() -> str:
    return "{}::a::".format(int(time.time()))


def get_user(
    username: str, browser: str, cookies: Optional[str]
) -> Tuple[Account, dict]:
    cjar = get_cookies(browser, cookies)
    data = get_user_data(username, cjar)
    acc = Account(data["fan_data"]["fan_id"], cjar)
    return (acc, data)


def get_user_data(user: str, cookies: http.cookiejar.CookieJar) -> Optional[dict]:
    soup = BeautifulSoup(
        requests.get(
            USER_URL.format(user),
            cookies=cookies,
        ).text,
        "html.parser",
        parse_only=SoupStrainer("div", id="pagedata"),
    )
    div = soup.find("div")
    if not div:
        raise Exception(
            "ERROR: No div with pagedata found for user at url [{}]".format(
                USER_URL.format(user)
            )
        )
    data = json.loads(html.unescape(div.get("data-blob")))
    return data


def get_cookies(browser: str, cookies: Optional[str] = None):
    if cookies is not None:
        return load_cookies_from_file(browser, cookies)
    return load_cookies_from_browser(browser)


def load_cookies_from_browser(browser: str):
    try:
        func = getattr(browser_cookie3, browser)
    except AttributeError:
        raise Exception(
            "Browser type [{}] is unknown. Can't pull cookies, so can't authenticate with bandcamp.".format(
                browser
            )
        )
    else:
        return func(domain_name="bandcamp.com")


def load_cookies_from_file(browser: str, cookies: str):
    # First try it as a mozilla cookie jar
    try:
        cj = http.cookiejar.MozillaCookieJar(cookies)
        cj.load()
        return cj
    except Exception:
        log.info(
            "Cookie file at [%s] not a mozilla cookie jar.\nTrying it as a cookie store for the browser [%s]...",
            cookies,
            browser,
        )
    # Next try it with browser_cookie
    try:
        func = getattr(browser_cookie3, browser)
    except AttributeError:
        raise Exception(
            "Browser type [{}] is unknown. Can't pull cookies, so can't authenticate with bandcamp.".format(
                browser
            )
        )
    else:
        return func(domain_name="bandcamp.com", cookie_file=cookies)


if __name__ == "__main__":
    main()
