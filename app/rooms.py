"""Room registry: maps sala labels to connected display WebSockets."""

import json
from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class WebSocketLike(Protocol):
    """Minimal WebSocket interface required by RoomRegistry."""

    def send_text(self, data: str) -> Awaitable[None]: ...  # noqa: D102


@dataclass
class DisplayClient:
    """A connected display WebSocket with its preferences."""

    ws: WebSocketLike
    show_partial: bool = False


@dataclass
class Room:
    """State for a single sala."""

    displays: list[DisplayClient] = field(default_factory=list[DisplayClient])
    lang: str = "it-IT"


class RoomRegistry:
    """In-memory registry of rooms and their connected displays."""

    def __init__(self) -> None:
        """Initialize with an empty rooms dictionary."""
        self.rooms: dict[str, Room] = {}

    def _ensure_room(self, sala: str) -> Room:
        """Get or create a room."""
        if sala not in self.rooms:
            self.rooms[sala] = Room()
        return self.rooms[sala]

    def add_display(self, sala: str, ws: WebSocketLike, *, show_partial: bool = False) -> None:
        """Register a display WebSocket for a sala."""
        room = self._ensure_room(sala)
        room.displays.append(DisplayClient(ws=ws, show_partial=show_partial))

    def remove_display(self, sala: str, ws: WebSocketLike) -> None:
        """Unregister a display WebSocket."""
        if sala not in self.rooms:
            return
        self.rooms[sala].displays = [d for d in self.rooms[sala].displays if d.ws is not ws]

    def list_rooms(self) -> list[str]:
        """List all rooms with at least one display."""
        return [sala for sala, room in self.rooms.items() if room.displays]

    async def broadcast(self, sala: str, text: str, *, is_partial: bool) -> None:
        """Send transcript text to all displays in a sala."""
        if sala not in self.rooms:
            return
        message = json.dumps({"text": text, "is_partial": is_partial})
        for client in self.rooms[sala].displays:
            if is_partial and not client.show_partial:
                continue
            await client.ws.send_text(message)

    def set_lang(self, sala: str, lang: str) -> None:
        """Set the language for a sala."""
        room = self._ensure_room(sala)
        room.lang = lang

    def get_lang(self, sala: str) -> str:
        """Get the language for a sala, default it-IT."""
        if sala not in self.rooms:
            return "it-IT"
        return self.rooms[sala].lang
