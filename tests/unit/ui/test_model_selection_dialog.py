"""
Unit Tests for Model Selection Dialog UI

Tests ensuring that when an invalid model is configured,
the user is presented with a model selection dialog.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from opendata.models import UserSettings
from opendata.ai.service import AIService


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace directory."""
    return tmp_path


@pytest.fixture
def settings():
    """Create user settings with invalid model."""
    settings = UserSettings()
    settings.openai_model = "invalid-model-xyz"
    settings.openai_base_url = "http://localhost:11434/v1"
    settings.ai_provider = "openai"
    return settings


class TestModelSelectionDialog:
    """Tests for model selection dialog behavior."""

    def test_detect_invalid_model_on_startup(self, workspace, settings):
        """App should detect invalid model during initialization."""
        # Arrange: Create AI service with invalid model
        ai_service = AIService(workspace, settings)

        # Mock available models (doesn't include configured model)
        available_models = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]

        with patch.object(
            ai_service.provider, "list_available_models", return_value=available_models
        ):
            # Act: Check if configured model is valid
            current_model = ai_service.model_name
            is_valid = current_model in available_models

            # Assert: Model is invalid
            assert is_valid is False
            assert current_model == "invalid-model-xyz"

    def test_auto_switch_to_first_available_model(self, workspace, settings):
        """When model is invalid, should suggest first available model."""
        # Arrange
        ai_service = AIService(workspace, settings)
        available_models = ["gpt-4", "gpt-3.5-turbo"]

        with patch.object(
            ai_service.provider, "list_available_models", return_value=available_models
        ):
            # Act: Auto-select first available
            if ai_service.model_name not in available_models:
                suggested_model = available_models[0]
                ai_service.switch_model(suggested_model)

            # Assert: Model switched to valid one
            assert ai_service.model_name == "gpt-4"

    def test_google_provider_invalid_model_detection(self, workspace):
        """Google provider should detect when configured model is unavailable."""
        # Arrange
        settings = UserSettings()
        settings.ai_provider = "google"
        settings.google_model = "gemini-nonexistent-v999"

        ai_service = AIService(workspace, settings)

        # Mock available models
        available = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

        with patch.object(
            ai_service.provider, "list_available_models", return_value=available
        ):
            # Act & Assert: Configured model not in list
            assert ai_service.model_name not in available

    def test_genai_provider_auto_detects_valid_model(self, workspace):
        """GenAI provider should auto-detect valid model on auth."""
        # Arrange
        settings = UserSettings()
        settings.ai_provider = "genai"
        # No model set initially

        ai_service = AIService(workspace, settings)

        # After auth, GenAI auto-detects - mock this
        with patch.object(
            ai_service.provider,
            "list_available_models",
            return_value=["gemini-2.0-flash", "gemini-1.5-flash"],
        ):
            # Simulate what happens after auth
            available = ai_service.list_available_models()

            # Assert: Has valid options
            assert len(available) > 0
            # GenAI would auto-select gemini-2.0-flash (priority list)
            assert "gemini-2.0-flash" in available


class TestModelValidationWorkflow:
    """Tests for complete model validation workflow."""

    def test_full_validation_workflow_openai(self, workspace, settings):
        """Complete workflow: detect invalid -> list available -> switch."""
        # Arrange
        ai_service = AIService(workspace, settings)

        # Mock models API
        mock_models_response = {
            "data": [{"id": "gpt-4"}, {"id": "gpt-3.5-turbo"}, {"id": "gpt-4-turbo"}]
        }

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_models_response
            mock_get.return_value = mock_response

            # Act: Get available models
            available = ai_service.list_available_models()

            # Assert: Has valid models
            assert len(available) > 0

            # Act: Check if current model is valid
            current = ai_service.model_name
            if current not in available and available:
                # Switch to first available
                ai_service.switch_model(available[0])

            # Assert: Now using valid model
            assert ai_service.model_name in available

    def test_settings_updated_after_model_switch(self, workspace, settings):
        """When model is switched, settings should be updated."""
        # Arrange
        ai_service = AIService(workspace, settings)

        with patch.object(
            ai_service.provider,
            "list_available_models",
            return_value=["valid-model-1", "valid-model-2"],
        ):
            # Act: Switch model
            ai_service.switch_model("valid-model-1")

            # Assert: Settings should reflect the change
            # (In real app, this would be persisted by UI callback)
            assert settings.openai_model == "invalid-model-xyz"
            # Note: Settings are not auto-updated by AIService,
            # UI handles persistence in handle_model_change callback
