import io
import math
import struct
import wave

from stt.audio import CHUNK_BYTES, SAMPLE_RATE, decode_to_pcm16, iter_chunks, pcm_duration_seconds
from stt.tts import detect_tts_language


def _sine_wav(seconds: float, rate: int = 44_100, channels: int = 2) -> bytes:
    frames = int(seconds * rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        samples = (int(8000 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(frames))
        wav.writeframes(b"".join(struct.pack("<h", s) * channels for s in samples))
    return buffer.getvalue()


def test_decode_resamples_to_16k_mono():
    pcm = decode_to_pcm16(_sine_wav(1.0))
    assert abs(pcm_duration_seconds(pcm) - 1.0) < 0.02
    assert len(pcm) % 2 == 0
    assert abs(len(pcm) // 2 - SAMPLE_RATE) < SAMPLE_RATE * 0.02


def test_iter_chunks_covers_all_bytes():
    data = bytes(range(256)) * 50
    chunks = list(iter_chunks(data))
    assert b"".join(chunks) == data
    assert all(len(c) == CHUNK_BYTES for c in chunks[:-1])


def test_detect_tts_language():
    assert detect_tts_language("Hello, how are you?") == "en"
    assert detect_tts_language("मेरा नाम Ravi है") == "hi"
