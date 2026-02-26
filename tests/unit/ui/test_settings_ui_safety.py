"""
Regression tests for NiceGUI UI safety.

Ensures that UI components (like settings) don't crash when
encountering unexpected values (e.g., an invalid model name).
"""

import pytest
from unittest.mock import MagicMock, patch
from opendata.ui.components.settings import render_settings_tab
from opendata.ui.context import AppContext
from opendata.models import UserSettings


@pytest.fixture
def app_context(tmp_path):
    """Create a mock application context with invalid model."""
    settings = UserSettings()
    settings.ai_provider = "openai"
    settings.openai_model = "invalid-model-that-causes-crash"

    ai = MagicMock()
    ai.is_authenticated.return_value = True
    ai.model_name = "invalid-model-that-causes-crash"
    # Available models don't include the current one
    ai.list_available_models.return_value = ["gpt-4", "gpt-3.5-turbo"]

    wm = MagicMock()
    agent = MagicMock()
    agent.project_id = None

    ctx = AppContext(
        wm=wm,
        agent=agent,
        ai=ai,
        pm=MagicMock(),
        pkg_mgr=MagicMock(),
        packaging_service=MagicMock(),
        settings=settings,
        port=8080,
    )
    return ctx


def test_render_settings_tab_safety_with_invalid_model(app_context):
    """
    Test that render_settings_tab doesn't crash with invalid model.

    NiceGUI ui.select raises ValueError if value is not in options.
    Our fix ensures the value is temporarily added to options.
    """
    # Mock NiceGUI components
    with (
        patch("nicegui.ui.column"),
        patch("nicegui.ui.row"),
        patch("nicegui.ui.label"),
        patch("nicegui.ui.button"),
        patch("nicegui.ui.input"),
        patch("nicegui.ui.checkbox"),
        patch("nicegui.ui.switch"),
        patch("nicegui.ui.separator"),
        patch("nicegui.ui.select") as mock_select,
    ):
        # Act: Render the settings tab
        render_settings_tab(app_context)

        # Assert: ui.select was called
        mock_select.assert_called()

        # Check the call that handled the AI model selection
        # We look for the call where value was our invalid model
        model_select_call = None
        for call in mock_select.call_args_list:
            if call.kwargs.get("value") == "invalid-model-that-causes-crash":
                model_select_call = call
                break

        assert model_select_call is not None, "AI Model select was not rendered"

        # Verify our fix: the invalid model MUST be in the options list
        options = model_select_call.kwargs.get("options", [])
        assert "invalid-model-that-causes-crash" in options
        assert "gpt-4" in options
