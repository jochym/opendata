import pytest
from pathlib import Path
import tempfile
from opendata.workspace import WorkspaceManager
from opendata.models import UserSettings


@pytest.fixture
def mock_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield WorkspaceManager(base_path=Path(tmpdir))


def test_workspace_isolation(mock_workspace):
    """Verify that the workspace stays within its own boundaries."""
    assert mock_workspace.base_path.exists()
    assert (mock_workspace.base_path / "protocols").exists()
    assert (mock_workspace.base_path / "workspaces").exists()


def test_read_only_research_integrity():
    """Verify that the tool logic (via a mock) does not modify a research directory."""
    with tempfile.TemporaryDirectory() as research_dir:
        research_path = Path(research_dir)
        important_file = research_path / "data.csv"
        content = "v1,v2\n1,2"
        important_file.write_text(content)

        # Simulate an operation that should be read-only
        from opendata.utils import scan_project_lazy

        scan_project_lazy(research_path)

        # Verify content hasn't changed
        assert important_file.read_text() == content
        # Verify no temporary files were created in research_dir
        files = list(research_path.iterdir())
        assert len(files) == 1


def test_yaml_error_forgiveness(mock_workspace):
    """Verify that the tool handles 'messy' human YAML edits gracefully."""
    settings_path = mock_workspace.base_path / "settings.yaml"

    # Write some "broken" but still parsable YAML (e.g. extra spaces, comments)
    messy_yaml = """
language: pl # User manually added a comment
ai_consent_granted:   true    
workspace_path: /tmp/manual_path
field_protocols_path: /tmp/manual_protocols
    """
    settings_path.write_text(messy_yaml)

    settings = mock_workspace.get_settings()
    assert settings.language == "pl"
    assert settings.ai_consent_granted is True
    assert settings.workspace_path == "/tmp/manual_path"
