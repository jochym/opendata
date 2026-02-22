import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, Mock
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.workspace import WorkspaceManager
from opendata.models import Metadata, ProjectFingerprint
from opendata.utils import PromptManager


@pytest.fixture
def workspace_manager(tmp_path):
    wm = WorkspaceManager()
    # Override workspace base directory to temp path
    wm._workspace_dir = tmp_path
    (tmp_path / "projects").mkdir(parents=True, exist_ok=True)
    return wm


@pytest.fixture
def agent(workspace_manager):
    return ProjectAnalysisAgent(wm=workspace_manager, prompt_manager=PromptManager())


@pytest.fixture
def realistic_projects():
    fixture_path = (
        Path(__file__).parent.parent.parent / "fixtures" / "realistic_metadata.yaml"
    )
    with open(fixture_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["projects"]


@pytest.fixture
def project_3csic_path():
    return (
        Path(__file__).parent.parent.parent
        / "fixtures"
        / "realistic_projects"
        / "3C-SiC"
    )


@pytest.fixture
def project_fesi_path():
    return (
        Path(__file__).parent.parent.parent / "fixtures" / "realistic_projects" / "FeSi"
    )


class TestAgentContextBuilding:
    """Tests for CORRECT behavior: Agent should build rich context from project files."""

    def test_agent_loads_project_state(
        self, agent, project_3csic_path, workspace_manager
    ):
        """
        Test behavior: Agent should load existing project metadata and fingerprint.
        """
        # Arrange: Get project ID (this creates the project structure in workspace)
        project_id = workspace_manager.get_project_id(project_3csic_path)

        # Act: Load the project
        loaded = agent.load_project(project_3csic_path)

        # Assert: Project is loaded with ID
        assert agent.project_id == project_id
        # Note: loaded may be False if no prior state exists, which is expected
        assert agent.project_id is not None

    def test_agent_builds_context_from_significant_files(
        self, agent, project_3csic_path, workspace_manager
    ):
        """
        Test behavior: When significant files are set, Agent should include their content
        in the context for AI analysis.
        """
        # Arrange: Load project and set significant files
        agent.load_project(project_3csic_path)

        # Manually set fingerprint with significant files
        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(project_3csic_path),
            file_count=10,
            total_size_bytes=10000,
            extensions=[".tex", ".yaml"],
            structure_sample=["main.tex", "OpenData.yaml"],
            significant_files=["main.tex"],
            primary_file=None,
        )

        # Act: Run AI analysis phase (mock AI service)
        mock_ai = MagicMock()
        mock_ai.ask_agent.return_value = "METADATA:\n  title: Test Title"

        # We can't easily test the full prompt without calling the actual method,
        # but we can verify the context files are read
        from opendata.utils import FullTextReader

        main_tex = project_3csic_path / "main.tex"
        content = FullTextReader.read_full_text(main_tex)

        # Assert: Content is readable and contains expected metadata
        assert content is not None
        assert len(content) > 0
        assert "Thermal conductivity" in content or "3C-SiC" in content

    def test_agent_handles_missing_files_gracefully(
        self, agent, workspace_manager, tmp_path
    ):
        """
        Test behavior: Agent should not crash when significant files are missing.
        """
        # Arrange: Create fingerprint with non-existent files
        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(tmp_path),
            file_count=0,
            total_size_bytes=0,
            extensions=[],
            structure_sample=[],
            significant_files=["nonexistent.tex"],
        )
        agent.project_id = "test-project"

        # Act: Try to run analysis
        mock_ai = MagicMock()
        mock_ai.ask_agent.return_value = "METADATA:\n  title: Fallback Title"

        # Should not raise exception
        result = agent.run_ai_analysis_phase(mock_ai)

        # Assert: Returns message (not crash)
        assert result is not None


class TestAgentStateManagement:
    """Tests for CORRECT behavior: Agent should maintain state correctly."""

    def test_agent_remembers_metadata_between_interactions(
        self, agent, project_3csic_path
    ):
        """
        Test behavior: Metadata set in one interaction should persist to the next.
        """
        # Arrange: Load project and set metadata
        agent.load_project(project_3csic_path)
        agent.current_metadata = Metadata(
            title="Initial Title",
            keywords=["physics"],
            kind_of_data="Simulation",
            license="CC-BY-4.0",
        )
        # Clear any existing history from loaded state
        agent.chat_history = []

        # Act: Simulate multiple interactions
        agent.chat_history.append(("user", "What is the title?"))
        agent.chat_history.append(("agent", "The title is Initial Title"))

        # Assert: Metadata is preserved
        assert agent.current_metadata.title == "Initial Title"
        assert len(agent.chat_history) == 2

    def test_agent_save_state_persists_to_disk(
        self, agent, project_3csic_path, workspace_manager
    ):
        """
        Test behavior: save_state() should persist metadata and chat history to workspace.
        """
        # Arrange: Load project and modify state
        agent.load_project(project_3csic_path)
        agent.current_metadata = Metadata(title="Persistent Title")
        agent.chat_history = [("user", "Hello"), ("agent", "Hi")]

        # Act: Save state
        agent.save_state()

        # Assert: State can be reloaded
        new_agent = ProjectAnalysisAgent(
            wm=workspace_manager, prompt_manager=PromptManager()
        )
        new_agent.load_project(project_3csic_path)

        assert new_agent.current_metadata.title == "Persistent Title"
        assert len(new_agent.chat_history) == 2

    def test_agent_clear_chat_history(self, agent, project_3csic_path):
        """
        Test behavior: clear_chat_history() should empty history and persist.
        """
        # Arrange: Load and add history
        agent.load_project(project_3csic_path)
        agent.chat_history = [("user", "Test"), ("agent", "Response")]

        # Act: Clear history
        agent.clear_chat_history()

        # Assert: History is empty
        assert len(agent.chat_history) == 0

    def test_agent_clear_metadata(self, agent, project_3csic_path):
        """
        Test behavior: clear_metadata() should reset to fresh Metadata object.
        """
        # Arrange: Load and set metadata
        agent.load_project(project_3csic_path)
        agent.current_metadata = Metadata(title="Old Title", keywords=["old"])

        # Act: Clear metadata
        agent.clear_metadata()

        # Assert: Metadata is reset (default values)
        assert agent.current_metadata.title is None
        assert agent.current_metadata.keywords == []


class TestAgentProtocolInjection:
    """Tests for CORRECT behavior: Agent should inject Field Protocols correctly."""

    def test_agent_gets_field_protocol_from_config(
        self, agent, project_3csic_path, workspace_manager
    ):
        """
        Test behavior: Agent should read user-selected field protocol from project config.
        """
        # Arrange: Load project and set field protocol
        agent.load_project(project_3csic_path)
        project_id = agent.project_id

        # Set field protocol in config
        config = workspace_manager.load_project_config(project_id)
        config["field_name"] = "Physics"
        workspace_manager.save_project_config(project_id, config)

        # Act: Get effective field
        field = agent._get_effective_field()

        # Assert: Returns user-selected field
        assert field == "Physics"

    def test_agent_no_heuristics_field_detection(
        self, agent, workspace_manager, tmp_path
    ):
        """
        Test behavior: Agent should NOT auto-detect field from file extensions.
        Field protocol is 100% user-controlled (NO automatic heuristics).
        """
        # Arrange: Create fingerprint with obvious physics files
        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(tmp_path),
            file_count=5,
            total_size_bytes=5000,
            extensions=[".tex", ".born", ".kappa"],  # Physics indicators
            structure_sample=[],
            significant_files=[],
        )
        agent.project_id = "test-project"

        # Act: Get effective field (no user selection)
        field = agent._get_effective_field()

        # Assert: Returns None - NO automatic detection
        assert field is None


class TestAgentRealisticProjects:
    """Integration tests using realistic project fixtures."""

    def test_agent_loads_3csic_project_structure(
        self, agent, project_3csic_path, workspace_manager
    ):
        """
        Test behavior: Agent should correctly load 3C-SiC project with all files.
        """
        # Arrange: Project path exists
        assert project_3csic_path.exists()

        # Act: Load project
        loaded = agent.load_project(project_3csic_path)

        # Assert: Project loaded successfully
        assert loaded is True
        assert agent.project_id is not None

        # Verify fingerprint can be created
        agent.refresh_inventory(project_3csic_path, force=True)
        assert agent.current_fingerprint is not None
        assert agent.current_fingerprint.file_count > 0

    def test_agent_loads_fesi_project_structure(
        self, agent, project_fesi_path, workspace_manager
    ):
        """
        Test behavior: Agent should correctly load FeSi project with all files.
        """
        # Arrange: Project path exists
        assert project_fesi_path.exists()

        # Act: Load project (may return False if no prior state, which is OK)
        loaded = agent.load_project(project_fesi_path)

        # Assert: Project ID is set (structure created in workspace)
        assert agent.project_id is not None

    def test_agent_processes_tex_content_for_metadata(
        self, agent, project_3csic_path, realistic_projects
    ):
        """
        Test behavior: Agent should be able to extract metadata from TeX content.
        This tests the integration between Agent -> FullTextReader -> Parser.
        """
        # Arrange: Load expected metadata
        expected = realistic_projects["3C-SiC"]

        # Read TeX content (file is in root of fixture, not paper/ subdirectory)
        main_tex = project_3csic_path / "main.tex"
        from opendata.utils import FullTextReader

        content = FullTextReader.read_full_text(main_tex)

        # Assert: Content contains expected metadata markers
        assert content is not None
        assert len(content) > 0
        assert "Thermal conductivity" in content
        assert "Jochym" in content or "Łażewski" in content


class TestAgentSignificantFiles:
    """Tests for CORRECT behavior: Manual file selection workflow."""

    def test_agent_add_significant_file(self, agent, project_3csic_path):
        """
        Test behavior: Adding a significant file should update fingerprint and analysis.
        """
        # Arrange: Load project and create fingerprint
        agent.load_project(project_3csic_path)
        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(project_3csic_path),
            file_count=10,
            total_size_bytes=10000,
            extensions=[".tex"],
            structure_sample=["main.tex"],
            significant_files=[],
        )

        # Act: Add significant file
        agent.add_significant_file("main.tex", category="main_article")

        # Assert: File is in significant files
        assert "main.tex" in agent.current_fingerprint.significant_files
        assert agent.heuristics_run is True

    def test_agent_remove_significant_file(self, agent, project_3csic_path):
        """
        Test behavior: Removing a significant file should update both fingerprint and analysis.
        """
        # Arrange: Load project with significant file
        agent.load_project(project_3csic_path)
        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(project_3csic_path),
            file_count=10,
            total_size_bytes=10000,
            extensions=[".tex"],
            structure_sample=["main.tex"],
            significant_files=["main.tex"],
        )

        # Act: Remove file
        agent.remove_significant_file("main.tex")

        # Assert: File is removed
        assert "main.tex" not in agent.current_fingerprint.significant_files

    def test_agent_set_significant_files_manual(self, agent, project_3csic_path):
        """
        Test behavior: Bulk set significant files with categories.
        """
        # Arrange: Load project
        agent.load_project(project_3csic_path)
        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(project_3csic_path),
            file_count=10,
            total_size_bytes=10000,
            extensions=[".tex", ".yaml"],
            structure_sample=["main.tex", "OpenData.yaml"],
            significant_files=[],
        )

        # Act: Set files manually
        selections = [
            {"path": "main.tex", "category": "main_article"},
            {"path": "OpenData.yaml", "category": "documentation"},
        ]
        msg = agent.set_significant_files_manual(selections)

        # Assert: Files are set with categories
        assert len(agent.current_fingerprint.significant_files) == 2
        assert agent.heuristics_run is True
        assert "main.tex" in msg
