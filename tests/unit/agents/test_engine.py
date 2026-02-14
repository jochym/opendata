import pytest
from unittest.mock import MagicMock
from opendata.agents.engine import AnalysisEngine
from opendata.utils import PromptManager
from opendata.models import Metadata, ProjectFingerprint


@pytest.fixture
def engine():
    return AnalysisEngine(PromptManager())


def test_generate_ai_prompt_structure(engine):
    """Test that the prompt generator includes all necessary context."""
    metadata = Metadata(title="Test Title")
    fingerprint = ProjectFingerprint(
        root_path="/tmp",
        file_count=5,
        total_size_bytes=100,
        extensions=[".txt"],
        structure_sample=["a.txt"],
        primary_file="paper.tex",
    )
    protocol = {
        "prompts": ["Global Rule 1"],
        "metadata_prompts": ["Metadata Rule 1"],
        "curator_prompts": ["Curator Rule 1"],
    }

    # Test Metadata Mode
    prompt = engine.generate_ai_prompt("metadata", metadata, fingerprint, protocol)

    assert "Test Title" in prompt
    assert "paper.tex" in prompt
    assert "Global Rule 1" in prompt
    assert "Metadata Rule 1" in prompt
    assert "Curator Rule 1" not in prompt  # Should not be in metadata mode

    # Test Curator Mode
    prompt_curator = engine.generate_ai_prompt(
        "curator", metadata, fingerprint, protocol
    )
    assert "Curator Rule 1" in prompt_curator
    assert "Metadata Rule 1" not in prompt_curator
