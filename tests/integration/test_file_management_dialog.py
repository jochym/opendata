"""Integration tests for File Management Dialog component."""

import pytest
from pathlib import Path
from opendata.workspace import WorkspaceManager
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.models import ProjectFingerprint, AIAnalysis, FileSuggestion


@pytest.fixture
def test_project(tmp_path):
    """Create a test project with sample files."""
    # Create project structure
    (tmp_path / "paper.tex").write_text(
        r"""\documentclass{article}
\title{Test Paper}
\author{John Doe}
\begin{document}
\maketitle
\begin{abstract}
This is a test abstract.
\end{abstract}
\end{document}
"""
    )
    (tmp_path / "data.csv").write_text("x,y\n1,2\n3,4\n")
    (tmp_path / "script.py").write_text("print('hello')")
    (tmp_path / "README.md").write_text("# Test Project")

    return tmp_path


class TestFileManagementDialogIntegration:
    """Integration tests for file management workflow."""

    def test_initial_state_no_files_selected(self, test_project):
        """Initial state should have no files selected."""
        # Arrange
        wm = WorkspaceManager(base_path=test_project)
        agent = ProjectAnalysisAgent(wm=wm)

        # Setup fingerprint
        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(test_project),
            file_count=4,
            total_size_bytes=1000,
            extensions=[".tex", ".csv", ".py", ".md"],
            structure_sample=["paper.tex", "data.csv", "script.py", "README.md"],
            significant_files=[],
            primary_file=None,
        )
        agent.current_analysis = AIAnalysis(summary="Test")
        agent.current_analysis.file_suggestions = []

        # Assert
        assert len(agent.current_analysis.file_suggestions) == 0
        assert agent.heuristics_run is False

    def test_add_multiple_files_different_roles(self, test_project):
        """Should be able to add multiple files with different roles."""
        # Arrange
        wm = WorkspaceManager(base_path=test_project)
        agent = ProjectAnalysisAgent(wm=wm)

        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(test_project),
            file_count=4,
            total_size_bytes=1000,
            extensions=[".tex", ".csv", ".py", ".md"],
            structure_sample=["paper.tex", "data.csv", "script.py", "README.md"],
            significant_files=[],
            primary_file=None,
        )
        agent.current_analysis = AIAnalysis(summary="Test")
        agent.current_analysis.file_suggestions = []

        # Act: Add files with different roles
        agent.add_significant_file("paper.tex", "main_article")
        agent.add_significant_file("data.csv", "data_files")
        agent.add_significant_file("script.py", "visualization_scripts")

        # Assert
        assert len(agent.current_analysis.file_suggestions) == 3

        roles = {fs.path: fs.reason for fs in agent.current_analysis.file_suggestions}
        assert "paper.tex" in roles
        assert "data.csv" in roles
        assert "script.py" in roles

        # Check roles are assigned
        assert "Main article" in roles["paper.tex"]
        assert "Data" in roles["data.csv"]
        assert "Visualization" in roles["script.py"]

    def test_update_file_role_preserves_path(self, test_project):
        """Updating file role should preserve the file path."""
        # Arrange
        wm = WorkspaceManager(base_path=test_project)
        agent = ProjectAnalysisAgent(wm=wm)

        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(test_project),
            file_count=4,
            total_size_bytes=1000,
            extensions=[".tex", ".csv"],
            structure_sample=["paper.tex", "data.csv"],
            significant_files=[],
            primary_file=None,
        )
        agent.current_analysis = AIAnalysis(summary="Test")
        agent.add_significant_file("paper.tex", "other")

        # Act: Update role
        agent.update_file_role("paper.tex", "main_article")

        # Assert: Path preserved, role changed
        assert len(agent.current_analysis.file_suggestions) == 1
        suggestion = agent.current_analysis.file_suggestions[0]
        assert suggestion.path == "paper.tex"
        assert (
            "Main article" in suggestion.reason
            or "article" in suggestion.reason.lower()
        )

    def test_remove_file_clears_from_suggestions(self, test_project):
        """Removing a file should clear it from suggestions."""
        # Arrange
        wm = WorkspaceManager(base_path=test_project)
        agent = ProjectAnalysisAgent(wm=wm)

        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(test_project),
            file_count=4,
            total_size_bytes=1000,
            extensions=[".tex", ".csv"],
            structure_sample=["paper.tex", "data.csv"],
            significant_files=[],
            primary_file=None,
        )
        agent.current_analysis = AIAnalysis(summary="Test")
        agent.add_significant_file("paper.tex", "main_article")
        agent.add_significant_file("data.csv", "data_files")

        # Act: Remove one file
        agent.remove_significant_file("paper.tex")

        # Assert
        assert len(agent.current_analysis.file_suggestions) == 1
        assert agent.current_analysis.file_suggestions[0].path == "data.csv"
        assert "paper.tex" not in agent.current_fingerprint.significant_files

    def test_stats_calculation_accurate(self, test_project):
        """Stats should accurately reflect selected files."""
        # Arrange
        wm = WorkspaceManager(base_path=test_project)
        agent = ProjectAnalysisAgent(wm=wm)

        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(test_project),
            file_count=4,
            total_size_bytes=1000,
            extensions=[".tex", ".csv"],
            structure_sample=["paper.tex", "data.csv"],
            significant_files=[],
            primary_file=None,
        )
        agent.current_analysis = AIAnalysis(summary="Test")
        agent.add_significant_file("paper.tex", "main_article")
        agent.add_significant_file("data.csv", "data_files")

        # Act: Calculate stats
        project_dir = Path(agent.current_fingerprint.root_path)
        total_size = 0
        for fs in agent.current_analysis.file_suggestions:
            p = project_dir / fs.path
            if p.exists():
                total_size += p.stat().st_size

        # Assert
        expected_size = (test_project / "paper.tex").stat().st_size + (
            test_project / "data.csv"
        ).stat().st_size
        assert total_size == expected_size

    def test_heuristics_flag_tracks_selection_state(self, test_project):
        """heuristics_run flag should track whether files are selected."""
        # Arrange
        wm = WorkspaceManager(base_path=test_project)
        agent = ProjectAnalysisAgent(wm=wm)

        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(test_project),
            file_count=4,
            total_size_bytes=1000,
            extensions=[".tex"],
            structure_sample=["paper.tex"],
            significant_files=[],
            primary_file=None,
        )
        agent.current_analysis = AIAnalysis(summary="Test")
        agent.current_analysis.file_suggestions = []
        agent.heuristics_run = False

        # Act & Assert: Flag updates with selection
        assert agent.heuristics_run is False

        agent.add_significant_file("paper.tex", "main_article")
        assert agent.heuristics_run is True

        agent.remove_significant_file("paper.tex")
        assert agent.heuristics_run is False
