"""Tests for manual file selection feature with incremental updates."""

import pytest
from pathlib import Path
from opendata.models import FileSuggestion, ProjectFingerprint
from opendata.workspace import WorkspaceManager
from opendata.agents.project_agent import ProjectAnalysisAgent


@pytest.fixture
def agent(tmp_path):
    """Create a test agent with initialized workspace."""
    wm = WorkspaceManager(base_path=tmp_path)
    agent = ProjectAnalysisAgent(wm=wm)
    return agent


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with basic structure."""
    project = tmp_path / "test_project"
    project.mkdir()
    return project


class TestManualFileSelectionIncremental:
    """Test manual file selection workflow with incremental updates."""

    def test_add_significant_file(self, agent, temp_project_dir):
        """User can add a file to significant files list."""
        (temp_project_dir / "paper.tex").write_text("\\documentclass{article}")
        agent.load_project(temp_project_dir)
        agent.refresh_inventory(temp_project_dir)

        # Act
        agent.add_significant_file("paper.tex", "main_article")

        # Assert
        assert "paper.tex" in agent.current_fingerprint.significant_files
        assert agent.current_analysis.file_suggestions[0].path == "paper.tex"
        assert "Main article" in agent.current_analysis.file_suggestions[0].reason

    def test_remove_significant_file(self, agent, temp_project_dir):
        """User can remove a file from significant files list."""
        (temp_project_dir / "paper.tex").write_text("...")
        agent.load_project(temp_project_dir)
        agent.refresh_inventory(temp_project_dir)
        agent.add_significant_file("paper.tex", "main_article")

        # Act
        agent.remove_significant_file("paper.tex")

        # Assert
        assert "paper.tex" not in agent.current_fingerprint.significant_files
        assert len(agent.current_analysis.file_suggestions) == 0

    def test_update_file_role(self, agent, temp_project_dir):
        """User can update the role of an already selected file."""
        (temp_project_dir / "data.csv").write_text("...")
        agent.load_project(temp_project_dir)
        agent.refresh_inventory(temp_project_dir)
        agent.add_significant_file("data.csv", "other")

        # Act
        agent.update_file_role("data.csv", "data_files")

        # Assert
        assert "data.csv" in agent.current_fingerprint.significant_files
        assert "Data files" in agent.current_analysis.file_suggestions[0].reason

    def test_primary_file_auto_detection_on_add(self, agent, temp_project_dir):
        """Adding a .tex file as main_article sets it as primary."""
        (temp_project_dir / "thesis.tex").write_text("...")
        agent.load_project(temp_project_dir)
        agent.refresh_inventory(temp_project_dir)

        # Act
        agent.add_significant_file("thesis.tex", "main_article")

        # Assert
        assert agent.current_fingerprint.primary_file == "thesis.tex"

    def test_heuristics_run_flag_logic(self, agent, temp_project_dir):
        """Flag is True if list is not empty, False if empty."""
        (temp_project_dir / "file.txt").write_text("...")
        agent.load_project(temp_project_dir)
        agent.refresh_inventory(temp_project_dir)

        assert agent.heuristics_run is False

        agent.add_significant_file("file.txt", "other")
        assert agent.heuristics_run is True

        agent.remove_significant_file("file.txt")
        assert agent.heuristics_run is False
