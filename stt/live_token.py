"""Ephemeral Gemini Live tokens so the browser can stream audio to Gemini directly.

The real API key stays on the server. Each token is single-use, short-lived and locked to our
model and transcription config, so a leaked token cannot be reused for anything else.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from google import genai
from google.genai import types

from stt.transcriber import transcription_config

LIVE_WS_URL = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained"
)
START_WINDOW = timedelta(minutes=10)  # a session must be started within this window
TOKEN_LIFETIME = timedelta(minutes=30)


@dataclass(frozen=True)
class LiveToken:
    value: str
    start_deadline: datetime

    def is_expiring(self, margin: timedelta = timedelta(seconds=60)) -> bool:
        return datetime.now(timezone.utc) >= self.start_deadline - margin


def create_live_token(api_key: str, model: str, language_codes: list[str]) -> LiveToken:
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    now = datetime.now(timezone.utc)
    token = client.auth_tokens.create(
        config=types.CreateAuthTokenConfig(
            uses=1,
            expire_time=now + TOKEN_LIFETIME,
            new_session_expire_time=now + START_WINDOW,
            live_connect_constraints=types.LiveConnectConstraints(
                model=model, config=transcription_config(language_codes)
            ),
        )
    )
    return LiveToken(value=token.name, start_deadline=now + START_WINDOW)
