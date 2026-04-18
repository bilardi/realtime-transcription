import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestTranscriptHandler:
    """Tests for TranscriptHandler event processing."""

    @pytest.mark.asyncio
    async def test_final_result_queued_with_false(self):
        """Final results must be queued as (text, False)."""
        from app.transcribe_service import TranscriptHandler

        queue: asyncio.Queue[tuple[str, bool]] = asyncio.Queue()
        handler = TranscriptHandler(queue)

        mock_event = MagicMock()
        mock_result = MagicMock()
        mock_result.is_partial = False
        mock_alt = MagicMock()
        mock_alt.transcript = "ciao a tutti"
        mock_result.alternatives = [mock_alt]
        mock_event.transcript.results = [mock_result]

        await handler.handle_transcript_event(mock_event)

        text, is_partial = await queue.get()
        assert text == "ciao a tutti"
        assert is_partial is False

    @pytest.mark.asyncio
    async def test_partial_result_queued_with_true(self):
        """Partial results must be queued as (text, True)."""
        from app.transcribe_service import TranscriptHandler

        queue: asyncio.Queue[tuple[str, bool]] = asyncio.Queue()
        handler = TranscriptHandler(queue)

        mock_event = MagicMock()
        mock_result = MagicMock()
        mock_result.is_partial = True
        mock_alt = MagicMock()
        mock_alt.transcript = "ciao"
        mock_result.alternatives = [mock_alt]
        mock_event.transcript.results = [mock_result]

        await handler.handle_transcript_event(mock_event)

        text, is_partial = await queue.get()
        assert text == "ciao"
        assert is_partial is True


class TestTranscribeService:
    """Tests for TranscribeService streaming."""

    @pytest.mark.asyncio
    async def test_sends_audio_chunks_to_stream(self):
        """Audio chunks from generator must be sent to Transcribe input stream."""
        from app.transcribe_service import TranscribeService

        mock_stream = MagicMock()
        mock_stream.input_stream.send_audio_event = AsyncMock()
        mock_stream.input_stream.end_stream = AsyncMock()
        mock_stream.output_stream = AsyncMock()

        mock_client = AsyncMock()
        mock_client.start_stream_transcription.return_value = mock_stream

        service = TranscribeService.__new__(TranscribeService)
        service.client = mock_client

        chunks = [b"\x00\x01" * 512, b"\x00\x02" * 512]

        async def audio_gen():
            for chunk in chunks:
                yield chunk

        with patch(
            "app.transcribe_service.TranscriptHandler.handle_events",
            side_effect=AsyncMock(),
        ):
            callback = AsyncMock()
            await service.start_transcription(audio_gen(), callback, lang="it-IT")

        assert mock_stream.input_stream.send_audio_event.call_count == 2
        mock_stream.input_stream.end_stream.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_uses_language_parameter(self):
        """The language passed to start_transcription must reach AWS."""
        from app.transcribe_service import TranscribeService

        mock_stream = MagicMock()
        mock_stream.input_stream.send_audio_event = AsyncMock()
        mock_stream.input_stream.end_stream = AsyncMock()
        mock_stream.output_stream = AsyncMock()

        mock_client = AsyncMock()
        mock_client.start_stream_transcription.return_value = mock_stream

        service = TranscribeService.__new__(TranscribeService)
        service.client = mock_client

        async def empty_gen():
            return
            yield  # noqa: RET504

        with patch(
            "app.transcribe_service.TranscriptHandler.handle_events",
            side_effect=AsyncMock(),
        ):
            await service.start_transcription(empty_gen(), AsyncMock(), lang="en-US")

        call_kwargs = mock_client.start_stream_transcription.call_args[1]
        assert call_kwargs["language_code"] == "en-US"
