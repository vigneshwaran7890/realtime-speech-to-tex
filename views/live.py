"""Live transcription page: stream the microphone to Gemini Live, review the text and save it."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from stt.app_context import flash, get_repository, require_api_key, speak
from stt.audio import decode_to_pcm16, pcm_duration_seconds
from stt.config import get_settings
from stt.languages import LANGUAGE_OPTIONS, storage_label
from stt.live_mic import live_mic
from stt.live_token import LIVE_WS_URL, create_live_token
from stt.transcriber import transcribe_pcm

TOKEN_KEY = "live_token"
HANDLED_EVENTS_KEY = "live_handled_events"
LIVE_ERROR_KEY = "live_error"
DRAFT_META_KEY = "draft_meta"
DRAFT_TEXT_KEY = "draft_text"
DRAFT_TITLE_KEY = "draft_title"
MAX_SESSION_SECONDS = 570  # Gemini live transcription sessions are capped at 10 minutes


# -- Draft (review & save) ----------------------------------------------------------
def _set_draft(text: str, source: str, language: str, duration: float) -> bool:
    if not text.strip():
        return False
    label = "Live" if source == "live" else "Clip"
    st.session_state[DRAFT_META_KEY] = {"source": source, "language": language, "duration": duration}
    st.session_state[DRAFT_TEXT_KEY] = text
    st.session_state[DRAFT_TITLE_KEY] = f"{label} transcription - {datetime.now():%d %b %Y, %H:%M}"
    return True


def _clear_draft() -> None:
    for key in (DRAFT_META_KEY, DRAFT_TEXT_KEY, DRAFT_TITLE_KEY):
        st.session_state.pop(key, None)


def _save_draft() -> None:
    meta = st.session_state[DRAFT_META_KEY]
    try:
        record = get_repository().create(
            title=st.session_state[DRAFT_TITLE_KEY],
            text=st.session_state[DRAFT_TEXT_KEY],
            language=meta["language"],
            source=meta["source"],
            duration_seconds=meta["duration"],
        )
    except ValueError as exc:
        st.error(str(exc))
        return
    flash(f"Saved “{record.title}” to history.")
    _clear_draft()


def _render_draft() -> None:
    if DRAFT_META_KEY not in st.session_state:
        return
    st.subheader("Review & save")
    with st.form("draft_form"):
        st.text_input("Title", key=DRAFT_TITLE_KEY, max_chars=200)
        st.text_area("Transcription (editable)", key=DRAFT_TEXT_KEY, height=180)
        save_col, discard_col = st.columns(2)
        save_col.form_submit_button("💾 Save to history", type="primary", on_click=_save_draft, width="stretch")
        discard_col.form_submit_button("🗑️ Discard", on_click=_clear_draft, width="stretch")

    if st.button("🔊 Listen (Text-to-Speech)"):
        try:
            st.audio(speak(st.session_state[DRAFT_TEXT_KEY]), format="audio/mp3", autoplay=True)
        except Exception as exc:
            st.error(f"Text-to-Speech failed: {exc}")


# -- Live microphone (browser -> Gemini Live over WebSocket) -------------------------
def _session_token(api_key: str, model: str, language_codes: list[str]) -> str | None:
    """Return a fresh single-use token, minting a new one when needed."""
    language_key = storage_label(language_codes)
    cached = st.session_state.get(TOKEN_KEY)
    if cached is None or cached["language"] != language_key or cached["token"].is_expiring():
        try:
            token = create_live_token(api_key, model, language_codes)
        except Exception as exc:
            st.error(f"Could not start a Gemini Live session: {exc}")
            return None
        st.session_state[TOKEN_KEY] = cached = {"language": language_key, "token": token}
    return cached["token"].value


def _handle_live_event(event: dict | None, language_codes: list[str]) -> None:
    if not event or not event.get("id"):
        return
    handled: set[str] = st.session_state.setdefault(HANDLED_EVENTS_KEY, set())
    event_key = f"{event.get('event')}:{event['id']}"
    if event_key in handled:
        return
    handled.add(event_key)
    st.session_state.pop(TOKEN_KEY, None)  # the token is single-use: mint a new one for next time

    if event.get("event") == "started":
        st.session_state.pop(LIVE_ERROR_KEY, None)
    elif event.get("event") == "finished":
        if event.get("error"):
            st.session_state[LIVE_ERROR_KEY] = event["error"]
        saved = _set_draft(event.get("text", ""), "live", storage_label(language_codes), event.get("duration") or 0)
        if not saved and not event.get("error"):
            flash("No speech was detected. Please try again closer to the microphone.", icon="⚠️")
    st.rerun()


def _render_live_tab(api_key: str, model: str, language_codes: list[str]) -> None:
    st.write("Click **Start recording**, allow microphone access and speak. Click **Stop recording** when done.")
    token = _session_token(api_key, model, language_codes)
    event = live_mic(
        token=token,
        ws_url=LIVE_WS_URL,
        model=model,
        language_codes=language_codes,
        max_seconds=MAX_SESSION_SECONDS,
        key="live_mic",
    )
    if error := st.session_state.get(LIVE_ERROR_KEY):
        st.error(error)
    _handle_live_event(event, language_codes)


# -- Recorded / uploaded clip -----------------------------------------------------------
def _render_clip_tab(api_key: str, model: str, language_codes: list[str]) -> None:
    st.write("Record a short clip in the browser, or upload an existing audio file.")
    recorded = st.audio_input("Record a clip", key="clip_recorder")
    uploaded = st.file_uploader(
        "...or upload an audio file", type=["wav", "mp3", "m4a", "ogg", "webm", "flac"], key="clip_upload"
    )
    audio = recorded or uploaded
    if not st.button("Transcribe clip", type="primary", disabled=audio is None):
        return
    try:
        pcm = decode_to_pcm16(audio.getvalue())
    except Exception as exc:
        st.error(f"Could not read the audio file: {exc}")
        return
    with st.spinner("Transcribing with Gemini Live..."):
        try:
            text = transcribe_pcm(api_key, model, pcm, language_codes)
        except RuntimeError as exc:
            st.error(f"Transcription failed: {exc}")
            return
    if not _set_draft(text, "clip", storage_label(language_codes), round(pcm_duration_seconds(pcm), 1)):
        st.warning("No speech was detected in the clip.")


# -- Page ---------------------------------------------------------------------------------
st.title("🎙️ Real-time Speech to Text")
st.caption("Speak in Hindi, English or a mix of both. Gemini Live transcribes your words as you talk.")

settings = get_settings()
api_key = require_api_key()
language_label = st.selectbox(
    "Spoken language",
    list(LANGUAGE_OPTIONS),
    help="Hinglish mode writes mixed speech in Roman script, e.g. 'Kal meeting hai, please join on time'. "
    "Auto-detect writes Hindi in Devanagari.",
)
language_codes = LANGUAGE_OPTIONS[language_label]

live_tab, clip_tab = st.tabs(["🔴 Live microphone", "📼 Record or upload a clip"])
with live_tab:
    _render_live_tab(api_key, settings.live_model, language_codes)
with clip_tab:
    _render_clip_tab(api_key, settings.live_model, language_codes)

_render_draft()
