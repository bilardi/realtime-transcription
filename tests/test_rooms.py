import pytest
from unittest.mock import AsyncMock


class TestRoomRegistry:
    """Tests for RoomRegistry sala management."""

    def test_add_display_creates_room(self):
        from app.rooms import RoomRegistry

        registry = RoomRegistry()
        ws = AsyncMock()
        registry.add_display("sala-1", ws)
        assert "sala-1" in registry.rooms
        assert any(d.ws is ws for d in registry.rooms["sala-1"].displays)

    def test_remove_display(self):
        from app.rooms import RoomRegistry

        registry = RoomRegistry()
        ws = AsyncMock()
        registry.add_display("sala-1", ws)
        registry.remove_display("sala-1", ws)
        assert not any(d.ws is ws for d in registry.rooms["sala-1"].displays)

    def test_remove_display_nonexistent_room(self):
        from app.rooms import RoomRegistry

        registry = RoomRegistry()
        registry.remove_display("nonexistent", AsyncMock())

    def test_list_active_rooms(self):
        from app.rooms import RoomRegistry

        registry = RoomRegistry()
        registry.add_display("sala-1", AsyncMock())
        registry.add_display("sala-2", AsyncMock())
        assert set(registry.list_rooms()) == {"sala-1", "sala-2"}

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_displays(self):
        from app.rooms import RoomRegistry

        registry = RoomRegistry()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        registry.add_display("sala-1", ws1)
        registry.add_display("sala-1", ws2)

        await registry.broadcast("sala-1", "ciao", is_partial=False)

        expected = '{"text": "ciao", "is_partial": false}'
        ws1.send_text.assert_awaited_once_with(expected)
        ws2.send_text.assert_awaited_once_with(expected)

    @pytest.mark.asyncio
    async def test_broadcast_skips_partial_when_not_requested(self):
        from app.rooms import RoomRegistry

        registry = RoomRegistry()
        ws = AsyncMock()
        registry.add_display("sala-1", ws, show_partial=False)

        await registry.broadcast("sala-1", "ciao", is_partial=True)
        ws.send_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_broadcast_sends_partial_when_requested(self):
        from app.rooms import RoomRegistry

        registry = RoomRegistry()
        ws = AsyncMock()
        registry.add_display("sala-1", ws, show_partial=True)

        await registry.broadcast("sala-1", "ciao", is_partial=True)

        expected = '{"text": "ciao", "is_partial": true}'
        ws.send_text.assert_awaited_once_with(expected)

    def test_set_lang(self):
        from app.rooms import RoomRegistry

        registry = RoomRegistry()
        registry.set_lang("sala-1", "en-US")
        assert registry.get_lang("sala-1") == "en-US"

    def test_get_lang_default(self):
        from app.rooms import RoomRegistry

        registry = RoomRegistry()
        assert registry.get_lang("sala-1") == "it-IT"
