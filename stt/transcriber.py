"""Real-time transcription client for the Gemini Live API.

``LiveTranscriber`` owns a background thread running an asyncio event loop. Audio (16 kHz
mono PCM16) is pushed from any thread via :meth:`LiveTranscriber.push_audio`; interim and
final transcripts are collected thread-safely so a UI can poll them while audio streams.

Gemini Live sessions are limited to ~10 minutes, so the session is transparently rotated
before that limit; queued audio is kept, so nothing is lost across the reconnect.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
from contextlib import suppress
from typing import Any

from google import genai
from google.genai import types

from stt.audio import BYTES_PER_SAMPLE, CHUNK_BYTES, CHUNK_MS, MIME_TYPE, SAMPLE_RATE, iter_chunks

logger = logging.getLogger(__name__)

SESSION_ROTATE_SECONDS = 9 * 60  # reconnect before the 10-minute Live session limit
_STOP = None  # queue sentinel


class LiveTranscriber:
    def __init__(
        self,
        api_key: str,
        model: str,
        language_codes: list[str] | None = None,
        *,
        drain_quiet_seconds: float = 1.5,
        drain_max_seconds: float = 8.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._language_codes = list(language_codes or [])
        self._drain_quiet_seconds = drain_quiet_seconds
        self._drain_max_seconds = drain_max_seconds

        self._audio_queue: queue.Queue[bytes | None] = queue.Queue()
        self._pending = bytearray()  # batches small WebRTC frames into ~100 ms chunks
        self._audio_bytes = 0

        self._lock = threading.Lock()
        self._segments: list[str] = []
        self._interim = ""
        self._last_message_at = 0.0
        self._error: str | None = None

        self._connected = threading.Event()
        self._thread: threading.Thread | None = None
        self._stopped = False

    # -- Public API -------------------------------------------------------------
    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("Transcriber already started.")
        self._thread = threading.Thread(target=self._run, name="gemini-live", daemon=True)
        self._thread.start()

    def push_audio(self, pcm: bytes) -> None:
        """Queue PCM16 audio for streaming. Safe to call with frames of any size."""
        if self._stopped or not pcm:
            return
        self._audio_bytes += len(pcm)
        self._pending += pcm
        while len(self._pending) >= CHUNK_BYTES:
            self._audio_queue.put(bytes(self._pending[:CHUNK_BYTES]))
            del self._pending[:CHUNK_BYTES]

    def stop(self, timeout: float = 15.0) -> str:
        """Flush audio, wait for the final transcript and return the full text."""
        if not self._stopped:
            self._stopped = True
            if self._pending:
                self._audio_queue.put(bytes(self._pending))
                self._pending.clear()
            self._audio_queue.put(_STOP)
        if self._thread is not None:
            self._thread.join(timeout)
        with self._lock:
            # Keep any words that never received a final transcript.
            if self._interim:
                self._segments.append(self._interim.strip())
                self._interim = ""
        return self.final_text

    @property
    def final_text(self) -> str:
        with self._lock:
            return " ".join(s for s in self._segments if s)

    @property
    def interim_text(self) -> str:
        with self._lock:
            return self._interim

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def audio_seconds(self) -> float:
        return self._audio_bytes / (SAMPLE_RATE * BYTES_PER_SAMPLE)

    # -- Message handling (separated for unit testing) --------------------------
    def handle_server_content(self, content: Any) -> None:
        if content is None:
            return
        with self._lock:
            self._last_message_at = time.monotonic()
            interim = getattr(content, "interim_input_transcription", None)
            if interim is not None and interim.text:
                self._interim = interim.text
            final = getattr(content, "input_transcription", None)
            if final is not None and final.text:
                self._segments.append(final.text.strip())
                self._interim = ""

    # -- Background worker --------------------------------------------------------
    def _run(self) -> None:
        try:
            asyncio.run(self._main())
        except Exception as exc:  # surfaced to the UI via `.error`
            logger.exception("Gemini Live session failed")
            self._error = f"{type(exc).__name__}: {exc}"

    def _build_config(self) -> types.LiveConnectConfig:
        return types.LiveConnectConfig(
            response_modalities=[types.Modality.TEXT],
            input_audio_transcription=types.AudioTranscriptionConfig(language_codes=self._language_codes),
        )

    async def _main(self) -> None:
        client = genai.Client(api_key=self._api_key, http_options={"api_version": "v1beta"})
        config = self._build_config()
        finished = False
        while not finished:
            finished = await self._run_session(client, config)

    async def _run_session(self, client: genai.Client, config: types.LiveConnectConfig) -> bool:
        """Run one Live session. Returns True when the user stopped, False to rotate."""
        async with client.aio.live.connect(model=self._model, config=config) as session:
            self._connected.set()
            receiver = asyncio.create_task(self._receive_loop(session))
            try:
                finished = await self._send_loop(session, receiver, time.monotonic() + SESSION_ROTATE_SECONDS)
                await session.send_realtime_input(audio_stream_end=True)
                await self._drain(receiver)
            finally:
                receiver.cancel()
                with suppress(asyncio.CancelledError):
                    await receiver
        return finished

    async def _send_loop(self, session: Any, receiver: asyncio.Task, deadline: float) -> bool:
        while True:
            if receiver.done():
                receiver.result()  # re-raise a receive error
                raise ConnectionError("Gemini Live closed the connection.")
            if time.monotonic() >= deadline:
                return False
            chunk = await asyncio.to_thread(self._next_chunk)
            if chunk is _STOP:
                return True
            if chunk:
                await session.send_realtime_input(audio=types.Blob(data=chunk, mime_type=MIME_TYPE))

    def _next_chunk(self) -> bytes | None:
        try:
            return self._audio_queue.get(timeout=0.2)
        except queue.Empty:
            return b""

    async def _receive_loop(self, session: Any) -> None:
        while True:
            received = False
            async for message in session.receive():  # one iteration per model turn
                received = True
                self.handle_server_content(message.server_content)
            if not received:
                return

    async def _drain(self, receiver: asyncio.Task) -> None:
        """Wait for trailing final transcripts after the audio stream ended."""
        started = time.monotonic()
        while time.monotonic() - started < self._drain_max_seconds and not receiver.done():
            with self._lock:
                quiet_for = time.monotonic() - max(self._last_message_at, started)
                has_interim = bool(self._interim)
            if quiet_for >= self._drain_quiet_seconds and not has_interim:
                return
            await asyncio.sleep(0.1)


def transcribe_pcm(api_key: str, model: str, pcm: bytes, language_codes: list[str] | None = None) -> str:
    """Transcribe a complete recording by streaming it through a Live session."""
    transcriber = LiveTranscriber(api_key, model, language_codes, drain_quiet_seconds=3.0, drain_max_seconds=30.0)
    transcriber.start()
    for chunk in iter_chunks(pcm):
        transcriber.push_audio(chunk)
        time.sleep(CHUNK_MS / 1000 / 4)  # stream at ~4x real time to keep server-side VAD happy
        if transcriber.error:
            break
    text = transcriber.stop(timeout=60.0)
    if transcriber.error:
        raise RuntimeError(transcriber.error)
    return text
