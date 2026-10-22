"""
Free stock-photo lookup for timeline scenes, as an alternative to manually
dropping a file in timeline_video/images/ and pointing an IMAGE: line at it.

Tries Pexels first, then Pixabay, matching the provider order and
"pick the smallest rendition that still covers the target resolution"
approach used by MoneyPrinterTurbo's app/services/material.py (video search,
not photos, but same idea) — adapted here for the still-image Ken Burns
background this pipeline actually uses, nothing video-shaped.

Results are cached to disk by (provider, query, orientation) so re-rendering
the same script doesn't re-hit the API or re-download the same file.
"""
import hashlib
import sys
from pathlib import Path

import requests

CACHE_DIR = Path(__file__).resolve().parent / "images" / "stock_cache"

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
PIXABAY_SEARCH_URL = "https://pixabay.com/api/"


def _cache_path(provider, query, orientation):
    key = hashlib.sha1(f"{provider}:{orientation}:{query}".encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{provider}_{key}.jpg"


def _download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=(10, 30))
    response.raise_for_status()
    dest.write_bytes(response.content)


def _search_pexels(query, orientation, api_key):
    params = {"query": query, "orientation": orientation, "per_page": 1}
    headers = {"Authorization": api_key}
    response = requests.get(PEXELS_SEARCH_URL, params=params, headers=headers, timeout=(10, 30))
    response.raise_for_status()
    photos = response.json().get("photos") or []
    if not photos:
        return None
    src = photos[0].get("src") or {}
    return src.get("large2x") or src.get("large") or src.get("original")


def _search_pixabay(query, orientation, api_key):
    params = {
        "key": api_key,
        "q": query,
        "image_type": "photo",
        "orientation": "vertical" if orientation == "portrait" else "horizontal",
        "per_page": 3,
    }
    response = requests.get(PIXABAY_SEARCH_URL, params=params, timeout=(10, 30))
    response.raise_for_status()
    hits = response.json().get("hits") or []
    if not hits:
        return None
    return hits[0].get("largeImageURL") or hits[0].get("webformatURL")


def fetch_stock_image(query, orientation="landscape", pexels_api_key=None, pixabay_api_key=None):
    """
    Returns a local file path to a stock photo matching `query`, or None if
    no provider is configured/available. `orientation` is "landscape" or
    "portrait", matching reveal_common.is_portrait()'s two states.
    """
    providers = []
    if pexels_api_key:
        providers.append(("pexels", _search_pexels, pexels_api_key))
    if pixabay_api_key:
        providers.append(("pixabay", _search_pixabay, pixabay_api_key))

    for name, search_fn, api_key in providers:
        cached = _cache_path(name, query, orientation)
        if cached.exists():
            return str(cached)
        try:
            image_url = search_fn(query, orientation, api_key)
            if not image_url:
                continue
            _download(image_url, cached)
            return str(cached)
        except Exception as e:
            print(f"stock_fetch: {name} lookup failed for {query!r}: {e}", file=sys.stderr)
            continue

    return None
