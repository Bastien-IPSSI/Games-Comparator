"""
Orchestrateur de scraping — s'exécute toutes les heures.

Logique :
  1. Lance les 3 scrapers en séquence.
  2. Fait matcher les noms entre sites (fuzzy matching, seuil 90 %).
  3. N'enregistre un jeu que s'il est présent sur au moins 2 sites.
  4. Utilise le module `database` existant (MySQL / SQLAlchemy).
"""
import importlib.util
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule
from rapidfuzz import fuzz

# ── Chemins ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))          # permet d'importer `database`

from database.models import init_db, SessionLocal
from database.crud import get_or_create_game, add_price, normalize as crud_normalize

SCRIPTS_DIR = ROOT / "scrapers"

# ── Paramètres ────────────────────────────────────────────────────────────────
CONFIDENCE = 70    # score minimum (0-100) pour considérer deux titres identiques
MIN_SITES  = 2     # un jeu doit apparaître sur au moins N sites pour être sauvegardé

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ── Import dynamique (gère les noms de fichiers avec tiret) ──────────────────
def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# ── Normalisation étendue pour le matching cross-sites ───────────────────────
_EDITION_RE = re.compile(
    r"\b(deluxe|standard|gold|premium|ultimate|complete|goty|"
    r"game\s+of\s+the\s+year|remastered|definitive|enhanced|"
    r"anniversary|collectors?|bundle|edition|pack|dlc|remake)\b",
    re.IGNORECASE,
)
_ARTICLE_RE = re.compile(r"^(the|a|an|le|la|les|un|une|des)\s+")

def normalize_for_match(title: str) -> str:
    """Normalisation plus agressive que crud.normalize() : supprime aussi
    les suffixes d'édition et les articles, pour maximiser les matchs cross-sites."""
    t = crud_normalize(title)           # lowercase, accents, ponctuation
    t = _ARTICLE_RE.sub("", t)
    t = _EDITION_RE.sub("", t)
    return " ".join(t.split())

# ── Matching cross-sites ──────────────────────────────────────────────────────
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
        site: [(normalize_for_match(g["title"]), g) for g in games]
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

# ── Conversion de prix ────────────────────────────────────────────────────────
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

# ── Scrapers disponibles ──────────────────────────────────────────────────────
# Format : (site_name, filename, function_name, kwargs)
# Note : instant-gaming.py ouvre un Chrome visible (pas de mode headless natif).
SCRAPERS = [
    ("gamesplanet",    "gameplanet.py",     "scrape_all_pages", {}),
    ("instant_gaming", "instant-gaming.py", "scrape_all_pages", {"max_pages": 2, "headless": True}),
    ("fanatical",      "fanatical.py",      "scrape_all",       {}),
]

def run_scraper(site: str, filename: str, func: str, kwargs: dict) -> list[dict]:
    log.info("[%s] Démarrage du scraping…", site)
    try:
        mod    = _load_module(site, SCRIPTS_DIR / filename)
        games  = getattr(mod, func)(**kwargs)
        log.info("[%s] %d jeux trouvés", site, len(games))
        return games
    except Exception as exc:
        log.error("[%s] Erreur : %s", site, exc)
        return []

# ── Sauvegarde en base ────────────────────────────────────────────────────────
def save_groups(groups: list[dict]) -> int:
    session = SessionLocal()
    saved   = 0
    try:
        for group in groups:
            canonical = group["canonical"]
            title     = canonical.get("title", "")
            platform  = canonical.get("platform", "PC")
            image_url = canonical.get("image_url") or None

            if not title:
                continue

            game = get_or_create_game(session, title, platform, image_url)

            for site, g in group["sites"].items():
                price = _to_float(g.get("price"))
                if price is None:
                    continue     # prix inconnu → on ne crée pas de ligne Price
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

# ── Job principal ─────────────────────────────────────────────────────────────
def run_job():
    log.info("=" * 60)
    log.info("Lancement du job — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    # 1. Scraper
    games_by_site: dict[str, list[dict]] = {}
    for site, filename, func, kwargs in SCRAPERS:
        games_by_site[site] = run_scraper(site, filename, func, kwargs)

    sites_with_data = {s: v for s, v in games_by_site.items() if v}
    if len(sites_with_data) < MIN_SITES:
        log.warning("Moins de %d sites ont renvoyé des données — abandon.", MIN_SITES)
        return

    total = sum(len(v) for v in sites_with_data.values())
    log.info("Total scrapé : %d jeux sur %d sites", total, len(sites_with_data))

    # 2. Matcher
    log.info("Matching des titres (seuil %d%%)…", CONFIDENCE)
    groups = match_across_sites(sites_with_data)
    log.info("%d jeux présents sur %d+ sites", len(groups), MIN_SITES)

    # 3. Enregistrer
    saved = save_groups(groups)
    log.info("Enregistrés / mis à jour en base : %d", saved)
    log.info("Job terminé.\n")

# ── Point d'entrée ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()   # crée les tables si elles n'existent pas encore

    run_job()   # exécution immédiate au démarrage

    schedule.every(1).hours.do(run_job)
    log.info("Scheduler actif — prochain run dans 1 heure (Ctrl+C pour arrêter)")

    while True:
        schedule.run_pending()
        time.sleep(60)
