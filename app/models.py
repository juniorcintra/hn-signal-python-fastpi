from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .enums import EnrichmentStatus


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    hn_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    author: Mapped[str] = mapped_column(String, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)

    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    enrichment_status: Mapped[EnrichmentStatus] = mapped_column(
        SAEnum(EnrichmentStatus), default=EnrichmentStatus.pending, nullable=False
    )

    summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    technical_level: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    enriched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    enrichment_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("ix_articles_hn_id", "hn_id"),
        Index("ix_articles_category", "category"),
        Index("ix_articles_enrichment_status", "enrichment_status"),
    )
