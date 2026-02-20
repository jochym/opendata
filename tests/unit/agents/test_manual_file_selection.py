"""Tests for manual file selection feature replacing AI heuristics."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
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


class TestManualFileSelection:
    """Test manual file selection workflow."""

    def test_user_can_select_significant_files_with_categories(
        self, agent, temp_project_dir
    ):
        """User can manually select significant files and assign categories."""
        # Arrange: Create test files
        (temp_project_dir / "paper.tex").write_text("\\documentclass{article}")
        (temp_project_dir / "data.csv").write_text("x,y\n1,2")
        (temp_project_dir / "plot.py").write_text("import matplotlib")

        agent.load_project(temp_project_dir)
        agent.refresh_inventory(temp_project_dir)

        # Act: User manually selects files with categories
        selections = [
            {"path": "paper.tex", "category": "main_article"},
            {"path": "plot.py", "category": "visualization_scripts"},
            {"path": "data.csv", "category": "data_files"},
        ]
        agent.set_significant_files_manual(selections)

        # Assert: Files are stored in fingerprint
        assert agent.current_fingerprint is not None
        assert len(agent.current_fingerprint.significant_files) == 3
        assert "paper.tex" in agent.current_fingerprint.significant_files
        assert "plot.py" in agent.current_fingerprint.significant_files
        assert "data.csv" in agent.current_fingerprint.significant_files

    def test_manual_selection_sets_primary_file_automatically(
        self, agent, temp_project_dir
    ):
        """Selecting a .tex or .docx file automatically sets it as primary."""
        # Arrange
        (temp_project_dir / "thesis.docx").write_bytes(b"")
        (temp_project_dir / "notes.txt").write_text("notes")

        agent.load_project(temp_project_dir)
        agent.refresh_inventory(temp_project_dir)

        # Act: Select docx as main article
        selections = [
            {"path": "thesis.docx", "category": "main_article"},
            {"path": "notes.txt", "category": "documentation"},
        ]
        agent.set_significant_files_manual(selections)

        # Assert: Primary file is set to the article
        assert agent.current_fingerprint.primary_file == "thesis.docx"

    def test_manual_selection_overwrites_ai_heuristics(self, agent, temp_project_dir):
        """Manual selection replaces any previous AI heuristics results."""
        # Arrange: Simulate AI heuristics already ran
        (temp_project_dir / "ai_chosen.tex").write_text("\\documentclass{}")
        (temp_project_dir / "user_chosen.tex").write_text("\\documentclass{}")

        agent.load_project(temp_project_dir)
        agent.refresh_inventory(temp_project_dir)

        # Simulate AI already selected files
        agent.current_fingerprint.significant_files = ["ai_chosen.tex"]
        agent.heuristics_run = True

        # Act: User makes different selection
        selections = [
            {"path": "user_chosen.tex", "category": "main_article"},
        ]
        agent.set_significant_files_manual(selections)

        # Assert: AI choice is replaced
        assert "ai_chosen.tex" not in agent.current_fingerprint.significant_files
        assert "user_chosen.tex" in agent.current_fingerprint.significant_files
        assert agent.current_fingerprint.primary_file == "user_chosen.tex"

    def test_file_categories_are_stored_in_analysis(self, agent, temp_project_dir):
        """File categories are preserved in current_analysis for context injection."""
        # Arrange
        (temp_project_dir / "script.py").write_text("print('hello')")

        agent.load_project(temp_project_dir)
        agent.refresh_inventory(temp_project_dir)

        # Act
        selections = [
            {"path": "script.py", "category": "visualization_scripts"},
        ]
        agent.set_significant_files_manual(selections)

        # Assert: Category is stored
        assert agent.current_analysis is not None
        file_suggestions = agent.current_analysis.file_suggestions
        assert len(file_suggestions) == 1
        assert file_suggestions[0].path == "script.py"
        assert "visualization" in file_suggestions[0].reason.lower()

    def test_empty_selection_clears_significant_files(self, agent, temp_project_dir):
        """Empty selection clears previously selected significant files."""
        # Arrange
        (temp_project_dir / "file.tex").write_text("\\documentclass{}")

        agent.load_project(temp_project_dir)
        agent.refresh_inventory(temp_project_dir)
        agent.current_fingerprint.significant_files = ["file.tex"]

        # Act: User clears selection
        agent.set_significant_files_manual([])

        # Assert
        assert agent.current_fingerprint.significant_files == []

    def test_invalid_path_ignored_in_selection(self, agent, temp_project_dir):
        """Paths that don't exist in inventory are silently ignored."""
        # Arrange
        (temp_project_dir / "real.tex").write_text("\\documentclass{}")

        agent.load_project(temp_project_dir)
        agent.refresh_inventory(temp_project_dir)

        # Act: Include non-existent file
        selections = [
            {"path": "real.tex", "category": "main_article"},
            {"path": "does_not_exist.tex", "category": "main_article"},
        ]
        agent.set_significant_files_manual(selections)

        # Assert: Only valid file is selected
        assert len(agent.current_fingerprint.significant_files) == 1
        assert "real.tex" in agent.current_fingerprint.significant_files
        assert "does_not_exist.tex" not in agent.current_fingerprint.significant_files

    def test_heuristics_run_flag_set_after_manual_selection(
        self, agent, temp_project_dir
    ):
        """Manual selection sets heuristics_run flag to enable AI Analyze button."""
        # Arrange
        (temp_project_dir / "paper.tex").write_text("\\documentclass{}")

        agent.load_project(temp_project_dir)
        agent.refresh_inventory(temp_project_dir)
        agent.heuristics_run = False

        # Act
        selections = [{"path": "paper.tex", "category": "main_article"}]
        agent.set_significant_files_manual(selections)

        # Assert: Flag is set
        assert agent.heuristics_run is True

    def test_chat_message_added_after_manual_selection(self, agent, temp_project_dir):
        """Manual selection adds confirmation message to chat history."""
        # Arrange
        (temp_project_dir / "main.tex").write_text("\\documentclass{}")

        agent.load_project(temp_project_dir)
        agent.refresh_inventory(temp_project_dir)
        initial_history_len = len(agent.chat_history)

        # Act
        selections = [{"path": "main.tex", "category": "main_article"}]
        agent.set_significant_files_manual(selections)

        # Assert: Chat message added
        assert len(agent.chat_history) > initial_history_len
        last_role, last_msg = agent.chat_history[-1]
        assert last_role == "agent"
        assert "main.tex" in last_msg
        assert "manual file selection" in last_msg.lower()
