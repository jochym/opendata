"""
Unit Tests for GenAI Provider

⚠️  AI INTERACTION TEST - LOCAL EXECUTION ONLY

These tests make real AI API calls and should:
- Run LOCALLY only (NOT in CI/CD/GitHub Actions)
- Use OpenAI interface for better quotas
- Requires valid authentication tokens

To run:
    pytest tests/unit/ai/test_genai_provider.py -v

To skip AI tests:
    pytest -m "not ai_interaction" -v
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from opendata.ai.genai_provider import GenAIProvider
from opendata.ai.telemetry import AITelemetry
from opendata.agents.parsing import extract_metadata_from_ai_response
from opendata.models import Metadata

# Mark all tests in this file as AI interaction tests
pytestmark = pytest.mark.ai_interaction


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


@pytest.fixture
def provider(workspace):
    return GenAIProvider(workspace)


def test_genai_provider_ask_agent_logging(provider, workspace):
    # Mock the google-genai client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"METADATA": {"title": "Test"}}'
    mock_client.models.generate_content.return_value = mock_response

    provider.client = mock_client

    # Execute
    response = provider.ask_agent("Test prompt")

    # Verify ID injection
    interaction_id = AITelemetry.extract_id(response)
    assert interaction_id is not None

    # Verify telemetry log file exists and contains the interaction
    log_file = workspace / "logs" / "ai_interactions.jsonl"
    assert log_file.exists()

    log_content = log_file.read_text()
    assert interaction_id in log_content
    assert "Test prompt" in log_content
    # The response is JSON-encoded in the log, so quotes are escaped
    assert '{\\"METADATA\\": {\\"title\\": \\"Test\\"}}' in log_content


def test_parser_integration_with_telemetry_id():
    interaction_id = "test-uuid-123"
    ai_response = 'METADATA: {"title": "New Title"}' + AITelemetry.get_id_tag(
        interaction_id
    )

    current_metadata = Metadata(
        title="Old Title",
        kind_of_data="Experimental",
        license="CC-BY-4.0",
        ai_model="test-model",
        abstract="Test abstract",
        notes="Test notes",
    )

    # We want to capture logs to verify the ID is logged

    with patch("opendata.agents.parsing.logger") as mock_logger:
        clean_msg, analysis, updated_metadata = extract_metadata_from_ai_response(
            ai_response, current_metadata
        )

        # Verify logger was called with the ID
        mock_logger.info.assert_any_call(f"Processing AI Response ID: {interaction_id}")

        # Verify metadata was updated correctly
        assert updated_metadata.title == "New Title"
        # Verify the tag was stripped from the clean message if it was there
        assert interaction_id not in clean_msg


def test_genai_provider_list_models_fallback(provider):
    # Test fallback when client is not initialized
    models = provider.list_available_models()
    assert "gemini-2.0-flash" in models
    assert "gemini-1.5-pro" in models


@patch("opendata.ai.genai_provider.genai.Client")
def test_genai_provider_client_creation(mock_client_class, provider):
    provider.creds = MagicMock()
    provider.creds.token = "fake-token"

    client = provider._create_client()
    assert client is not None
    mock_client_class.assert_called_once()
    # Check if headers were passed
    args, kwargs = mock_client_class.call_args
    assert "http_options" in kwargs
    assert "Authorization" in kwargs["http_options"]["headers"]
    assert kwargs["http_options"]["headers"]["Authorization"] == "Bearer fake-token"
