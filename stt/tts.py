"""Text-to-Speech using gTTS (open-source library) so saved transcriptions can be played back."""

from __future__ import annotations

import io
import re

from gtts import gTTS

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def detect_tts_language(text: str) -> str:
    """Pick a voice: Hindi if the text contains Devanagari script, otherwise English."""
    return "hi" if _DEVANAGARI.search(text) else "en"


def synthesize_speech(text: str, lang: str | None = None) -> bytes:
    """Return MP3 bytes for ``text``. Uses the Indian English accent for English."""
    text = text.strip()
    if not text:
        raise ValueError("Nothing to speak.")
    buffer = io.BytesIO()
    gTTS(text=text, lang=lang or detect_tts_language(text), tld="co.in").write_to_fp(buffer)
    return buffer.getvalue()
