from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

def scrape_page(driver: webdriver.Chrome, wait: WebDriverWait, page: int) -> list[dict]:
    driver.get(BASE_URL.format(page=page))

    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".listing-items .item")))
    except Exception:
        return []

    games = driver.find_elements(By.CSS_SELECTOR, ".listing-items .item")
    results = []

    for game in games:
        try:
            title = game.find_element(By.CSS_SELECTOR, ".information .title").text
            price = game.find_element(By.CSS_SELECTOR, ".information .price").text
            results.append({"title": title, "price": price})
        except Exception:
            continue

    return results


def scrape_all_pages(max_pages: int = 10) -> list[dict]:
    """Boucle sur max_pages pages et agrège les résultats."""
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.maximize_window()
    wait = WebDriverWait(driver, 10)

    all_games = []

    try:
        for page in range(1, max_pages + 1):
            print(f"Scraping page {page}...")
            games = scrape_page(driver, wait, page)

            if not games:
                print(f"Page {page} vide — arrêt.")
                break

            all_games.extend(games)
            print(f"{len(games)} jeux récupérés (total : {len(all_games)})")
    finally:
        driver.quit()

    return all_games


if __name__ == "__main__":
    games = scrape_all_pages(max_pages=5)

    print(f"\n{'='*40}")
    print(f"{len(games)} jeux au total\n")
    for g in games:
        print(f"{g['title']} — {g['price']}")