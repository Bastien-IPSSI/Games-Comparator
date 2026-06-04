import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

SOURCE = "instant-gaming"

BASE_URL = (
    "https://www.instant-gaming.com/fr/rechercher/"
    "?sort_by=bestsellers_desc"
    "&preferences%5B%5D=hide_f2p"
    "&preferences%5B%5D=instock"
    "&preferences%5B%5D=hide_rumors"
    "&platform%5B%5D=1"
    "&product_types%5B%5D=game"
    "&page={page}"
)

HEADERS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def parse_price(raw: str) -> float | None:
    if not raw:
        return None
    cleaned = raw.replace("\xa0", "").replace(" ", "").strip()
    match = re.search(r"\d+[.,]\d{2}", cleaned)
    if match:
        return float(match.group().replace(",", "."))
    match = re.search(r"\d+", cleaned)
    return float(match.group()) if match else None


def parse_discount(raw: str) -> int | None:
    if not raw:
        return None
    match = re.search(r"\d+", raw)
    return int(match.group()) if match else None


def setup_driver(headless: bool = False) -> webdriver.Chrome:
    service = ChromeService(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_argument(f"user-agent={HEADERS_UA}")
    driver = webdriver.Chrome(service=service, options=options)
    if not headless:
        driver.maximize_window()
    else:
        driver.set_window_size(1920, 1080)
    return driver


def scrape_game_urls_by_page(driver: webdriver.Chrome, wait: WebDriverWait, page: int) -> list[str]:
    driver.get(BASE_URL.format(page=page))
    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".listing-items .item")))
    except Exception:
        return []

    urls = []
    for game in driver.find_elements(By.CSS_SELECTOR, ".listing-items .item"):
        try:
            url = game.find_element(By.CSS_SELECTOR, ".item.force-badge a").get_attribute("href")
            if url and "-steam-" in url:
                urls.append(url)
        except Exception:
            continue
    return urls


def _safe_text(driver: webdriver.Chrome, selector: str, container_selector: str = ".panel-container") -> str | None:
    """Re-query un élément à chaque appel pour éviter les références stale."""
    try:
        return driver.find_element(By.CSS_SELECTOR, f"{container_selector} {selector}").text.strip() or None
    except Exception:
        return None


def _safe_texts(driver: webdriver.Chrome, selector: str) -> list[str]:
    try:
        return [el.text.strip() for el in driver.find_elements(By.CSS_SELECTOR, selector) if el.text.strip()]
    except Exception:
        return []


def _safe_attr(driver: webdriver.Chrome, selector: str, attr: str) -> str | None:
    try:
        return driver.find_element(By.CSS_SELECTOR, selector).get_attribute(attr) or None
    except Exception:
        return None


def scrape_game_details(driver: webdriver.Chrome, wait: WebDriverWait, url: str) -> dict | None:
    driver.get(url)
    try:
        # Attendre que la page soit prête et le contenu stabilisé
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".panel-container")))
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(0.5)

        # Re-query chaque élément depuis driver (jamais de référence stale)
        title = _safe_text(driver, "h1")
        if not title:
            return None

        price_raw      = _safe_text(driver, ".total")
        discount_raw   = _safe_text(driver, ".discounted")
        original_price_raw = _safe_text(driver, ".retail", container_selector="")

        image_url = _safe_attr(driver, ".panel-container img", "src")

        platform_texts = _safe_texts(driver, ".platform-container span")
        platform = platform_texts[0] if platform_texts else "Steam"

        return {
            "title": title,
            "price": parse_price(price_raw),
            "discount": parse_discount(discount_raw),
            "original_price": parse_price(original_price_raw),
            "platform": platform,
            "url": url,
            "image_url": image_url,
        }
    except Exception as e:
        print(f"  [!] Erreur détails {url} : {e}")
        return None


def scrape_all_pages(max_pages: int = 10, headless: bool = False) -> list[dict]:
    driver = setup_driver(headless=headless)
    wait = WebDriverWait(driver, 15)
    all_games: list[dict] = []

    try:
        # Étape 1 : collecter toutes les URLs
        all_urls: list[str] = []
        for page in range(1, max_pages + 1):
            print(f"  Page {page}/{max_pages} — collecte des URLs...")
            urls = scrape_game_urls_by_page(driver, wait, page)
            if not urls:
                print(f"  Page {page} vide — arrêt.")
                break
            all_urls.extend(urls)
            print(f"  {len(urls)} URLs (total : {len(all_urls)})")
            time.sleep(0.5)

        # Étape 2 : scraper les détails de chaque jeu
        print(f"\n  Scraping des détails pour {len(all_urls)} jeux...")
        for idx, url in enumerate(all_urls, 1):
            print(f"  [{idx}/{len(all_urls)}] {url}")
            details = scrape_game_details(driver, wait, url)
            if details:
                all_games.append(details)
            time.sleep(0.3)

    finally:
        driver.quit()

    return all_games


if __name__ == "__main__":
    import json
    games = scrape_all_pages(max_pages=1, headless=False)

    print(f"\n{'='*40}")
    print(f"{len(games)} jeux au total\n")
    for g in games:
        print("-" * 40)
        print(f"{g['title']}")
        print(f"  Prix : {g['price']} €")
        print(f"  Remise : {g['discount']}%" if g['discount'] else "  Pas de réduction")
        print(f"  Prix original : {g['original_price']}" if g['original_price'] else "")
        print(f"  URL : {g['url']}")
        print(f"  Plateforme : {g['platform']}")
