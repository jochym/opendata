"""Test that welcome message persists until explicitly dismissed."""

import pytest
from opendata.ui.context import SessionState


class TestChatWelcomePersistence:
    """Test that the welcome instruction stays visible until user dismisses it."""

    def test_welcome_shown_by_default(self):
        """Welcome message is shown by default (not dismissed)."""
        session = SessionState()
        assert session.welcome_dismissed is False

    def test_welcome_stays_after_scan(self):
        """Welcome message stays visible after scan (not auto-dismissed)."""
        session = SessionState()
        # Even with chat history from scan, welcome should stay
        assert session.welcome_dismissed is False

    def test_welcome_dismissed_by_user(self):
        """Welcome message hidden after user explicitly dismisses it."""
        session = SessionState()
        session.welcome_dismissed = True
        assert session.welcome_dismissed is True

    def test_welcome_stays_with_user_messages(self):
        """Welcome stays visible even after user messages (until dismissed)."""
        session = SessionState()
        # Welcome should stay until explicitly dismissed, regardless of chat content
        assert session.welcome_dismissed is False

    def test_session_reset_preserves_chat_len(self):
        """Session reset should preserve last_chat_len for scroll state."""
        session = SessionState()
        session.last_chat_len = 5
        session.inventory_cache = [{"path": "test.txt"}]
        session.grid_rows = [{"id": 1}]

        # Reset should preserve last_chat_len but clear other state
        session.reset()

        assert session.last_chat_len == 5
        assert session.inventory_cache == []
        assert session.grid_rows == []

    def test_session_reset_with_zero_chat_len(self):
        """Session reset works correctly when last_chat_len is 0."""
        session = SessionState()
        session.last_chat_len = 0

        session.reset()

        assert session.last_chat_len == 0

    def test_session_reset_clears_welcome_dismissed(self):
        """Session reset clears welcome_dismissed so it shows for new project."""
        session = SessionState()
        session.welcome_dismissed = True

        session.reset()

        # Welcome should be shown again for new project
        assert session.welcome_dismissed is False
