import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule
from rapidfuzz import fuzz

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from database.models import init_db, SessionLocal
from database.crud import get_or_create_game, add_price, normalize as crud_normalize
from scrapers.gameplanet import scrape_all_pages as scrape_gamesplanet
from scrapers.instant_gaming import scrape_all_pages as scrape_instant_gaming
from scrapers.fanatical import scrape_all as scrape_fanatical

CONFIDENCE = 70
MIN_SITES  = 2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)


def _similarity(a: str, b: str) -> int:
    return max(fuzz.ratio(a, b), fuzz.token_sort_ratio(a, b))


def match_across_sites(games_by_site: dict[str, list[dict]]) -> list[dict]:
    """
    Regroupe les jeux présents sur ≥ MIN_SITES sites avec un score ≥ CONFIDENCE.

    Retourne une liste de groupes :
        [{"canonical": game_dict, "sites": {site_name: game_dict, ...}}, ...]

    Le jeu retenu comme canonique est celui du site le plus complet
    (fanatical > gamesplanet > instant_gaming).
    """
    PRIORITY = ["instant_gaming", "fanatical", "gamesplanet"]

    sites  = list(games_by_site.keys())
    normed = {
        site: [(crud_normalize(g["title"]), g) for g in games]
        for site, games in games_by_site.items()
    }
    used   = {site: set() for site in sites}
    groups = []

    for primary in sites:
        for i, (norm_i, game_i) in enumerate(normed[primary]):
            if i in used[primary]:
                continue

            group  = {primary: game_i}
            g_idxs = {primary: i}

            for other in sites:
                if other == primary:
                    continue
                best_score, best_k = 0, -1
                for k, (norm_k, _) in enumerate(normed[other]):
                    if k in used[other]:
                        continue
                    score = _similarity(norm_i, norm_k)
                    if score > best_score:
                        best_score, best_k = score, k
                if best_score >= CONFIDENCE and best_k >= 0:
                    group[other]  = normed[other][best_k][1]
                    g_idxs[other] = best_k

            if len(group) >= MIN_SITES:
                for site, idx in g_idxs.items():
                    used[site].add(idx)
                canonical = next(
                    (group[s] for s in PRIORITY if s in group),
                    game_i,
                )
                groups.append({"canonical": canonical, "sites": group})

    return groups


def _to_float(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = re.sub(r"[^\d,.]", "", str(val)).replace(",", ".").strip(".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def run_scraper(site: str, fn, **kwargs) -> list[dict]:
    log.info("[%s] Démarrage du scraping…", site)
    try:
        games = fn(**kwargs)
        log.info("[%s] %d jeux trouvés", site, len(games))
        return games
    except Exception as exc:
        log.error("[%s] Erreur : %s", site, exc)
        return []


def save_groups(groups: list[dict]) -> int:
    session = SessionLocal()
    saved   = 0
    try:
        for group in groups:
            canonical = group["canonical"]
            title     = canonical.get("title", "")
            if not title:
                continue

            game = get_or_create_game(
                session, title,
                canonical.get("platform", "PC"),
                canonical.get("image_url") or None,
            )

            for site, g in group["sites"].items():
                price = _to_float(g.get("price"))
                if price is None:
                    continue
                add_price(
                    session,
                    game_id        = game.id,
                    source         = site,
                    price          = price,
                    original_price = _to_float(g.get("original_price")),
                    discount_pct   = g.get("discount"),
                    url            = g.get("url") or None,
                )

            saved += 1

        session.commit()
    except Exception as exc:
        session.rollback()
        log.error("Erreur lors de la sauvegarde : %s", exc)
    finally:
        session.close()

    return saved


def run_job():
    log.info("=" * 60)
    log.info("Lancement du job — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    games_by_site = {
        "gamesplanet":    run_scraper("gamesplanet",    scrape_gamesplanet, max_pages=200),
        "instant_gaming": run_scraper("instant_gaming", scrape_instant_gaming, max_pages=2, headless=True),
        "fanatical":      run_scraper("fanatical",      scrape_fanatical),
    }

    sites_with_data = {s: v for s, v in games_by_site.items() if v}
    if len(sites_with_data) < MIN_SITES:
        log.warning("Moins de %d sites ont renvoyé des données — abandon.", MIN_SITES)
        return

    total = sum(len(v) for v in sites_with_data.values())
    log.info("Total scrapé : %d jeux sur %d sites", total, len(sites_with_data))

    log.info("Matching des titres (seuil %d%%)…", CONFIDENCE)
    groups = match_across_sites(sites_with_data)
    log.info("%d jeux présents sur %d+ sites", len(groups), MIN_SITES)

    saved = save_groups(groups)
    log.info("Enregistrés / mis à jour en base : %d", saved)
    log.info("Job terminé.\n")


if __name__ == "__main__":
    init_db()
    run_job()

    schedule.every(1).hours.do(run_job)
    log.info("Scheduler actif — prochain run dans 1 heure (Ctrl+C pour arrêter)")

    while True:
        schedule.run_pending()
        time.sleep(60)
