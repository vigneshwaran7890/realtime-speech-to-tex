"""Application settings loaded from environment variables, `.env` or Streamlit secrets."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

DEFAULT_LIVE_MODEL = "gemini-3.5-transcribe-live"
DEFAULT_DATABASE_URL = "sqlite:///data/transcriptions.db"


def _read(name: str, default: str | None = None) -> str | None:
    """Read a setting from the environment first, then from Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        secret = st.secrets.get(name)
        if secret:
            return str(secret)
    except Exception:  # No secrets file, or not running inside Streamlit.
        pass
    return default


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None
    live_model: str
    database_url: str
    turn_url: str | None
    turn_username: str | None
    turn_credential: str | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        gemini_api_key=_read("GEMINI_API_KEY") or _read("GOOGLE_API_KEY"),
        live_model=_read("GEMINI_LIVE_MODEL", DEFAULT_LIVE_MODEL),
        database_url=_read("DATABASE_URL", DEFAULT_DATABASE_URL),
        turn_url=_read("TURN_URL"),
        turn_username=_read("TURN_USERNAME"),
        turn_credential=_read("TURN_CREDENTIAL"),
    )
