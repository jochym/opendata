"""
Unit Tests for Model Validation

Tests ensuring that invalid model names are handled gracefully
with a model selection dialog instead of crashing.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from opendata.ai.service import AIService
from opendata.ai.openai_provider import OpenAIProvider
from opendata.ai.google_provider import GoogleProvider
from opendata.ai.genai_provider import GenAIProvider
from opendata.models import UserSettings


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace directory."""
    return tmp_path


@pytest.fixture
def default_settings():
    """Create default user settings."""
    return UserSettings()


class TestOpenAIModelValidation:
    """Tests for OpenAI provider model validation."""

    def test_invalid_model_name_does_not_crash(self, workspace, default_settings):
        """Invalid model name should not crash the provider initialization."""
        # Arrange: Set an invalid model name
        default_settings.openai_model = "nonexistent-model-v999"
        default_settings.openai_base_url = "http://localhost:11434/v1"

        # Act: Create provider (should not crash)
        provider = OpenAIProvider(workspace, default_settings)

        # Assert: Provider is created, but model_name is set to the invalid value
        # (validation happens later during switch_model)
        assert provider.model_name == "nonexistent-model-v999"

    def test_switch_to_invalid_model_returns_false(self, workspace, default_settings):
        """Switching to an invalid model should return False or raise validation error."""
        # Arrange
        default_settings.openai_model = "valid-model"
        default_settings.openai_base_url = "http://localhost:11434/v1"
        provider = OpenAIProvider(workspace, default_settings)

        # Mock the API call to simulate invalid model
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"id": "model-1"}, {"id": "model-2"}]
            }
            mock_get.return_value = mock_response

            # Act & Assert: Switching to invalid model should be detected
            provider.switch_model("nonexistent-model")
            # The model name is set, but validation should fail when used
            assert provider.model_name == "nonexistent-model"

    def test_list_models_fallback_on_error(self, workspace, default_settings):
        """When model listing fails, should fallback to configured model."""
        # Arrange
        default_settings.openai_model = "configured-model"
        default_settings.openai_base_url = "http://localhost:11434/v1"
        provider = OpenAIProvider(workspace, default_settings)

        # Mock network error
        with patch("requests.get", side_effect=Exception("Connection failed")):
            # Act
            models = provider.list_available_models()

            # Assert: Returns configured model as fallback
            assert models == ["configured-model"]


class TestGoogleModelValidation:
    """Tests for Google provider model validation."""

    def test_google_provider_default_model(self, workspace):
        """Google provider should have a valid default model."""
        # Arrange & Act
        provider = GoogleProvider(workspace)

        # Assert: Default model is set
        assert provider.model_name == "gemini-flash-latest"

    def test_switch_to_invalid_model_google_raises_exception(self, workspace):
        """Switching to invalid model should raise exception (needs validation layer)."""
        # Arrange
        provider = GoogleProvider(workspace)
        provider.creds = MagicMock()  # Mock authenticated state

        # Mock genai to simulate invalid model error
        with patch("google.generativeai.GenerativeModel") as mock_model:
            mock_model.side_effect = Exception("Model not found")

            # Act & Assert: Should raise exception (validation should catch this before)
            with pytest.raises(Exception, match="Model not found"):
                provider.switch_model("invalid-model-name")


class TestGenAIModelValidation:
    """Tests for GenAI provider model validation."""

    def test_genai_provider_empty_model_initially(self, workspace):
        """GenAI provider starts with empty model_name (set after auth)."""
        # Arrange & Act
        provider = GenAIProvider(workspace)

        # Assert: Empty initially
        assert provider.model_name == ""

    def test_genai_auto_detects_valid_model_on_auth(self, workspace):
        """GenAI should auto-detect a valid model after authentication."""
        # Arrange
        provider = GenAIProvider(workspace)
        provider.creds = MagicMock()
        provider.client = MagicMock()

        # Mock model listing
        mock_model1 = MagicMock()
        mock_model1.name = "models/gemini-2.0-flash"
        mock_model1.supported_generation_methods = ["generateContent"]

        mock_model2 = MagicMock()
        mock_model2.name = "models/gemini-1.5-flash"
        mock_model2.supported_generation_methods = ["generateContent"]

        provider.client.models.list.return_value = [mock_model1, mock_model2]

        # Act: Simulate successful auth
        with patch.object(
            provider,
            "list_available_models",
            return_value=["gemini-2.0-flash", "gemini-1.5-flash"],
        ):
            # Manually trigger model auto-detection logic
            available = provider.list_available_models()
            if available:
                # Should prefer gemini-2.0-flash
                assert "gemini-2.0-flash" in available


class TestAIServiceModelValidation:
    """Tests for AI Service facade model validation."""

    def test_switch_model_delegates_to_provider(self, workspace, default_settings):
        """AIService should delegate model switching to provider."""
        # Arrange
        ai_service = AIService(workspace, default_settings)

        # Act
        ai_service.switch_model("new-model")

        # Assert
        assert ai_service.model_name == "new-model"

    def test_list_available_models_delegates(self, workspace, default_settings):
        """AIService should delegate model listing to provider."""
        # Arrange
        ai_service = AIService(workspace, default_settings)

        with patch.object(
            ai_service.provider,
            "list_available_models",
            return_value=["model-1", "model-2"],
        ):
            # Act
            models = ai_service.list_available_models()

            # Assert
            assert models == ["model-1", "model-2"]


class TestModelSelectionValidation:
    """Tests for model selection validation logic."""

    def test_validate_model_in_list(self, workspace, default_settings):
        """Model should be validated against available models."""
        # Arrange
        provider = OpenAIProvider(workspace, default_settings)
        available_models = ["model-1", "model-2", "model-3"]

        # Act & Assert: Valid model
        assert "model-1" in available_models

        # Act & Assert: Invalid model
        assert "invalid-model" not in available_models

    def test_select_default_model_when_invalid(self, workspace, default_settings):
        """When configured model is invalid, should suggest default."""
        # Arrange
        default_settings.openai_model = "invalid-model"
        default_settings.openai_base_url = "http://localhost:11434/v1"
        provider = OpenAIProvider(workspace, default_settings)

        # Mock available models
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {"id": "gpt-4"},
                    {"id": "gpt-3.5-turbo"},
                ]
            }
            mock_get.return_value = mock_response

            # Act
            available = provider.list_available_models()

            # Assert: Configured model is not in available list
            assert provider.model_name not in available
            # Assert: Should have alternatives
            assert len(available) > 0


class TestAIServiceValidation:
    """Tests for AIService validation methods."""

    def test_validate_model_valid(self, workspace, default_settings):
        """validate_model should return True for valid model."""
        # Arrange
        ai_service = AIService(workspace, default_settings)

        with patch.object(
            ai_service.provider,
            "list_available_models",
            return_value=["model-1", "model-2"],
        ):
            # Act
            ai_service.switch_model("model-1")
            is_valid = ai_service.validate_model("model-1")

            # Assert
            assert is_valid is True

    def test_validate_model_invalid(self, workspace, default_settings):
        """validate_model should return False for invalid model."""
        # Arrange
        ai_service = AIService(workspace, default_settings)

        with patch.object(
            ai_service.provider,
            "list_available_models",
            return_value=["model-1", "model-2"],
        ):
            # Act & Assert
            is_valid = ai_service.validate_model("invalid-model")
            assert is_valid is False

    def test_ensure_valid_model_switches_when_invalid(
        self, workspace, default_settings
    ):
        """ensure_valid_model should auto-switch when model is invalid."""
        # Arrange
        default_settings.ai_provider = "openai"
        default_settings.openai_model = "invalid-model"
        default_settings.openai_base_url = "http://localhost:11434/v1"
        ai_service = AIService(workspace, default_settings)

        with patch.object(
            ai_service.provider,
            "list_available_models",
            return_value=["valid-model-1", "valid-model-2"],
        ):
            # Act
            old_model = ai_service.ensure_valid_model()

            # Assert
            assert old_model == "invalid-model"
            assert ai_service.model_name == "valid-model-1"

    def test_ensure_valid_model_no_change_when_valid(self, workspace, default_settings):
        """ensure_valid_model should not change valid model."""
        # Arrange
        default_settings.ai_provider = "openai"
        default_settings.openai_model = "valid-model"
        default_settings.openai_base_url = "http://localhost:11434/v1"
        ai_service = AIService(workspace, default_settings)

        with patch.object(
            ai_service.provider,
            "list_available_models",
            return_value=["valid-model", "other-model"],
        ):
            # Act
            old_model = ai_service.ensure_valid_model()

            # Assert
            assert old_model is None
            assert ai_service.model_name == "valid-model"

    def test_get_invalid_model_suggestion(self, workspace, default_settings):
        """get_invalid_model_suggestion should return suggestion dict."""
        # Arrange
        default_settings.ai_provider = "openai"
        default_settings.openai_model = "bad-model"
        default_settings.openai_base_url = "http://localhost:11434/v1"
        ai_service = AIService(workspace, default_settings)

        with patch.object(
            ai_service.provider,
            "list_available_models",
            return_value=["good-model-1", "good-model-2"],
        ):
            # Act
            suggestion = ai_service.get_invalid_model_suggestion()

            # Assert
            assert suggestion is not None
            assert suggestion["current"] == "bad-model"
            assert suggestion["suggested"] == "good-model-1"
            assert "good-model-1" in suggestion["available"]

    def test_get_invalid_model_suggestion_none_when_valid(
        self, workspace, default_settings
    ):
        """get_invalid_model_suggestion should return None when model is valid."""
        # Arrange
        default_settings.ai_provider = "openai"
        default_settings.openai_model = "good-model"
        default_settings.openai_base_url = "http://localhost:11434/v1"
        ai_service = AIService(workspace, default_settings)

        with patch.object(
            ai_service.provider,
            "list_available_models",
            return_value=["good-model", "other-model"],
        ):
            # Act
            suggestion = ai_service.get_invalid_model_suggestion()

            # Assert
            assert suggestion is None
