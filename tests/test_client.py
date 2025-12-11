"""Tests for Vox8Client."""

import json

import pytest

from vox8 import Vox8Client


class FakeWS:
    """Fake WebSocket for testing."""

    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.closed = False

    class state:
        name = "OPEN"

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))

    async def close(self) -> None:
        self.closed = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


@pytest.fixture
def fake_ws(monkeypatch):
    """Create a fake WebSocket and patch the connect function."""
    ws = FakeWS()

    async def fake_connect(url):
        return ws

    monkeypatch.setattr("vox8.client.websockets.connect", fake_connect)
    return ws


@pytest.mark.asyncio
async def test_connect_sends_session_start(fake_ws):
    """Test that connect sends a session_start message."""
    client = Vox8Client(api_key="vox8_test_key", target_language="es")
    await client.connect()

    assert len(fake_ws.sent) == 1
    msg = fake_ws.sent[0]
    assert msg["type"] == "session_start"
    assert msg["api_key"] == "vox8_test_key"
    assert msg["target_language"] == "es"
    assert msg["source_language"] == "auto"
    assert msg["voice_mode"] == "match"
    assert msg["audio_format"] == "pcm_s16le"


@pytest.mark.asyncio
async def test_send_audio(fake_ws):
    """Test that send_audio sends an audio message."""
    client = Vox8Client(api_key="vox8_test_key", target_language="es")
    await client.connect()
    await client.send_audio("ZGF0YQ==")

    assert len(fake_ws.sent) == 2
    msg = fake_ws.sent[1]
    assert msg["type"] == "audio"
    assert msg["audio"] == "ZGF0YQ=="


@pytest.mark.asyncio
async def test_send_keepalive(fake_ws):
    """Test that send_keepalive sends a keepalive message."""
    client = Vox8Client(api_key="vox8_test_key", target_language="es")
    await client.connect()
    await client.send_keepalive()

    assert len(fake_ws.sent) == 2
    msg = fake_ws.sent[1]
    assert msg["type"] == "keepalive"


@pytest.mark.asyncio
async def test_disconnect(fake_ws):
    """Test that disconnect sends session_end and closes the connection."""
    client = Vox8Client(api_key="vox8_test_key", target_language="es")
    await client.connect()
    await client.disconnect()

    assert fake_ws.closed is True
    assert any(msg["type"] == "session_end" for msg in fake_ws.sent)


@pytest.mark.asyncio
async def test_is_connected(fake_ws):
    """Test the is_connected property."""
    client = Vox8Client(api_key="vox8_test_key", target_language="es")
    assert client.is_connected is False

    await client.connect()
    assert client.is_connected is True


@pytest.mark.asyncio
async def test_custom_config(fake_ws):
    """Test custom configuration options."""
    client = Vox8Client(
        api_key="vox8_test_key",
        target_language="fr",
        source_language="en",
        voice_mode="female",
    )
    await client.connect()

    msg = fake_ws.sent[0]
    assert msg["target_language"] == "fr"
    assert msg["source_language"] == "en"
    assert msg["voice_mode"] == "female"
