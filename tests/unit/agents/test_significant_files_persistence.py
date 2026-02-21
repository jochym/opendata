"""Tests for persistence of significant files during AI analysis."""

import pytest
from unittest.mock import MagicMock
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.workspace import WorkspaceManager
from opendata.models import ProjectFingerprint, AIAnalysis, FileSuggestion


@pytest.fixture
def agent(tmp_path):
    wm = WorkspaceManager(base_path=tmp_path)
    agent = ProjectAnalysisAgent(wm=wm)
    return agent


class TestSignificantFilesPersistence:
    """Verify that significant files are NOT cleared during AI analysis."""

    def test_analysis_preserves_significant_files(self, agent, tmp_path):
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "paper.tex").write_text("content")

        agent.load_project(project_dir)
        agent.refresh_inventory(project_dir)

        # Add significant file
        agent.add_significant_file("paper.tex", "main_article")
        assert len(agent.current_analysis.file_suggestions) == 1
        assert "paper.tex" in agent.current_fingerprint.significant_files

        # Act: Simulate AI Analysis
        mock_ai = MagicMock()
        # Mocking the AI response to return some metadata but NOT clearing suggestions
        mock_ai.ask_agent.return_value = (
            '{"title": "Test Project", "abstract": "Summary"}'
        )

        agent.run_ai_analysis_phase(mock_ai)

        # Assert: Suggestions should still be there!
        assert len(agent.current_analysis.file_suggestions) == 1, (
            "Significant files were cleared after analysis!"
        )
        assert agent.current_analysis.file_suggestions[0].path == "paper.tex"
        assert "paper.tex" in agent.current_fingerprint.significant_files
