from types import SimpleNamespace

from stt.audio import CHUNK_BYTES
from stt.transcriber import LiveTranscriber


def _content(interim=None, final=None):
    return SimpleNamespace(
        interim_input_transcription=SimpleNamespace(text=interim) if interim is not None else None,
        input_transcription=SimpleNamespace(text=final) if final is not None else None,
    )


def test_interim_then_final_segments():
    t = LiveTranscriber("key", "model")
    t.handle_server_content(_content(interim="Kal meet"))
    assert t.interim_text == "Kal meet"
    assert t.final_text == ""

    t.handle_server_content(_content(final=" Kal meeting hai, "))
    assert t.interim_text == ""
    t.handle_server_content(_content(final="please join on time."))
    assert t.final_text == "Kal meeting hai, please join on time."


def test_stop_keeps_unfinalized_interim():
    t = LiveTranscriber("key", "model")
    t.handle_server_content(_content(final="Hello"))
    t.handle_server_content(_content(interim="world"))
    assert t.stop() == "Hello world"


def test_push_audio_batches_into_chunks():
    t = LiveTranscriber("key", "model")
    t.push_audio(b"\0" * (CHUNK_BYTES * 2 + 10))
    assert t._audio_queue.qsize() == 2
    assert round(t.audio_seconds, 3) == round((CHUNK_BYTES * 2 + 10) / 32000, 3)


def test_ignores_empty_content():
    t = LiveTranscriber("key", "model")
    t.handle_server_content(None)
    t.handle_server_content(_content(interim="", final=""))
    assert t.final_text == "" and t.interim_text == ""
