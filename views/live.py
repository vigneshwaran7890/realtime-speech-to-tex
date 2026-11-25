"""Live transcription page: stream the microphone to Gemini Live, review the text and save it."""

from __future__ import annotations

import html
import queue
import time
from datetime import datetime

import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer

from stt.app_context import flash, get_repository, require_api_key, rtc_configuration, speak
from stt.audio import PcmConverter, decode_to_pcm16, pcm_duration_seconds
from stt.config import get_settings
from stt.languages import LANGUAGE_OPTIONS, storage_label
from stt.transcriber import LiveTranscriber, transcribe_pcm

TRANSCRIBER_KEY = "live_transcriber"
CONVERTER_KEY = "live_converter"
DRAFT_META_KEY = "draft_meta"
DRAFT_TEXT_KEY = "draft_text"
DRAFT_TITLE_KEY = "draft_title"
UI_REFRESH_SECONDS = 0.3


# -- Draft (review & save) ----------------------------------------------------------
def _set_draft(text: str, source: str, language: str, duration: float) -> None:
    if not text.strip():
        st.warning("No speech was detected. Please try again, speaking a little closer to the microphone.")
        return
    label = "Live" if source == "live" else "Clip"
    st.session_state[DRAFT_META_KEY] = {"source": source, "language": language, "duration": duration}
    st.session_state[DRAFT_TEXT_KEY] = text
    st.session_state[DRAFT_TITLE_KEY] = f"{label} transcription - {datetime.now():%d %b %Y, %H:%M}"


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


# -- Live microphone ------------------------------------------------------------------
def _render_live_transcript(placeholder, transcriber: LiveTranscriber) -> None:
    with placeholder.container(border=True):
        if transcriber.error:
            st.error(f"Transcription stopped: {transcriber.error}")
        elif not transcriber.is_connected:
            st.caption("Connecting to Gemini Live...")
        else:
            seconds = int(transcriber.audio_seconds)
            st.caption(f"🔴 Listening · {seconds // 60}:{seconds % 60:02d}")

        final, interim = transcriber.final_text, transcriber.interim_text
        if final or interim:
            st.markdown(
                f'<div style="font-size:1.2rem;line-height:1.6">{html.escape(final)} '
                f'<span style="opacity:.55;font-style:italic">{html.escape(interim)}</span></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(":gray[Start speaking...]")


def _stream_live(ctx, placeholder, api_key: str, model: str, language_codes: list[str]) -> None:
    """Pump microphone frames into Gemini while the WebRTC stream is playing."""
    transcriber: LiveTranscriber | None = st.session_state.get(TRANSCRIBER_KEY)
    if transcriber is None:
        transcriber = LiveTranscriber(api_key, model, language_codes)
        transcriber.start()
        st.session_state[TRANSCRIBER_KEY] = transcriber
        st.session_state[CONVERTER_KEY] = PcmConverter()
    converter: PcmConverter = st.session_state[CONVERTER_KEY]

    last_render = 0.0
    while ctx.state.playing:
        if ctx.audio_receiver is None:
            time.sleep(0.1)
            continue
        try:
            frames = ctx.audio_receiver.get_frames(timeout=1)
        except queue.Empty:
            frames = []
        if frames:
            transcriber.push_audio(converter.convert(frames))

        now = time.monotonic()
        if now - last_render >= UI_REFRESH_SECONDS or transcriber.error:
            _render_live_transcript(placeholder, transcriber)
            last_render = now
        if transcriber.error:
            break


def _finalize_live_session(language_codes: list[str]) -> None:
    transcriber: LiveTranscriber | None = st.session_state.pop(TRANSCRIBER_KEY, None)
    st.session_state.pop(CONVERTER_KEY, None)
    if transcriber is None:
        return
    with st.spinner("Finalising transcript..."):
        text = transcriber.stop()
    if transcriber.error and not text:
        st.error(f"Transcription failed: {transcriber.error}")
        return
    _set_draft(text, "live", storage_label(language_codes), round(transcriber.audio_seconds, 1))


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
    _set_draft(text, "clip", storage_label(language_codes), round(pcm_duration_seconds(pcm), 1))


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
    st.write("Click **START**, allow microphone access and speak. Click **STOP** when you are done.")
    webrtc_ctx = webrtc_streamer(
        key="live-mic",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        rtc_configuration=rtc_configuration(),
        media_stream_constraints={"audio": True, "video": False},
    )
    transcript_placeholder = st.empty()
    if not webrtc_ctx.state.playing:
        _finalize_live_session(language_codes)

with clip_tab:
    _render_clip_tab(api_key, settings.live_model, language_codes)

_render_draft()

# Must run last: this loop blocks until the user presses STOP.
if webrtc_ctx.state.playing:
    _stream_live(webrtc_ctx, transcript_placeholder, api_key, settings.live_model, language_codes)
