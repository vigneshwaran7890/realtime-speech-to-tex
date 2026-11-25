"""Streamlit glue: cached resources, API-key handling and small UI helpers shared by pages."""

from __future__ import annotations

import streamlit as st

from stt.config import get_settings
from stt.database import TranscriptionRepository, create_db_engine, init_db
from stt.tts import synthesize_speech

_API_KEY_STATE = "user_gemini_api_key"
_FLASH_STATE = "flash_message"


@st.cache_resource(show_spinner=False)
def get_repository() -> TranscriptionRepository:
    engine = create_db_engine(get_settings().database_url)
    init_db(engine)
    return TranscriptionRepository(engine)


def get_api_key() -> str | None:
    return st.session_state.get(_API_KEY_STATE) or get_settings().gemini_api_key


def render_sidebar() -> None:
    settings = get_settings()
    with st.sidebar:
        st.subheader("Settings")
        if settings.gemini_api_key:
            st.success("Gemini API key loaded from environment.", icon="🔑")
        else:
            st.text_input(
                "Gemini API key",
                type="password",
                key=_API_KEY_STATE,
                help="Stored only in this browser session. Set GEMINI_API_KEY to avoid entering it.",
            )
        st.caption(f"Model: `{settings.live_model}`")
        backend = settings.database_url.split(":", 1)[0]
        st.caption(f"Database: `{backend}`")


def require_api_key() -> str:
    api_key = get_api_key()
    if not api_key:
        st.warning("Add your Gemini API key in the sidebar (or set `GEMINI_API_KEY`) to start transcribing.", icon="🔑")
        st.stop()
    return api_key


def rtc_configuration() -> dict | None:
    """ICE servers for WebRTC.

    With a manual ``TURN_URL`` (comma-separated URLs allowed) that server is used. Otherwise ``None``
    lets streamlit-webrtc pick a TURN provider from its own env vars: ``CLOUDFLARE_TURN_KEY_ID`` +
    ``CLOUDFLARE_TURN_KEY_API_TOKEN``, ``TWILIO_ACCOUNT_SID`` + ``TWILIO_AUTH_TOKEN`` or ``HF_TOKEN``
    (falling back to STUN only). A TURN relay is required on hosts such as Render that block UDP.
    """
    settings = get_settings()
    if not settings.turn_url:
        return None
    turn_urls = [url.strip() for url in settings.turn_url.split(",") if url.strip()]
    return {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {"urls": turn_urls, "username": settings.turn_username, "credential": settings.turn_credential},
        ]
    }


@st.cache_data(show_spinner="Generating speech...", max_entries=64)
def speak(text: str) -> bytes:
    return synthesize_speech(text)


def flash(message: str, icon: str = "✅") -> None:
    """Queue a toast to show after the next rerun."""
    st.session_state[_FLASH_STATE] = (message, icon)


def show_flash() -> None:
    if message := st.session_state.pop(_FLASH_STATE, None):
        st.toast(message[0], icon=message[1])
