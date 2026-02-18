import json
import pytest
from pathlib import Path
from opendata.ai.telemetry import AITelemetry


@pytest.fixture
def telemetry(tmp_path):
    log_file = tmp_path / "ai_interactions.jsonl"
    return AITelemetry(log_file)


def test_generate_id(telemetry):
    id1 = telemetry.generate_id()
    id2 = telemetry.generate_id()
    assert id1 != id2
    assert len(id1) > 0


def test_sanitize_prompt_no_truncation(telemetry):
    prompt = "--- FILE CONTENT: test.txt ---\nShort content\n---"
    sanitized = telemetry.sanitize_prompt(prompt)
    assert sanitized == prompt


def test_sanitize_prompt_with_truncation(telemetry):
    large_content = "A" * 1000
    prompt = f"--- FILE CONTENT: test.txt ---\n{large_content}\n---"
    sanitized = telemetry.sanitize_prompt(prompt)
    assert "truncated" in sanitized
    assert "1000 chars" in sanitized
    assert "Short content" not in sanitized


def test_sanitize_prompt_end_truncation(telemetry):
    large_content = "B" * 600
    prompt = f"Please analyze this:\n--- FILE CONTENT: data.csv ---\n{large_content}"
    sanitized = telemetry.sanitize_prompt(prompt)
    assert "truncated" in sanitized
    assert "600 chars" in sanitized


def test_log_interaction(telemetry, tmp_path):
    interaction_id = "test-id"
    telemetry.log_interaction(
        interaction_id=interaction_id,
        model_name="test-model",
        prompt="Hello",
        response="Hi there",
        latency_ms=100.5,
    )

    assert telemetry.log_path.exists()
    with open(telemetry.log_path, "r") as f:
        line = f.readline()
        data = json.loads(line)
        assert data["id"] == interaction_id
        assert data["model"] == "test-model"
        assert data["prompt"] == "Hello"
        assert data["response"] == "Hi there"
        assert data["latency_ms"] == 100.5


def test_id_tag_injection_and_extraction():
    interaction_id = "unique-id-123"
    tag = AITelemetry.get_id_tag(interaction_id)
    assert "unique-id-123" in tag

    response = "This is the AI response." + tag
    extracted = AITelemetry.extract_id(response)
    assert extracted == interaction_id

    stripped = AITelemetry.strip_id_tag(response)
    assert stripped == "This is the AI response."
