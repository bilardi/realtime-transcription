"""AWS Transcribe Streaming integration.

Ported from video-to-text/app/transcribe_service.py with:
- configurable language (parameter, not hardcoded)
- is_partial flag passed to callback
"""

import asyncio
import contextlib
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import cast

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import (
    StartStreamTranscriptionEventStream,
    TranscriptEvent,
    TranscriptResultStream,
)


class TranscriptHandler(TranscriptResultStreamHandler):
    """Handles transcript events and queues results with partial flag."""

    def __init__(self, result_queue: asyncio.Queue[tuple[str, bool]]) -> None:
        """Initialize with a result queue used as both stream and output store."""
        super().__init__(cast("TranscriptResultStream", result_queue))
        self.result_queue = result_queue

    @classmethod
    def from_stream(
        cls,
        output_stream: TranscriptResultStream,
    ) -> "TranscriptHandler":
        """Create a handler wired to an AWS output stream.

        Args:
            output_stream: AWS Transcribe output stream to read events from.

        Returns:
            A new TranscriptHandler whose handle_events iterates the given stream.
        """
        result_queue: asyncio.Queue[tuple[str, bool]] = asyncio.Queue()
        instance = cls(result_queue)
        instance._transcript_result_stream = output_stream
        return instance

    async def handle_transcript_event(self, transcript_event: TranscriptEvent) -> None:
        """Enqueue (text, is_partial) tuples for all results."""
        results = transcript_event.transcript.results
        for result in results:
            for alt in result.alternatives or []:
                await self.result_queue.put((alt.transcript, bool(result.is_partial)))


class TranscribeService:
    """Manages a streaming session with Amazon Transcribe."""

    def __init__(self, region: str = "eu-west-1") -> None:
        """Initialize the Transcribe streaming client for the given AWS region."""
        self.client = TranscribeStreamingClient(region=region)

    async def start_transcription(
        self,
        audio_generator: AsyncGenerator[bytes],
        callback: Callable[[str, bool], Awaitable[None]],
        lang: str = "it-IT",
    ) -> None:
        """Open a Transcribe stream, send audio chunks, and invoke callback for each result.

        Args:
            audio_generator: async generator yielding PCM audio chunks.
            callback: called with (text, is_partial) for each result.
            lang: BCP-47 language code (e.g. "it-IT", "en-US").
        """
        stream = await self.client.start_stream_transcription(  # type: ignore[reportUnknownMemberType]
            language_code=lang,
            media_sample_rate_hz=16000,
            media_encoding="pcm",
        )

        async def send_audio() -> None:
            async for chunk in audio_generator:
                await stream.input_stream.send_audio_event(audio_chunk=chunk)
            await stream.input_stream.end_stream()

        await asyncio.gather(send_audio(), self._process_events(stream, callback))

    async def _process_events(
        self,
        stream: StartStreamTranscriptionEventStream,
        callback: Callable[[str, bool], Awaitable[None]],
    ) -> None:
        """Consume transcript events and forward to callback."""
        handler = TranscriptHandler.from_stream(stream.output_stream)
        drain_task = asyncio.ensure_future(self._drain_queue(handler.result_queue, callback))
        try:
            await handler.handle_events()
        finally:
            drain_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await drain_task

    @staticmethod
    async def _drain_queue(
        result_queue: asyncio.Queue[tuple[str, bool]],
        callback: Callable[[str, bool], Awaitable[None]],
    ) -> None:
        """Drain result queue and forward items to callback."""
        while True:
            text, is_partial = await result_queue.get()
            await callback(text, is_partial)
