"""
=============================================================================
CREDENTIALS ALGOLIA DE FANATICAL
=============================================================================

Ce qui a été trouvé via DevTools (F12 → Réseau → filtre "algolia") :
  - ALGOLIA_APP_ID  : w2m9492ddv   (sous-domaine : w2m9492ddv-dsn.algolia.net)
  - ALGOLIA_INDEX   : fan_unlimited (dans le body de la requête)
  - ALGOLIA_API_KEY : clé "secured" générée par Fanatical côté serveur,
                      valide ~10 minutes seulement.

"""

import json
import time
import urllib.parse

import requests

ALGOLIA_APP_ID    = "w2m9492ddv"
ALGOLIA_INDEX     = "fan_unlimited"
ALGOLIA_MULTI_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/*/queries"
SITE_BASE         = "https://www.fanatical.com"
CDN_IMG           = "https://fanatical.imgix.net/product/original/"

BASE_FILTERS = "on_sale:true AND type:game"

# Tranches de prix pour contourner la limite de 1000 résultats par requête Algolia.
PRICE_RANGES = [
    (0,    2.5),
    (2.5,    5),
    (5,    7.5),
    (7.5,  10),
    (10,   15),
    (15,   20),
    (20,   35),
    (35,   60),
    (60,   100),
    (100,  9999),
]

# Content-Type x-www-form-urlencoded (pas application/json) pour éviter le preflight CORS.
HEADERS = {
    "Content-Type":   "application/x-www-form-urlencoded",
    "Referer":        f"{SITE_BASE}/",
    "Origin":         SITE_BASE,
    "User-Agent":     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "Accept":         "*/*",
}


def _fetch_fresh_key() -> str:
    """Charge Fanatical en Chrome headless et capture la clé Algolia depuis les logs réseau."""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options,
    )
    try:
        print("  Chargement de Fanatical pour capturer la clé Algolia...")
        driver.get(f"{SITE_BASE}/fr/on-sale?types=game")
        time.sleep(5)

        for entry in driver.get_log("performance"):
            msg = json.loads(entry["message"]).get("message", {})
            if msg.get("method") != "Network.requestWillBeSent":
                continue
            url = msg.get("params", {}).get("request", {}).get("url", "")
            if "x-algolia-api-key=" not in url:
                continue
            qs  = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            key = qs.get("x-algolia-api-key", [None])[0]
            if key:
                print("  Clé Algolia fraîche capturée (valide ~10 min).")
                return key
    finally:
        driver.quit()

    raise RuntimeError("Clé Algolia introuvable dans les logs réseau de Fanatical.")


def _make_request_url(api_key: str) -> str:
    # Les credentials sont en query params (pas en header) — obligatoire avec les secured keys Algolia.
    agent = urllib.parse.quote(
        "Algolia for JavaScript (4.20.0); Browser (lite); "
        "JS Helper (3.14.0); react (18.2.0); react-instantsearch (6.40.4)"
    )
    return (
        f"{ALGOLIA_MULTI_URL}"
        f"?x-algolia-agent={agent}"
        f"&x-algolia-api-key={urllib.parse.quote(api_key, safe='')}"
        f"&x-algolia-application-id={ALGOLIA_APP_ID.upper()}"
    )


def parse_hit(hit: dict) -> dict:
    slug  = hit.get("slug") or ""
    cover = hit.get("cover") or ""
    price    = (hit.get("price")     or {}).get("EUR")
    orig     = (hit.get("fullPrice") or {}).get("EUR")
    discount = hit.get("discount_percent")

    return {
        "title":          hit.get("name") or "N/A",
        "price":          float(price)    if price    is not None else None,
        "discount":       int(discount)   if discount is not None else None,
        "original_price": float(orig)     if orig     is not None else None,
        "platform":       "PC",
        "url":            f"{SITE_BASE}/fr/game/{slug}" if slug else "N/A",
        "image_url":      f"{CDN_IMG}{cover}"           if cover else "N/A",
    }


def fetch_page(session: requests.Session, api_key: str,
               page: int, extra_filters: str = "") -> dict:
    filters = f"{BASE_FILTERS} AND {extra_filters}" if extra_filters else BASE_FILTERS
    body = {"requests": [{"indexName": ALGOLIA_INDEX,
                          "query": "", "hitsPerPage": 100,
                          "page": page, "filters": filters}]}
    resp = session.post(
        _make_request_url(api_key),
        headers=HEADERS,
        data=json.dumps(body),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["results"][0] if "results" in data else data


def scrape_range(session: requests.Session, api_key: str,
                 price_min: float, price_max: float, delay: float) -> list[dict]:
    extra    = f"price.EUR >= {price_min} AND price.EUR < {price_max}"
    first    = fetch_page(session, api_key, 0, extra)
    nb_hits  = first.get("nbHits", 0)
    nb_pages = first.get("nbPages", 1)

    if nb_hits > 1000:
        print(f"    ⚠ {nb_hits} résultats pour {price_min}–{price_max}€ — divise cette tranche")

    games = [parse_hit(h) for h in first.get("hits", [])]
    print(f"    Tranche {price_min}–{price_max}€ : {nb_hits} jeux ({nb_pages} pages)")

    for page in range(1, nb_pages):
        games += [parse_hit(h) for h in fetch_page(session, api_key, page, extra).get("hits", [])]
        if page < nb_pages - 1:
            time.sleep(delay)

    return games


def scrape_all(delay: float = 0.3) -> list[dict]:
    api_key   = _fetch_fresh_key()
    session   = requests.Session()
    seen      : set[str] = set()
    all_games : list[dict] = []

    for price_min, price_max in PRICE_RANGES:
        for g in scrape_range(session, api_key, price_min, price_max, delay):
            if g["url"] not in seen:
                seen.add(g["url"])
                all_games.append(g)

    print(f"\nTotal après déduplication : {len(all_games)} jeux")
    return all_games


if __name__ == "__main__":
    import sys

    if "--inspect" in sys.argv:
        key     = _fetch_fresh_key()
        session = requests.Session()
        data    = fetch_page(session, key, 0)
        print(f"nbHits : {data.get('nbHits')}")
        print("\nChamps du 1er résultat :")
        print(json.dumps(data["hits"][0] if data.get("hits") else {}, ensure_ascii=False, indent=2))
    else:
        games = scrape_all()
        print(f"\n{'='*50}")
        print(f"{len(games)} jeux récupérés\n")
        print(json.dumps(games, ensure_ascii=False, indent=2))
