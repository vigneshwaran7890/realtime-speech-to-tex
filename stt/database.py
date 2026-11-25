"""Database layer: ORM model and a repository exposing CRUD operations for transcriptions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import DateTime, Engine, Float, Integer, String, Text, create_engine, func, or_, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

TITLE_MAX_LENGTH = 200
SOURCES = ("live", "clip", "manual")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Transcription(Base):
    __tablename__ = "transcriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(TITLE_MAX_LENGTH), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="auto")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual", index=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def __repr__(self) -> str:
        return f"<Transcription id={self.id} title={self.title!r}>"


@dataclass(frozen=True)
class Stats:
    total: int
    last_7_days: int


def _normalize_url(url: str) -> str:
    """Route plain Postgres URLs (`postgres://`, `postgresql://`) to the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def create_db_engine(database_url: str) -> Engine:
    url = _normalize_url(database_url)
    if url.startswith("sqlite:///") and not url.startswith("sqlite:///:memory:"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


class TranscriptionRepository:
    """CRUD operations for :class:`Transcription` records."""

    _EDITABLE_FIELDS = {"title", "text", "language"}

    def __init__(self, engine: Engine) -> None:
        self._sessions = sessionmaker(bind=engine, expire_on_commit=False)

    # -- Create ---------------------------------------------------------------
    def create(
        self,
        *,
        title: str,
        text: str,
        language: str = "auto",
        source: str = "manual",
        duration_seconds: float | None = None,
    ) -> Transcription:
        if source not in SOURCES:
            raise ValueError(f"Unknown source {source!r}; expected one of {SOURCES}.")
        record = Transcription(
            title=self._clean_title(title),
            text=self._clean_text(text),
            language=language,
            source=source,
            duration_seconds=duration_seconds,
        )
        with self._sessions.begin() as session:
            session.add(record)
        return record

    # -- Read -----------------------------------------------------------------
    def get(self, record_id: int) -> Transcription | None:
        with self._sessions() as session:
            return session.get(Transcription, record_id)

    def list(self, *, search: str | None = None, source: str | None = None, limit: int = 500) -> list[Transcription]:
        query = select(Transcription).order_by(Transcription.created_at.desc(), Transcription.id.desc()).limit(limit)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.where(or_(Transcription.title.ilike(pattern), Transcription.text.ilike(pattern)))
        if source:
            query = query.where(Transcription.source == source)
        with self._sessions() as session:
            return list(session.scalars(query))

    def stats(self) -> Stats:
        week_ago = _utcnow() - timedelta(days=7)
        with self._sessions() as session:
            total = session.scalar(select(func.count(Transcription.id))) or 0
            recent = session.scalar(select(func.count(Transcription.id)).where(Transcription.created_at >= week_ago)) or 0
        return Stats(total=total, last_7_days=recent)

    # -- Update ---------------------------------------------------------------
    def update(self, record_id: int, **changes: str) -> Transcription | None:
        unknown = set(changes) - self._EDITABLE_FIELDS
        if unknown:
            raise ValueError(f"Fields not editable: {sorted(unknown)}")
        if "title" in changes:
            changes["title"] = self._clean_title(changes["title"])
        if "text" in changes:
            changes["text"] = self._clean_text(changes["text"])

        with self._sessions.begin() as session:
            record = session.get(Transcription, record_id)
            if record is None:
                return None
            for field, value in changes.items():
                setattr(record, field, value)
        return record

    # -- Delete ---------------------------------------------------------------
    def delete(self, record_id: int) -> bool:
        with self._sessions.begin() as session:
            record = session.get(Transcription, record_id)
            if record is None:
                return False
            session.delete(record)
        return True

    # -- Validation -----------------------------------------------------------
    @staticmethod
    def _clean_title(title: str) -> str:
        title = (title or "").strip()
        if not title:
            raise ValueError("Title cannot be empty.")
        if len(title) > TITLE_MAX_LENGTH:
            raise ValueError(f"Title must be at most {TITLE_MAX_LENGTH} characters.")
        return title

    @staticmethod
    def _clean_text(text: str) -> str:
        text = (text or "").strip()
        if not text:
            raise ValueError("Transcription text cannot be empty.")
        return text
