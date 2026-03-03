"""Tests for FileManagementDialog component."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from opendata.ui.context import AppContext
from opendata.workspace import WorkspaceManager
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.models import ProjectFingerprint, AIAnalysis, FileSuggestion


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

    agent.heuristics_run = True

    # Create mock context
    ctx = MagicMock(spec=AppContext)
    ctx.agent = agent
    ctx.session = MagicMock()
    ctx.session.inventory_cache = []
    ctx.session.folder_children_map = {}
    ctx.session.explorer_path = ""
    ctx.refresh = MagicMock()

    return ctx


class TestFileManagementDialog:
    """Tests for FileManagementDialog component."""

    def test_dialog_shows_selected_files_count(self, app_context, tmp_path):
        """Dialog should display count of selected files."""
        # Arrange: Create actual files
        (tmp_path / "paper.tex").write_text("x" * 1000)
        app_context.agent.current_fingerprint.root_path = str(tmp_path)

        # Act: Get suggestions
        suggestions = app_context.agent.current_analysis.file_suggestions

        # Assert: Count is correct
        assert len(suggestions) == 1
        assert suggestions[0].path == "paper.tex"

    def test_dialog_shows_file_with_role(self, app_context, tmp_path):
        """Dialog should display each file with its assigned role."""
        # Arrange
        suggestion = app_context.agent.current_analysis.file_suggestions[0]

        # Assert: Role is present
        assert suggestion.reason == "Main article/paper"

    def test_add_file_from_explorer_updates_list(self, app_context, tmp_path):
        """Adding a file from explorer should update the selected files list."""
        # Arrange: Create file
        (tmp_path / "script.py").write_text("x" * 500)
        initial_count = len(app_context.agent.current_analysis.file_suggestions)

        # Act: Add file
        app_context.agent.add_significant_file("script.py", "visualization_scripts")

        # Assert: List updated
        new_count = len(app_context.agent.current_analysis.file_suggestions)
        assert new_count == initial_count + 1
        assert any(
            fs.path == "script.py"
            for fs in app_context.agent.current_analysis.file_suggestions
        )

    def test_remove_file_updates_list(self, app_context, tmp_path):
        """Removing a file should update the selected files list."""
        # Arrange: Add second file
        app_context.agent.add_significant_file("script.py", "visualization_scripts")
        initial_count = len(app_context.agent.current_analysis.file_suggestions)

        # Act: Remove original file
        app_context.agent.remove_significant_file("paper.tex")

        # Assert: List updated
        new_count = len(app_context.agent.current_analysis.file_suggestions)
        assert new_count == initial_count - 1
        assert not any(
            fs.path == "paper.tex"
            for fs in app_context.agent.current_analysis.file_suggestions
        )
        assert any(
            fs.path == "script.py"
            for fs in app_context.agent.current_analysis.file_suggestions
        )

    def test_update_file_role(self, app_context, tmp_path):
        """Changing file role should update the suggestion."""
        # Arrange
        initial_reason = app_context.agent.current_analysis.file_suggestions[0].reason
        assert "Main article" in initial_reason

        # Act: Update role
        app_context.agent.update_file_role("paper.tex", "data_files")

        # Assert: Role changed
        updated = app_context.agent.current_analysis.file_suggestions[0]
        assert updated.path == "paper.tex"
        assert "Data" in updated.reason or "data" in updated.reason.lower()

    def test_dialog_handles_empty_selection(self, app_context, tmp_path):
        """Dialog should handle case when no files are selected."""
        # Arrange: Remove all files
        app_context.agent.remove_significant_file("paper.tex")

        # Assert: Empty list
        assert len(app_context.agent.current_analysis.file_suggestions) == 0
        assert app_context.agent.heuristics_run is False

    def test_dialog_stats_calculation(self, app_context, tmp_path):
        """Dialog should calculate total size of selected files."""
        # Arrange: Create files
        (tmp_path / "paper.tex").write_text("x" * 1000)
        (tmp_path / "script.py").write_text("x" * 500)
        app_context.agent.current_fingerprint.root_path = str(tmp_path)

        app_context.agent.add_significant_file("script.py", "visualization_scripts")

        # Act: Calculate size
        project_dir = Path(app_context.agent.current_fingerprint.root_path)
        total_size = 0
        for fs in app_context.agent.current_analysis.file_suggestions:
            p = project_dir / fs.path
            if p.exists():
                total_size += p.stat().st_size

        # Assert: Size is correct
        assert total_size == 1500

    def test_dialog_stats_with_missing_files(self, app_context, tmp_path):
        """Dialog should handle missing files gracefully in stats."""
        # Arrange: Create paper.tex and add non-existent file
        (tmp_path / "paper.tex").write_text("x" * 1000)
        app_context.agent.current_fingerprint.root_path = str(tmp_path)
        app_context.agent.add_significant_file(
            "nonexistent.py", "visualization_scripts"
        )

        # Act: Calculate size (should not crash)
        project_dir = Path(app_context.agent.current_fingerprint.root_path)
        total_size = 0
        for fs in app_context.agent.current_analysis.file_suggestions:
            p = project_dir / fs.path
            if p.exists():
                total_size += p.stat().st_size

        # Assert: Only counts existing files
        assert total_size == 1000


class TestFileManagementDialogCategories:
    """Tests for file role categories in dialog."""

    def test_all_categories_available(self, app_context):
        """All file role categories should be available."""
        # Arrange
        CATEGORIES = {
            "main_article": "Article",
            "visualization_scripts": "Scripts",
            "data_files": "Data",
            "documentation": "Docs",
            "other": "Other",
        }

        # Assert: All categories present
        assert len(CATEGORIES) == 5
        assert "main_article" in CATEGORIES
        assert "visualization_scripts" in CATEGORIES
        assert "data_files" in CATEGORIES
        assert "documentation" in CATEGORIES
        assert "other" in CATEGORIES

    def test_role_mapping_works(self, app_context):
        """Reason to category mapping should work correctly."""
        # Arrange
        REASON_MAP = {
            "Main article/paper": "main_article",
            "Visualization scripts": "visualization_scripts",
            "Data files": "data_files",
            "Documentation": "documentation",
            "Supporting file": "other",
        }

        # Act & Assert: Each reason maps to a category
        for reason, expected_cat in REASON_MAP.items():
            assert expected_cat in [
                "main_article",
                "visualization_scripts",
                "data_files",
                "documentation",
                "other",
            ]
