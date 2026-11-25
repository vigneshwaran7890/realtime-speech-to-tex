"""Audio helpers: convert browser / file audio into the 16 kHz mono PCM16 Gemini Live expects."""

from __future__ import annotations

import io
from collections.abc import Iterable, Iterator

import av

SAMPLE_RATE = 16_000
BYTES_PER_SAMPLE = 2  # 16-bit PCM
CHUNK_MS = 100  # Gemini recommends ~100 ms chunks
CHUNK_BYTES = SAMPLE_RATE * BYTES_PER_SAMPLE * CHUNK_MS // 1000
MIME_TYPE = f"audio/pcm;rate={SAMPLE_RATE}"


def _new_resampler() -> av.AudioResampler:
    return av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)


def pcm_duration_seconds(pcm: bytes) -> float:
    return len(pcm) / (SAMPLE_RATE * BYTES_PER_SAMPLE)


class PcmConverter:
    """Stateful converter for a continuous stream of :class:`av.AudioFrame` (e.g. from WebRTC)."""

    def __init__(self) -> None:
        self._resampler = _new_resampler()

    def convert(self, frames: Iterable[av.AudioFrame]) -> bytes:
        out = bytearray()
        for frame in frames:
            for resampled in self._resampler.resample(frame):
                out += resampled.to_ndarray().tobytes()
        return bytes(out)


def decode_to_pcm16(data: bytes) -> bytes:
    """Decode an encoded audio file (wav, mp3, webm, ogg, m4a...) into 16 kHz mono PCM16."""
    resampler = _new_resampler()
    out = bytearray()
    with av.open(io.BytesIO(data)) as container:
        if not container.streams.audio:
            raise ValueError("The file does not contain an audio stream.")
        for frame in container.decode(container.streams.audio[0]):
            for resampled in resampler.resample(frame):
                out += resampled.to_ndarray().tobytes()
    for resampled in resampler.resample(None):  # flush buffered samples
        out += resampled.to_ndarray().tobytes()
    return bytes(out)


def iter_chunks(pcm: bytes, chunk_bytes: int = CHUNK_BYTES) -> Iterator[bytes]:
    for start in range(0, len(pcm), chunk_bytes):
        yield pcm[start : start + chunk_bytes]
