"""Yad2 car scraper — fetches Israel car listings for 4 target models."""

import json
import logging
import re
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

# (manufacturer_id, model_id, display_label)
TARGETS = [
    (19, 10226, "Toyota Corolla"),
    (48, 10720, "Kia Sportage"),
    (27, 10342, "Mazda CX-5"),
    (21, 10291, "Hyundai Tucson"),
]

FILTERS = {
    "min_year": 2020,
    "max_price": 95000,
    "max_km": 100000,
    "exclude_colors_eng": ["black"],
    "exclude_colors_he": ["שחור"],
}

_FEED_URL = "https://www.yad2.co.il/vehicles/cars?manufacturer={mfr}&model={mdl}"
_ITEM_API = "https://gw.yad2.co.il/vehicles-item/{token}"
_LISTING_URL = "https://www.yad2.co.il/item/{token}"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.yad2.co.il/",
    "Accept": "application/json",
}


@dataclass
class CarListing:
    token: str
    url: str
    manufacturer: str
    model: str
    sub_model: str
    year: int
    price: int
    km: int
    color: str
    hand: int
    area: str
    engine_type: str
    cover_image: str


def _fetch_feed_items(manufacturer: int, model: int, label: str) -> list[dict]:
    """Load model's first page via Playwright and parse embedded __NEXT_DATA__."""
    from playwright.sync_api import sync_playwright

    url = _FEED_URL.format(mfr=manufacturer, mdl=model)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                locale="he-IL",
            )
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            content = page.content()
            browser.close()

        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            content,
            re.DOTALL,
        )
        if not match:
            logger.warning("[Cars] No __NEXT_DATA__ for %s", label)
            return []

        data = json.loads(match.group(1))
        queries = (
            data["props"]["pageProps"]
            .get("dehydratedState", {})
            .get("queries", [])
        )
        for q in queries:
            if q.get("queryKey", [None])[0] == "feed":
                fd = q["state"]["data"]
                items = (
                    fd.get("private", [])
                    + fd.get("commercial", [])
                    + fd.get("platinum", [])
                    + fd.get("solo", [])
                )
                logger.info("[Cars] %s: %d listings on page 1", label, len(items))
                return items
        return []
    except Exception as e:
        logger.error("[Cars] Feed fetch failed for %s: %s", label, e)
        return []


def _fetch_item_details(token: str) -> dict | None:
    """Fetch full listing details (km, color) via direct gw API."""
    try:
        r = requests.get(_ITEM_API.format(token=token), headers=_HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        body = r.json()
        # API returns either {data: {...}} or the object directly
        return body.get("data", body)
    except Exception as e:
        logger.error("[Cars] Item API failed for %s: %s", token, e)
        return None


def _is_black(color: dict) -> bool:
    text = color.get("text", "").strip()
    eng = color.get("textEng", "").lower()
    return any(c in text for c in FILTERS["exclude_colors_he"]) or any(
        c in eng for c in FILTERS["exclude_colors_eng"]
    )


def fetch_listings() -> list[CarListing]:
    """Return all listings that pass year/price/km/color filters."""
    results = []

    for manufacturer, model, label in TARGETS:
        items = _fetch_feed_items(manufacturer, model, label)

        for item in items:
            # Pre-filter on preview data (no extra request needed)
            year = item.get("vehicleDates", {}).get("yearOfProduction", 0)
            price = item.get("price", 0)
            if year < FILTERS["min_year"] or price == 0 or price > FILTERS["max_price"]:
                continue

            token = item["token"]
            details = _fetch_item_details(token)
            if not details:
                continue

            km = details.get("km", 0)
            if km > FILTERS["max_km"]:
                continue

            color = details.get("color", {})
            if _is_black(color):
                continue

            results.append(
                CarListing(
                    token=token,
                    url=_LISTING_URL.format(token=token),
                    manufacturer=item.get("manufacturer", {}).get("text", ""),
                    model=item.get("model", {}).get("text", ""),
                    sub_model=item.get("subModel", {}).get("text", ""),
                    year=year,
                    price=price,
                    km=km,
                    color=color.get("text", ""),
                    hand=details.get("hand", {}).get("id", 0),
                    area=item.get("address", {}).get("area", {}).get("text", ""),
                    engine_type=item.get("engineType", {}).get("text", ""),
                    cover_image=item.get("metaData", {}).get("coverImage", ""),
                )
            )

    logger.info("[Cars] %d listings passed all filters", len(results))
    return results
