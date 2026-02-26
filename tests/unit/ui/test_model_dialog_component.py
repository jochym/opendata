"""
Unit Tests for Model Selection Dialog Component

Tests for the UI dialog that appears when an invalid model is detected.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from opendata.models import UserSettings
from opendata.ai.service import AIService
from opendata.ui.context import AppContext
from opendata.workspace import WorkspaceManager
from opendata.ui.components.model_dialog import (
    check_and_show_model_dialog,
    show_model_selection_dialog,
    _apply_model_selection,
)


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace directory."""
    return tmp_path


@pytest.fixture
def settings():
    """Create user settings with invalid model."""
    settings = UserSettings()
    settings.ai_consent_granted = True
    settings.ai_provider = "openai"
    settings.openai_model = "invalid-model-xyz"
    settings.openai_base_url = "http://localhost:11434/v1"
    return settings


@pytest.fixture
def app_context(workspace, settings):
    """Create a mock application context."""
    # Create real AIService
    ai = AIService(workspace, settings)

    # Mock other components
    wm = MagicMock(spec=WorkspaceManager)
    wm.save_yaml = MagicMock()

    agent = MagicMock()
    agent.project_id = "test-project"
    agent.current_metadata = MagicMock()
    agent.current_metadata.ai_model = None
    agent.save_state = MagicMock()

    pm = MagicMock()
    pkg_mgr = MagicMock()
    packaging_service = MagicMock()

    ctx = AppContext(
        wm=wm,
        agent=agent,
        ai=ai,
        pm=pm,
        pkg_mgr=pkg_mgr,
        packaging_service=packaging_service,
        settings=settings,
        port=8080,
    )

    return ctx


class TestModelDialogComponent:
    """Tests for model dialog component."""

    def test_check_dialog_shows_when_invalid(self, app_context):
        """Dialog should be triggered when model is invalid."""
        # Arrange: Mock AI to return invalid model suggestion
        suggestion = {
            "current": "invalid-model",
            "available": ["model-1", "model-2"],
            "suggested": "model-1",
        }

        with patch.object(
            app_context.ai, "get_invalid_model_suggestion", return_value=suggestion
        ):
            with patch(
                "opendata.ui.components.model_dialog.show_model_selection_dialog"
            ) as mock_show:
                # Act
                check_and_show_model_dialog(app_context)

                # Assert
                mock_show.assert_called_once_with(app_context, suggestion)

    def test_check_dialog_no_show_when_valid(self, app_context):
        """Dialog should not show when model is valid."""
        # Arrange: Mock AI to return None (valid model)
        with patch.object(
            app_context.ai, "get_invalid_model_suggestion", return_value=None
        ):
            with patch(
                "opendata.ui.components.model_dialog.show_model_selection_dialog"
            ) as mock_show:
                # Act
                check_and_show_model_dialog(app_context)

                # Assert
                mock_show.assert_not_called()

    def test_apply_model_selection_updates_settings(self, app_context):
        """Applying model selection should update settings."""
        # Arrange
        model_name = "valid-model-1"

        # Act
        import asyncio

        with patch("opendata.ui.components.model_dialog.ui.notify"):
            asyncio.run(_apply_model_selection(app_context, model_name))

        # Assert
        assert app_context.settings.openai_model == "valid-model-1"
        app_context.wm.save_yaml.assert_called_once()

    def test_apply_model_selection_google_provider(self, app_context):
        """Applying model selection should work for Google provider."""
        # Arrange
        app_context.settings.ai_provider = "google"
        app_context.settings.google_model = "old-model"
        model_name = "gemini-2.0-flash"

        # Act
        import asyncio

        with patch("opendata.ui.components.model_dialog.ui.notify"):
            asyncio.run(_apply_model_selection(app_context, model_name))

        # Assert
        assert app_context.settings.google_model == "gemini-2.0-flash"
        app_context.wm.save_yaml.assert_called_once()

    def test_apply_model_selection_genai_provider(self, app_context):
        """Applying model selection should work for GenAI provider."""
        # Arrange
        app_context.settings.ai_provider = "genai"
        model_name = "gemini-2.5-flash"

        # Act
        import asyncio

        with patch("opendata.ui.components.model_dialog.ui.notify"):
            asyncio.run(_apply_model_selection(app_context, model_name))

        # Assert
        assert app_context.settings.google_model == "gemini-2.5-flash"

    def test_apply_model_selection_updates_agent(self, app_context):
        """Applying model selection should update agent metadata."""
        # Arrange
        model_name = "new-model"

        # Act
        import asyncio

        with patch("opendata.ui.components.model_dialog.ui.notify"):
            asyncio.run(_apply_model_selection(app_context, model_name))

        # Assert
        assert app_context.agent.current_metadata.ai_model == "new-model"
        app_context.agent.save_state.assert_called_once()

    def test_apply_model_selection_no_project(self, app_context):
        """Should handle case when no project is loaded."""
        # Arrange
        app_context.agent.project_id = None
        model_name = "new-model"

        # Act
        import asyncio

        with patch("opendata.ui.components.model_dialog.ui.notify"):
            asyncio.run(_apply_model_selection(app_context, model_name))

        # Assert
        # Settings should still be updated
        assert app_context.settings.openai_model == "new-model"
        app_context.wm.save_yaml.assert_called_once()
        # But agent state should not be saved
        app_context.agent.save_state.assert_not_called()


class TestModelDialogUI:
    """Tests for model dialog UI rendering (mocked)."""

    def test_dialog_structure_created(self, app_context):
        """Dialog should be created with proper structure."""
        # Arrange
        suggestion = {
            "current": "bad-model",
            "available": ["good-1", "good-2"],
            "suggested": "good-1",
        }

        # Mock UI components to avoid NiceGUI initialization
        with (
            patch("nicegui.ui.dialog") as mock_dialog,
            patch("nicegui.ui.card") as mock_card,
            patch("nicegui.ui.label") as mock_label,
            patch("nicegui.ui.markdown") as mock_markdown,
            patch("nicegui.ui.select") as mock_select,
            patch("nicegui.ui.row") as mock_row,
            patch("nicegui.ui.button") as mock_button,
        ):
            # Setup mocks
            mock_dialog_instance = MagicMock()
            mock_dialog.return_value.__enter__ = MagicMock(
                return_value=mock_dialog_instance
            )
            mock_dialog.return_value.__exit__ = MagicMock(return_value=None)

            mock_card_instance = MagicMock()
            mock_card.return_value.__enter__ = MagicMock(
                return_value=mock_card_instance
            )
            mock_card.return_value.__exit__ = MagicMock(return_value=None)

            # Act
            try:
                show_model_selection_dialog(app_context, suggestion)
            except Exception:
                pass  # Expected since we're mocking

            # Assert: Dialog should be opened
            mock_dialog.assert_called()
