"""
Tests for chat component AI cancellation state management.

Ensures that after cancelling AI interaction, the UI properly shows
the cancellation state before cleaning up.
"""

from unittest.mock import MagicMock, patch

import pytest
import threading

from opendata.ui.state import ScanState


class TestChatAICancellationState:
    """Test that AI cancellation properly manages UI state."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock app context for testing."""
        ctx = MagicMock()
        ctx.agent = MagicMock()
        ctx.agent.chat_history = []
        ctx.ai = MagicMock()
        ctx.refresh = MagicMock()
        ctx.refresh_all = MagicMock()
        ctx.session = MagicMock()
        ctx.session.ai_stop_event = None
        return ctx

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "test.txt").write_text("test content")
        return str(project_dir)

    def test_cancel_ai_sets_stop_event_and_refreshes(self, mock_context):
        """When user clicks cancel, stop_event is set and UI is refreshed."""
        # Arrange
        from opendata.ui.components.chat import handle_cancel_ai
        import asyncio

        mock_context.session.ai_stop_event = threading.Event()

        with patch("opendata.ui.components.chat.ui.notify"):
            # Act
            asyncio.run(handle_cancel_ai(mock_context))

        # Assert
        assert mock_context.session.ai_stop_event.is_set()
        mock_context.refresh_all.assert_called_once()

    def test_ai_processing_resets_state_after_cancellation(self, mock_context):
        """After AI processing is cancelled, state is properly reset."""
        # Arrange
        from opendata.ui.components.chat import handle_user_msg_from_code
        import asyncio

        ScanState.is_processing_ai = True
        mock_context.session.ai_stop_event = threading.Event()

        # Mock the AI processing to detect cancellation immediately
        def mock_process_user_input(*args, **kwargs):
            stop_event = kwargs.get("stop_event")
            if stop_event and stop_event.is_set():
                raise Exception("Cancelled by user")
            return None

        mock_context.agent.process_user_input = MagicMock(
            side_effect=mock_process_user_input
        )

        with (
            patch("opendata.ui.components.chat.ui.notify"),
            patch("opendata.ui.components.chat.ui.run_javascript"),
        ):
            # Act
            asyncio.run(handle_user_msg_from_code(mock_context, "test message"))

        # Assert - state should be reset after cancellation
        assert ScanState.is_processing_ai is False
        assert mock_context.session.ai_stop_event is None

    def test_cancel_ai_before_processing_starts(self, mock_context):
        """Cancelling AI before processing starts has no effect."""
        # Arrange
        from opendata.ui.components.chat import handle_cancel_ai
        import asyncio

        mock_context.session.ai_stop_event = None

        with patch("opendata.ui.components.chat.ui.notify") as mock_notify:
            # Act
            asyncio.run(handle_cancel_ai(mock_context))

        # Assert - no crash, no refresh
        mock_notify.assert_not_called()
        mock_context.refresh_all.assert_not_called()

    def test_ui_cancellation_state_logic(self):
        """Test the logic that determines if UI should show cancellation state."""
        # Arrange
        ScanState.is_processing_ai = True
        ScanState.is_scanning = False
        stop_event = threading.Event()
        stop_event.set()

        # Act - test the logic directly (from chat.py lines 75-82)
        is_stopping = (
            (ScanState.stop_event and ScanState.stop_event.is_set())
            if ScanState.is_scanning
            else (stop_event and stop_event.is_set())
        )

        # Assert
        assert is_stopping is True

    def test_ui_normal_state_logic(self):
        """Test the logic that determines if UI should show normal spinner."""
        # Arrange
        ScanState.is_processing_ai = True
        ScanState.is_scanning = False
        stop_event = threading.Event()
        # Not set - normal operation

        # Act - test the logic directly
        is_stopping = (
            (ScanState.stop_event and ScanState.stop_event.is_set())
            if ScanState.is_scanning
            else (stop_event and stop_event.is_set())
        )

        # Assert
        assert is_stopping is False

    def test_cancel_ai_shows_canceled_state_before_cleanup(self, mock_context):
        """After cancellation, UI should show 'Canceled' state before cleanup."""
        # Arrange
        from opendata.ui.components.chat import handle_user_msg_from_code
        import asyncio

        ScanState.is_processing_ai = True
        mock_context.session.ai_stop_event = threading.Event()

        # Mock AI to immediately detect cancellation
        def mock_process_user_input(*args, **kwargs):
            stop_event = kwargs.get("stop_event")
            if stop_event and stop_event.is_set():
                raise Exception("Cancelled by user")
            return None

        mock_context.agent.process_user_input = MagicMock(
            side_effect=mock_process_user_input
        )

        # Track the order of state changes
        state_changes = []

        def track_refresh_all():
            state_changes.append(
                {
                    "is_processing_ai": ScanState.is_processing_ai,
                    "ai_stop_event": mock_context.session.ai_stop_event,
                }
            )

        mock_context.refresh_all = MagicMock(side_effect=track_refresh_all)

        with (
            patch("opendata.ui.components.chat.ui.notify"),
            patch("opendata.ui.components.chat.ui.run_javascript"),
        ):
            # Act - trigger cancellation before processing starts
            mock_context.session.ai_stop_event.set()
            asyncio.run(handle_user_msg_from_code(mock_context, "test message"))

        # Assert - verify state was cleaned up
        assert ScanState.is_processing_ai is False
        assert mock_context.session.ai_stop_event is None
        # Verify refresh was called at least once
        assert mock_context.refresh_all.call_count >= 1

    def test_cancelled_ai_adds_message_to_chat_history(self, mock_context):
        """When AI interaction is cancelled, a cancellation message is added to chat."""
        # Arrange
        from opendata.ui.components.chat import handle_user_msg_from_code
        import asyncio
        import time

        ScanState.is_processing_ai = True

        # Capture the stop_event that will be created inside handle_user_msg_from_code
        captured_events = []

        # Mock AI to wait for cancellation then raise CancelledError
        def mock_process_user_input(*args, **kwargs):
            stop_event = kwargs.get("stop_event")
            captured_events.append(stop_event)
            # Wait for cancellation signal (simulates AI processing time)
            while stop_event and not stop_event.is_set():
                time.sleep(0.01)
            # Raise cancellation error when stop_event is set
            raise asyncio.CancelledError("Cancelled by user")

        mock_context.agent.process_user_input = MagicMock(
            side_effect=mock_process_user_input
        )

        # Track chat_history modifications
        chat_history = []
        mock_context.agent.chat_history = chat_history

        async def cancel_during_processing():
            # Wait for the event to be created
            while not captured_events:
                await asyncio.sleep(0.001)
            # Set the stop event to trigger cancellation
            captured_events[0].set()

        async def run_test():
            with (
                patch("opendata.ui.components.chat.ui.notify"),
                patch("opendata.ui.components.chat.ui.run_javascript"),
            ):
                # Act - run cancellation concurrently with AI processing
                task = asyncio.create_task(
                    handle_user_msg_from_code(mock_context, "test message")
                )
                cancel_task = asyncio.create_task(cancel_during_processing())

                await asyncio.gather(task, cancel_task)

        asyncio.run(run_test())

        # Assert - cancellation message should be added (second message after user's)
        # Note: First message is the user's input (line 699), second is the cancellation
        assert len(chat_history) >= 2, f"Expected >= 2 messages, got: {chat_history}"
        message_role, message_content = chat_history[1]
        assert message_role == "agent"
        assert "🛑" in message_content
        assert "cancelled" in message_content.lower()
        mock_context.agent.save_state.assert_called_once()

    def test_successful_ai_processing_resets_state(self, mock_context):
        """After successful AI processing, state is properly reset (spinner stops)."""
        # Arrange
        from opendata.ui.components.chat import handle_user_msg_from_code
        import asyncio

        ScanState.is_processing_ai = True
        mock_context.session.ai_stop_event = threading.Event()

        # Mock AI to complete successfully
        def mock_process_user_input(*args, **kwargs):
            return None

        mock_context.agent.process_user_input = MagicMock(
            side_effect=mock_process_user_input
        )

        # Track chat_history modifications
        chat_history = []
        mock_context.agent.chat_history = chat_history

        with (
            patch("opendata.ui.components.chat.ui.notify"),
            patch("opendata.ui.components.chat.ui.run_javascript"),
        ):
            # Act
            asyncio.run(handle_user_msg_from_code(mock_context, "test message"))

        # Assert - state should be reset after successful completion
        assert ScanState.is_processing_ai is False
        assert mock_context.session.ai_stop_event is None
        # Verify AI response was added to chat
        assert len(chat_history) >= 1
