import unicodedata
import re
from sqlalchemy.orm import Session

from .models import Game, Price


def normalize(title: str) -> str:
    """Lowercase, strip accents, remove punctuation — used for dedup matching."""
    title = title.lower().strip()
    title = unicodedata.normalize("NFD", title)
    title = "".join(c for c in title if unicodedata.category(c) != "Mn")
    title = re.sub(r"[^a-z0-9\s]", "", title)
    return re.sub(r"\s+", " ", title).strip()


def get_or_create_game(
    session: Session,
    title: str,
    platform: str,
    image_url: str = None,
) -> Game:
    """Return the matching Game row, creating it if it doesn't exist yet."""
    normalized = normalize(title)
    game = (
        session.query(Game)
        .filter_by(normalized_title=normalized, platform=platform)
        .first()
    )
    if not game:
        game = Game(
            title=title,
            normalized_title=normalized,
            platform=platform,
            image_url=image_url,
        )
        session.add(game)
        session.flush()
    elif image_url and not game.image_url:
        game.image_url = image_url
    return game


def add_price(
    session: Session,
    game_id: int,
    source: str,
    price: float,
    original_price: float = None,
    discount_pct: int = None,
    url: str = None,
) -> Price:
    """Insert a new price snapshot. History is never overwritten."""
    entry = Price(
        game_id=game_id,
        source=source,
        price=price,
        original_price=original_price,
        discount_pct=discount_pct,
        url=url,
    )
    session.add(entry)
    return entry
