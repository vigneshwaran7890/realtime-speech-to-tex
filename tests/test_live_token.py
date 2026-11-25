from datetime import datetime, timedelta, timezone

from stt.live_token import LIVE_WS_URL, LiveToken


def test_token_expiry_margin():
    now = datetime.now(timezone.utc)
    assert not LiveToken("t", now + timedelta(minutes=5)).is_expiring()
    assert LiveToken("t", now + timedelta(seconds=30)).is_expiring()
    assert LiveToken("t", now - timedelta(seconds=1)).is_expiring()


def test_websocket_url_uses_constrained_endpoint():
    assert LIVE_WS_URL.startswith("wss://")
    assert LIVE_WS_URL.endswith("v1beta.GenerativeService.BidiGenerateContentConstrained")
