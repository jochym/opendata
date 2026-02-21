import pytest
from pathlib import Path
from unittest.mock import MagicMock
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.models import Metadata, ProjectFingerprint, AIAnalysis
from opendata.workspace import WorkspaceManager


@pytest.fixture
def agent(tmp_path):
    wm = WorkspaceManager(base_path=tmp_path)
    agent = ProjectAnalysisAgent(wm=wm)
    # Setup dummy fingerprint
    agent.current_fingerprint = ProjectFingerprint(
        root_path=str(tmp_path),
        file_count=10,
        total_size_bytes=1000,
        extensions=[".txt", ".py"],
        structure_sample=["foo.txt", "src/bar.py"],
        primary_file=None,
        significant_files=[],
    )
    # Create dummy files
    (tmp_path / "foo.txt").write_text("content of foo")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/bar.py").write_text("content of bar")
    return agent


def test_process_user_input_file_patterns(agent):
    """Test @file pattern extraction - simple patterns should work."""

    # Mock engine to capture input
    agent.engine = MagicMock()
    agent.engine.run_ai_loop.return_value = ("Response", None, Metadata())

    # Test single file (should definitely work)
    user_text = "Check this file @foo.txt"

    agent.process_user_input(user_text, ai_service=MagicMock())

    # Check if run_ai_loop was called with enhanced input containing file content
    call_args = agent.engine.run_ai_loop.call_args
    enhanced_input = call_args.kwargs["user_input"]

    # Verify file content is injected for single files
    assert "content of foo" in enhanced_input
    assert "[CONTEXT FROM ATTACHED FILES]" in enhanced_input
    assert "foo.txt" in enhanced_input

    # Note: Pattern matching (@*.py) should be documented but may have limitations
    # Simple patterns like @*.txt or @file.* should work if implemented


def test_curator_mode_filtering(agent):
    """Test that curator mode only allows specific fields to be updated."""

    agent.current_metadata = Metadata(title="Original Title", notes="Old notes")

    # Mock engine to return a full metadata update
    agent.engine = MagicMock()
    new_metadata = Metadata(
        title="Hacked Title",  # Should be ignored in curator mode
        kind_of_data="Experimental",  # Allowed
        description=["New description"],  # Should be appended to notes
    )
    agent.engine.run_ai_loop.return_value = ("Response", None, new_metadata)

    # Debug print to verify model_dump behavior
    # print(f"New metadata dump: {new_metadata.model_dump()}")

    agent.process_user_input("Update this", ai_service=MagicMock(), mode="curator")

    assert agent.current_metadata.title == "Original Title"

    # Note: kind_of_data has validation_alias="kindof_data" in the model.
    # The agent logic uses model_dump() which uses field names by default.
    # If this assertion fails, it might be because the field wasn't copied correctly.
    assert agent.current_metadata.kind_of_data == "Experimental"

    assert "New description" in agent.current_metadata.notes
    assert "[Curator Description]" in agent.current_metadata.notes


def test_submit_analysis_answers_validation(agent):
    """Test that form submission doesn't overwrite complex objects with strings."""

    agent.current_metadata = Metadata()
    agent.current_analysis = AIAnalysis(summary="Test")

    # Form submission with string value for 'authors' (complex field)
    answers = {"authors": "Some String Author", "keywords": "physics"}

    agent.submit_analysis_answers(answers)

    # Authors should remain empty (protected from string overwrite)
    assert agent.current_metadata.authors == []

    # Keywords should be converted to list
    assert agent.current_metadata.keywords == ["physics"]
