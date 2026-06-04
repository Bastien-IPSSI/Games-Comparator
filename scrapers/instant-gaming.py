from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

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

def parse_price(raw: str) -> float | None:
    if not raw:
        return None
    cleaned = raw.replace("\xa0", "").replace("\u00a0", "").strip()
    # Format décimal : "46.99" ou "24,99"
    match = re.search(r"\d+[.,]\d{2}", cleaned)
    if match:
        return float(match.group().replace(",", "."))
    # Entier seul : "70"
    match = re.search(r"\d+", cleaned)
    if match:
        return float(match.group())
    return None


def parse_discount(raw: str) -> int | None:
    """Convertit '-33%' en 33."""
    if not raw:
        return None
    match = re.search(r"\d+", raw)
    return int(match.group()) if match else None

def scrape_game_urls_by_page(driver: webdriver.Chrome, wait: WebDriverWait, page: int) -> list[dict]:
    driver.get(BASE_URL.format(page=page))

    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".listing-items .item")))
    except Exception:
        return []

    games = driver.find_elements(By.CSS_SELECTOR, ".listing-items .item")
    results = []

    for idx, game in enumerate(games, 1):
        try:
            url = game.find_element(By.CSS_SELECTOR, ".item.force-badge a").get_attribute("href")
            print(f"  - {url}")
            # if (idx == 1):
                # return [{"url": url}]  # Test rapide : on ne scrape que le premier jeu de la page
            results.append({"url": url})
        except Exception:
            continue

    return results

def scrape_all_pages(max_pages: int = 10) -> list[dict]:
    """Boucle sur max_pages pages et agrège les résultats."""
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.maximize_window()
    wait = WebDriverWait(driver, 10)

    games_urls: list[dict] = []

    try:
        for page in range(1, max_pages + 1):
            print(f"Scraping page {page}...")
            urls = scrape_game_urls_by_page(driver, wait, page)

            if not urls:
                print(f"Page {page} vide — arrêt.")
                break

            games_urls.extend(urls)
            print(f"{len(urls)} jeux récupérés (total : {len(games_urls)})\n")
    except Exception as e:
        print(f"Erreur lors du scraping : {e}")

    print(f"\n[detail] Scraping de {len(games_urls)} pages produit...\n")

    full_games: list[dict] = []

    for idx, game in enumerate(games_urls, 1):
        print(f"Scraping jeu {idx}/{len(games_urls)} : {game['url']}")
        details = scrape_game_details(driver, wait, game["url"])
        full_games.append(details)

    driver.quit()
    return full_games

def scrape_game_details(driver: webdriver.Chrome, wait: WebDriverWait, url: str) -> dict:
    driver.get(url)

    try:
        infos_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".panel-container")))
        title = infos_container.find_element(By.CSS_SELECTOR, "h1").text.strip()
        price_raw = infos_container.find_element(By.CSS_SELECTOR, ".total").text.strip()
        discount_raw = infos_container.find_element(By.CSS_SELECTOR, ".discounted").text.strip() if infos_container.find_element(By.CSS_SELECTOR, ".discounted") else None
        original_price_raw = infos_container.find_element(By.CSS_SELECTOR, ".retail").text.strip() if driver.find_element(By.CSS_SELECTOR, ".retail") else None
        image_url = infos_container.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
        platform = infos_container.find_element(By.CSS_SELECTOR, ".platform-container span").text.strip() if infos_container.find_element(By.CSS_SELECTOR, ".platform-container span") else "N/A"
        
        return {
            "title": title,
            "price": parse_price(price_raw),
            "discount": parse_discount(discount_raw),
            "original_price": parse_price(original_price_raw),
            "platform": platform,
            "url": url,
            "image_url": image_url
        }
    except Exception:
        print(f"Erreur lors du scraping des détails : {url}")

if __name__ == "__main__":
    games = scrape_all_pages(max_pages=1)

    print(f"\n{'='*40}")
    print(f"{len(games)} jeux au total\n")
    for g in games:
        print(f"-"*40)
        print(f"{g['title']}")
        print(f"  {g['price']}")
        print(f"  {g['discount']}% de réduction" if g['discount'] else "  Pas de réduction")
        print(f"  Prix original : {g['original_price']}" if g['original_price'] else "  Prix original non disponible")
        print(f"  {g['url']}")
        print(f"  Image : {g['image_url']}")
        print(f"  Platforme : {g['platform']}")
