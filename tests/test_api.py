import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient


async def _mock_start_transcription(audio_generator, callback, lang="it-IT"):
    """Drain audio generator and fire a single fake final transcript."""
    async for _ in audio_generator:
        pass
    await callback("test transcript", False)


class TestHttpEndpoints:
    """Tests for HTTP endpoints."""

    @pytest.mark.asyncio
    async def test_root_redirects(self):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/", follow_redirects=False)
        assert response.status_code == 307

    @pytest.mark.asyncio
    async def test_sala_returns_html(self):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/sala/test-room")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "test-room" in response.text

    @pytest.mark.asyncio
    async def test_api_sale_empty(self):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/sale")
        assert response.status_code == 200
        assert response.json() == {"sale": []}


class TestWsAudio:
    """Tests for audio WebSocket endpoint."""

    def test_audio_triggers_transcription(self):
        from app.main import app

        with patch(
            "app.main.transcribe_service.start_transcription",
            side_effect=_mock_start_transcription,
        ):
            with TestClient(app) as client:
                with client.websocket_connect("/ws/audio/sala-1?lang=it-IT") as ws:
                    ws.send_bytes(b"\x00\x01" * 1024)
                    ws.close()

    def test_audio_passes_language(self):
        from app.main import app

        captured_lang: dict[str, str] = {}

        async def capture_lang(audio_generator, callback, lang="it-IT"):
            captured_lang["lang"] = lang
            async for _ in audio_generator:
                pass
            await callback("test", False)

        with patch(
            "app.main.transcribe_service.start_transcription",
            side_effect=capture_lang,
        ):
            with TestClient(app) as client:
                with client.websocket_connect("/ws/audio/sala-1?lang=en-US") as ws:
                    ws.send_bytes(b"\x00\x01" * 512)
                    ws.close()

        assert captured_lang["lang"] == "en-US"


class TestWsTranscript:
    """Tests for transcript WebSocket endpoint."""

    def test_display_receives_transcript(self):
        from app.main import app

        with patch(
            "app.main.transcribe_service.start_transcription",
            side_effect=_mock_start_transcription,
        ):
            with TestClient(app) as client:
                with client.websocket_connect("/ws/transcript/sala-1") as ws_display:
                    with client.websocket_connect(
                        "/ws/audio/sala-1?lang=it-IT"
                    ) as ws_audio:
                        ws_audio.send_bytes(b"\x00\x01" * 1024)
                        ws_audio.close()

                    msg = ws_display.receive_json()
                    assert msg["text"] == "test transcript"
                    assert msg["is_partial"] is False
