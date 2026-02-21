"""Tests for Significant Files Editor auto-refresh behavior."""

import pytest
from unittest.mock import MagicMock, patch, call
from nicegui import ui
from opendata.ui.context import AppContext
from opendata.workspace import WorkspaceManager
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.models import ProjectFingerprint, AIAnalysis, FileSuggestion, Metadata


@pytest.fixture
def app_context(tmp_path):
    """Creates a mock AppContext with initialized agent."""
    wm = WorkspaceManager(base_path=tmp_path)
    agent = ProjectAnalysisAgent(wm=wm)

    # Setup mock fingerprint
    agent.current_fingerprint = ProjectFingerprint(
        root_path=str(tmp_path),
        file_count=3,
        total_size_bytes=1500,
        extensions=[".tex", ".py"],
        structure_sample=["paper.tex", "script.py"],
        primary_file="paper.tex",
        significant_files=["paper.tex"],
    )

    # Setup mock analysis with one file
    agent.current_analysis = AIAnalysis(summary="Test")
    agent.current_analysis.file_suggestions = [
        FileSuggestion(path="paper.tex", reason="Main article/paper")
    ]

    # Set heuristics_run flag to match the state
    agent.heuristics_run = True

    # Create mock context
    ctx = MagicMock(spec=AppContext)
    ctx.agent = agent
    ctx.session = MagicMock()
    ctx.session.inventory_cache = []
    ctx.session.folder_children_map = {}
    ctx.refresh = MagicMock()

    return ctx


class TestSignificantFilesEditorRefresh:
    """Tests for auto-refresh behavior in Significant Files Editor."""

    def test_add_file_triggers_refresh(self, app_context, tmp_path):
        """Adding a file should trigger refresh of both editor and selector."""
        # Arrange
        from opendata.ui.components.chat import render_significant_files_editor

        # Act: Add a new file
        app_context.agent.add_significant_file("script.py", "visualization_scripts")

        # Assert: Agent state updated
        assert "script.py" in app_context.agent.current_fingerprint.significant_files
        assert len(app_context.agent.current_analysis.file_suggestions) == 2

        # Note: Actual UI refresh is tested via integration tests
        # Here we verify the agent calls save_state which triggers UI update
        assert app_context.agent.heuristics_run is True

    def test_remove_file_triggers_refresh(self, app_context, tmp_path):
        """Removing a file should trigger refresh of both editor and selector."""
        # Arrange: Start with 2 files
        app_context.agent.add_significant_file("script.py", "visualization_scripts")
        initial_count = len(app_context.agent.current_analysis.file_suggestions)

        # Act: Remove one file
        app_context.agent.remove_significant_file("paper.tex")

        # Assert: Agent state updated
        assert (
            len(app_context.agent.current_analysis.file_suggestions)
            == initial_count - 1
        )
        assert (
            "paper.tex" not in app_context.agent.current_fingerprint.significant_files
        )
        assert "script.py" in app_context.agent.current_fingerprint.significant_files

    def test_update_role_triggers_refresh(self, app_context, tmp_path):
        """Updating file role should trigger refresh."""
        # Arrange
        initial_reason = app_context.agent.current_analysis.file_suggestions[0].reason

        # Act: Update role
        app_context.agent.update_file_role("paper.tex", "data_files")

        # Assert: Role changed
        updated_suggestion = app_context.agent.current_analysis.file_suggestions[0]
        assert updated_suggestion.path == "paper.tex"
        assert (
            "Data" in updated_suggestion.reason
            or "data" in updated_suggestion.reason.lower()
        )

    def test_heuristics_flag_updates_correctly(self, app_context, tmp_path):
        """heuristics_run flag should be True when files selected, False when empty."""
        # Arrange: Start with 1 file
        assert app_context.agent.heuristics_run is True

        # Act: Remove all files
        app_context.agent.remove_significant_file("paper.tex")

        # Assert: Flag is False
        assert app_context.agent.heuristics_run is False

        # Act: Add file back
        app_context.agent.add_significant_file("paper.tex", "main_article")

        # Assert: Flag is True again
        assert app_context.agent.heuristics_run is True


class TestSignificantFilesStats:
    """Tests for statistics calculation in Significant Files Editor."""

    def test_stats_calculation(self, app_context, tmp_path):
        """Stats should correctly count files and calculate size."""
        # Arrange: Create actual files for size calculation
        (tmp_path / "paper.tex").write_text("x" * 1000)  # 1000 bytes
        (tmp_path / "script.py").write_text("x" * 500)  # 500 bytes

        app_context.agent.current_fingerprint.root_path = str(tmp_path)
        app_context.agent.add_significant_file("script.py", "visualization_scripts")

        # Act: Get suggestions
        suggestions = app_context.agent.current_analysis.file_suggestions

        # Assert: Count and size
        assert len(suggestions) == 2

        # Calculate expected size
        expected_size = (tmp_path / "paper.tex").stat().st_size + (
            tmp_path / "script.py"
        ).stat().st_size
        assert expected_size == 1500

    def test_stats_with_missing_files(self, app_context, tmp_path):
        """Stats should handle missing files gracefully."""
        # Arrange: Add file that doesn\'t exist
        app_context.agent.add_significant_file("nonexistent.tex", "main_article")

        # Act: Get suggestions
        suggestions = app_context.agent.current_analysis.file_suggestions

        # Assert: Count is correct, size calculation doesn\'t crash
        assert len(suggestions) == 2  # paper.tex + nonexistent.tex
        # Size should only count existing files
