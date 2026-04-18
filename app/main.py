"""FastAPI server: HTTP and WebSocket endpoints for realtime transcription."""

import asyncio
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .rooms import RoomRegistry
from .transcribe_service import TranscribeService

load_dotenv()

app = FastAPI()

region = os.getenv("AWS_REGION", "eu-west-1")
transcribe_service = TranscribeService(region=region)
registry = RoomRegistry()

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root() -> RedirectResponse:
    """Redirect to active rooms list."""
    return RedirectResponse(url="/api/sale")


@app.get("/sala/{sala}")
async def get_sala(sala: str) -> HTMLResponse:
    """Serve the display page for a sala."""
    html_path = STATIC_DIR / "index.html"
    html = html_path.read_text(encoding="utf-8")
    html = html.replace("__SALA__", sala)
    return HTMLResponse(html)


@app.get("/api/sale")
async def list_sale() -> dict[str, list[str]]:
    """List active rooms."""
    return {"sale": registry.list_rooms()}


@app.websocket("/ws/audio/{sala}")
async def ws_audio(
    websocket: WebSocket,
    sala: str,
    lang: str = Query("it-IT"),
) -> None:
    """Receive PCM audio chunks and stream to AWS Transcribe."""
    await websocket.accept()

    registry.set_lang(sala, lang)
    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def audio_producer() -> None:
        try:
            while True:
                data = await websocket.receive_bytes()
                await audio_queue.put(data)
        except WebSocketDisconnect:
            await audio_queue.put(None)
        except Exception:  # noqa: BLE001
            await audio_queue.put(None)

    async def stream_generator() -> AsyncGenerator[bytes]:
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                break
            yield chunk

    async def on_transcript(text: str, is_partial: bool) -> None:
        await registry.broadcast(sala, text, is_partial=is_partial)

    producer_task = asyncio.create_task(audio_producer())

    try:
        await transcribe_service.start_transcription(stream_generator(), on_transcript, lang=lang)
    finally:
        await producer_task


@app.websocket("/ws/transcript/{sala}")
async def ws_transcript(
    websocket: WebSocket,
    sala: str,
    partial: bool = Query(False),
) -> None:
    """Send transcript text to display clients."""
    await websocket.accept()
    registry.add_display(sala, websocket, show_partial=partial)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        registry.remove_display(sala, websocket)
