"""
Tests for chat component scan message persistence.

Ensures that after a successful scan, the statistics message
is added to chat history and remains visible to the user.
"""

from unittest.mock import MagicMock, patch

import pytest

from opendata.ui.state import ScanState


class TestChatScanMessagePersistence:
    """Test that scan statistics are properly added to chat history."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock app context for testing."""
        ctx = MagicMock()
        ctx.agent = MagicMock()
        ctx.agent.chat_history = []
        ctx.agent.refresh_inventory = MagicMock(
            return_value="Inventory refreshed. Project contains 5 files."
        )
        ctx.refresh = MagicMock()
        ctx.refresh_all = MagicMock()
        return ctx

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "test.txt").write_text("test content")
        return str(project_dir)

    def test_successful_scan_adds_message_to_chat_history(
        self, mock_context, temp_project_dir
    ):
        """After successful scan, statistics message is added to chat history."""
        # Arrange
        from opendata.ui.components.chat import handle_scan_only
        import asyncio

        ScanState.is_scanning = False
        ScanState.stop_event = None

        # Mock ui.notify to avoid NiceGUI context errors
        with patch("opendata.ui.components.chat.ui.notify"):
            # Act
            asyncio.run(handle_scan_only(mock_context, temp_project_dir))

        # Assert
        assert len(mock_context.agent.chat_history) == 1
        message_role, message_content = mock_context.agent.chat_history[0]
        assert message_role == "agent"
        assert "✅" in message_content
        assert "Inventory refreshed" in message_content
        assert "5 files" in message_content

    def test_cancelled_scan_adds_canceled_message(self, mock_context, temp_project_dir):
        """After cancelled scan, cancellation message is added to chat history.

        Note: This test documents current behavior where stop_event is recreated
        inside handle_scan_only (line 246), so cancellation via stop_event must
        happen during the scan, not before.
        """
        # Arrange
        from opendata.ui.components.chat import handle_scan_only
        import asyncio

        ScanState.is_scanning = True

        # Mock refresh_inventory to set the stop_event during execution
        def mock_refresh_with_cancel(*args, **kwargs):
            stop_ev = kwargs.get("stop_event")
            if stop_ev:
                stop_ev.set()  # Simulate cancellation during scan
            return "Scan cancelled"

        mock_context.agent.refresh_inventory = MagicMock(
            side_effect=mock_refresh_with_cancel
        )

        # Mock ui.notify to avoid NiceGUI context errors
        with patch("opendata.ui.components.chat.ui.notify"):
            # Act
            asyncio.run(handle_scan_only(mock_context, temp_project_dir))

        # Assert
        assert len(mock_context.agent.chat_history) == 1
        message_role, message_content = mock_context.agent.chat_history[0]
        assert message_role == "agent"
        assert "🛑" in message_content
        assert "cancelled" in message_content.lower()

    def test_scan_error_shows_notification(self, mock_context, temp_project_dir):
        """When scan fails, error notification is shown."""
        # Arrange
        from opendata.ui.components.chat import handle_scan_only
        import asyncio

        ScanState.is_scanning = False
        ScanState.stop_event = None

        mock_context.agent.refresh_inventory = MagicMock(
            side_effect=Exception("Scan failed")
        )

        # Act & Assert
        with patch("opendata.ui.components.chat.ui.notify") as mock_notify:
            asyncio.run(handle_scan_only(mock_context, temp_project_dir))

            # Assert error notification was called
            mock_notify.assert_called()
            assert any("Scan error" in str(call) for call in mock_notify.call_args_list)

    def test_scan_resets_state_after_completion(self, mock_context, temp_project_dir):
        """After scan completes, scanning state is reset."""
        # Arrange
        from opendata.ui.components.chat import handle_scan_only
        import asyncio
        import threading

        ScanState.is_scanning = True
        ScanState.stop_event = threading.Event()

        # Mock ui.notify to avoid NiceGUI context errors
        with patch("opendata.ui.components.chat.ui.notify"):
            # Act
            asyncio.run(handle_scan_only(mock_context, temp_project_dir))

        # Assert
        assert ScanState.is_scanning is False
        assert ScanState.stop_event is None
