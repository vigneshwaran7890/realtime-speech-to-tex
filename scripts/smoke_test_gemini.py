"""End-to-end check of the Gemini Live pipeline without a microphone.

Synthesises a Hindi-English sentence with gTTS, streams it through Gemini Live and prints
the transcript.  Usage (from the project root, with GEMINI_API_KEY set or in .env):

    python -m scripts.smoke_test_gemini "Kal meeting hai, please join on time"
"""

from __future__ import annotations

import sys

from stt.audio import decode_to_pcm16, pcm_duration_seconds
from stt.config import get_settings
from stt.transcriber import transcribe_pcm
from stt.tts import synthesize_speech


def main() -> int:
    sentence = " ".join(sys.argv[1:]) or "Hello, mera naam Ravi hai aur main Bangalore mein kaam karta hoon."
    settings = get_settings()
    if not settings.gemini_api_key:
        print("GEMINI_API_KEY is not set (environment or .env).", file=sys.stderr)
        return 1

    pcm = decode_to_pcm16(synthesize_speech(sentence, lang="hi"))
    print(f"Model:      {settings.live_model}")
    print(f"Input:      {sentence}  ({pcm_duration_seconds(pcm):.1f}s of audio)")
    transcript = transcribe_pcm(settings.gemini_api_key, settings.live_model, pcm)
    print(f"Transcript: {transcript or '<empty>'}")
    return 0 if transcript else 2


if __name__ == "__main__":
    raise SystemExit(main())
