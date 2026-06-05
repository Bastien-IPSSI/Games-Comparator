import os
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, Integer, String,
    Float, DateTime, ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={"charset": "utf8mb4"},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Game(Base):
    __tablename__ = "games"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    title            = Column(String(255), nullable=False)
    normalized_title = Column(String(255), nullable=False)
    platform         = Column(String(50))
    image_url        = Column(Text)
    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("normalized_title", "platform", name="uq_game_title_platform"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    prices = relationship("Price", back_populates="game", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Game(id={self.id}, title='{self.title}', platform='{self.platform}')>"


class Price(Base):
    __tablename__ = "prices"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    game_id        = Column(Integer, ForeignKey("games.id"), nullable=False)
    source         = Column(String(50), nullable=False)   # "instant-gaming", "g2a", "micromania"
    price          = Column(Float, nullable=False)
    original_price = Column(Float)
    discount_pct   = Column(Integer)
    url            = Column(Text)
    scraped_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    game = relationship("Game", back_populates="prices")

    def __repr__(self):
        return f"<Price(source='{self.source}', price={self.price}, game_id={self.game_id})>"


def init_db():
    """Crée toutes les tables si elles n'existent pas encore."""
    Base.metadata.create_all(bind=engine)
    print("Base de données initialisée.")


def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
