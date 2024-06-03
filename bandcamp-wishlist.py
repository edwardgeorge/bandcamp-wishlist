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
from typing import Any, Dict, List, Optional, Tuple

import browser_cookie3
import dateparser
import requests
from bs4 import BeautifulSoup, SoupStrainer

log = logging.getLogger()

USER_URL = "https://bandcamp.com/{}"
WISHLIST_POST_URL = "https://bandcamp.com/api/fancollection/1/wishlist_items"
BANDS_POST_URL = "https://bandcamp.com/api/fancollection/1/following_bands"
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

    dl = subp.add_parser("download-bands")
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
    g.add_argument(
        "--before",
        type=parse_date,
        metavar="DATE",
    )
    g.add_argument(
        "--since",
        type=parse_date,
        metavar="DATE",
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
    ract.add_argument(
        "--bands",
        "-b",
        type=Path,
        metavar="BANDS_JSON",
    )
    follows = ract.add_mutually_exclusive_group()
    follows.add_argument(
        "--only-followed",
        action="store_true",
        default=False,
        dest="only_followed",
    )
    follows.add_argument(
        "--no-followed",
        action="store_true",
        default=False,
        dest="no_followed",
    )
    # next 2 imply --only-followed
    follows.add_argument(
        "--followed-since",
        type=parse_date,
        dest="followed_since",
        metavar="DATE",
    )
    follows.add_argument(
        "--followed-before",
        type=parse_date,
        dest="followed_before",
        metavar="DATE",
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
    elif args.action == "download-bands":
        acc, d = get_user(args.username, args.browser, args.cookies)
        init, tok, ic = initial_bands(d)
        r = init + acc._req_loop(
            BANDS_POST_URL, count=ic, initial_token=tok, result_key="followeers"
        )
        if args.output is not None:
            with args.output.open("w") as f:
                json.dump(r, f)
        else:
            print(json.dumps(r, indent=4))
    elif args.action == "random":
        with args.input.open() as f:
            wl = json.load(f)
        print("loaded {} items from {}".format(len(wl), args.input))
        if args.bands:
            with args.bands.open() as f:
                bands = json.load(f)
            print("loaded {} bands from {}".format(len(bands), args.bands))
            band_ids = {*(i["band_id"] for i in bands)}
            follow_times = {i["band_id"]: parse_date(i["date_followed"]) for i in bands}
        else:
            bands = None
            band_ids = {*[]}
            follow_times = {}

        filters = []
        if args.first:
            filters.append(lambda i, j: i < args.first)
        if args.after_first:
            filters.append(lambda i, j: i >= args.after_first)
        if args.last:
            ix = len(wl) - args.last
            filters.append(lambda i, j: i >= ix)
        if args.before:
            filters.append(lambda i, j: parse_date(j["added"]) < args.before)
        if args.since:
            filters.append(lambda i, j: parse_date(j["added"]) >= args.since)
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
        if args.only_followed:
            if bands is None:
                return parser.error("'--only-followed' requires '--bands'")
            filters.append(lambda i, j: j["band_id"] in band_ids)
        if args.no_followed:
            if bands is None:
                return parser.error("'--no-followed' requires '--bands'")
            filters.append(lambda i, j: j["band_id"] not in band_ids)
        if args.followed_since:
            if bands is None:
                return parser.error("'--followed-since' requires '--bands'")
            filters.append(
                lambda i, j: followed_since(
                    j["band_id"], follow_times, args.followed_since
                )
            )
        if args.followed_before:
            if bands is None:
                return parser.error("'--followed-before' requires '--bands'")
            filters.append(
                lambda i, j: followed_before(
                    j["band_id"], follow_times, args.followed_before
                )
            )

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


def parse_date(datestr: str):
    return dateparser.parse(
        datestr, settings={"RETURN_AS_TIMEZONE_AWARE": True, "TO_TIMEZONE": "UTC"}
    )


def followed_since(band_id, follow_times, since):
    try:
        t = follow_times[band_id]
    except KeyError:
        return False
    else:
        return t >= since


def followed_before(band_id, follow_times, before):
    try:
        t = follow_times[band_id]
    except KeyError:
        return False
    else:
        return t < before


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
            WISHLIST_POST_URL,
            count=count,
            initial_token=default_token(),
            result_key="items",
        )

    def _req_loop(self, url: str, count: int, initial_token: str, result_key: str):
        r = []
        tok = initial_token
        while True:
            d = self._api_post(url, count=count, last_token=tok)
            if "error" in d:
                raise Exception("Error from api request")
            try:
                items = d[result_key]
            except KeyError:
                raise Exception(f"No '{result_key}' found in {d}")
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


def initial_bands(data) -> Tuple[List[Any], str, int]:
    d = data["following_bands_data"]
    r = hydrate_initial(d["pending_sequence"], data["item_cache"]["following_bands"])
    return (r, d["last_token"], d["item_count"] - len(r))


def hydrate_initial(sequence: List[str], cache: Dict[str, Any]) -> List[Any]:
    return [cache[i] for i in sequence]


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
