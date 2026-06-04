import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "https://fr.gamesplanet.com/search"
PARAMS_BASE = {"av": "rel", "t": "game", "query": ""}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def scrape_page(session: requests.Session, page: int) -> list[dict]:
    """Scrape une page et retourne une liste de jeux {title, price, url}."""
    params = {**PARAMS_BASE, "page": page}
    response = session.get(BASE_URL, params=params, headers=HEADERS, timeout=10)

    if response.status_code != 200:
        print(f"  [!] HTTP {response.status_code} sur la page {page}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    items = soup.select("#search_filtered_view .game_list")

    results = []
    for item in items:
        try:
            title_el = item.select_one("h4 a")
            price_el = item.select_one(".price_current")

            title = title_el.get_text(strip=True) if title_el else "N/A"
            href  = title_el["href"] if title_el else ""
            price = price_el.get_text(strip=True) if price_el else "N/A"

            results.append({
                "title": title,
                "price": price,
                "url": f"https://fr.gamesplanet.com{href}" if href.startswith("/") else href,
            })
        except Exception:
            continue

    return results


def get_total_pages(session: requests.Session) -> int:
    """Récupère le nombre total de pages depuis la pagination."""
    response = session.get(BASE_URL, params=PARAMS_BASE, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    page_links = soup.select(".pagination a[href*='page=']")
    pages = []
    for link in page_links:
        href = link.get("href", "")
        if "page=" in href:
            try:
                num = int(href.split("page=")[-1])
                pages.append(num)
            except ValueError:
                continue

    return max(pages) if pages else 1


def scrape_all_pages(max_pages: int | None = None, delay: float = 0.5) -> list[dict]:
    """
    Boucle sur toutes les pages (ou max_pages si défini).
    delay : pause en secondes entre chaque requête (évite le ban).
    """
    session = requests.Session()

    total = get_total_pages(session)
    limit = min(total, max_pages) if max_pages else total
    print(f"Pages détectées : {total} — scraping des {limit} premières\n")

    all_games = []

    for page in range(1, limit + 1):
        print(f"Scraping page {page}/{limit}...", end=" ")
        games = scrape_page(session, page)

        if not games:
            print("vide")
            break

        all_games.extend(games)
        print(f"{len(games)} jeux (total : {len(all_games)})")

        if page < limit:
            time.sleep(delay)

    return all_games


if __name__ == "__main__":
    games = scrape_all_pages(max_pages=5)

    print(f"\n{'='*50}")
    print(f"{len(games)} jeux récupérés au total\n")
    for g in games:
        print(f"{g['title']} — {g['price']}")
        print(f"  {g['url']}")