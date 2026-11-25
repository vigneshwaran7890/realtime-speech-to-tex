"""Browser microphone component that streams audio straight to Gemini Live over a WebSocket.

The component captures the mic with an AudioWorklet, downsamples to 16 kHz PCM16, streams it to
Gemini using an ephemeral token and renders interim/final text live. It reports back to Python:

* ``{"event": "started", "id": ...}`` when a session begins (the token is now used up), and
* ``{"event": "finished", "id": ..., "text": ..., "duration": ..., "error": ...}`` when it ends.

No WebRTC/TURN is involved, so it works on any host that serves HTTPS.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_component = components.declare_component("live_mic", path=str(Path(__file__).parent / "frontend"))


def live_mic(
    *,
    token: str | None,
    ws_url: str,
    model: str,
    language_codes: list[str],
    max_seconds: int,
    key: str,
) -> dict[str, Any] | None:
    return _component(
        token=token,
        wsUrl=ws_url,
        model=model,
        languageCodes=language_codes,
        maxSeconds=max_seconds,
        key=key,
        default=None,
    )
