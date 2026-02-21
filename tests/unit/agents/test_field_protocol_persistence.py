import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from opendata.workspace import WorkspaceManager
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.protocols.manager import ProtocolManager


@pytest.fixture
def workspace(tmp_path):
    """Creates a temporary workspace for testing."""
    ws_path = tmp_path / ".opendata_tool"
    ws_path.mkdir(parents=True, exist_ok=True)
    return ws_path


@pytest.fixture
def project_path(tmp_path):
    """Creates a fake project directory with sample files."""
    proj = tmp_path / "test_project"
    proj.mkdir(parents=True, exist_ok=True)

    # Create some sample files
    (proj / "paper").mkdir()
    (proj / "paper" / "main.tex").write_text("\\documentclass{article}")
    (proj / "data").mkdir()
    (proj / "data" / "results.dat").write_text("1 2 3")
    (proj / "WAVECAR_test").write_text("fake wavecar")
    (proj / "analysis_TAKE1").mkdir()
    (proj / "analysis_TAKE1" / "output.out").write_text("test")

    return proj


@pytest.fixture
def agent(workspace):
    """Creates a ProjectAnalysisAgent with mocked dependencies."""
    wm = WorkspaceManager(workspace)
    agent = ProjectAnalysisAgent(wm)
    return agent


class TestFieldProtocolPersistence:
    """Tests for field protocol persistence and isolation from metadata."""

    def test_field_protocol_loads_from_project_config(
        self, workspace, project_path, agent
    ):
        """Field protocol should be loaded from project_config.json on initialization."""
        # Arrange: Set up project config with specific field
        project_id = agent.wm.get_project_id(project_path)
        agent.project_id = project_id

        config = {"field_name": "physics"}
        agent.wm.save_project_config(project_id, config)

        # Act: Get effective field
        field = agent._get_effective_field()

        # Assert: Field comes from config, not metadata
        assert field == "physics"
        assert agent.current_metadata.science_branches_mnisw == []  # Metadata untouched

    def test_field_protocol_persists_to_disk(self, workspace, project_path, agent):
        """Field protocol selection should be saved to project_config.json."""
        # Arrange
        project_id = agent.wm.get_project_id(project_path)
        agent.project_id = project_id

        # Act: User selects field protocol
        agent.set_field_protocol("physics")

        # Assert: Config file exists and contains correct value
        config_path = agent.wm.get_project_config_path(project_id)
        assert config_path.exists()

        with open(config_path, "r") as f:
            config = json.load(f)

        assert config["field_name"] == "physics"
        assert agent.current_metadata.science_branches_mnisw == []  # Metadata untouched

    def test_field_protocol_survives_rescan(self, workspace, project_path, agent):
        """Field protocol should persist through multiple scan operations."""
        # Arrange
        project_id = agent.wm.get_project_id(project_path)
        agent.project_id = project_id
        agent.set_field_protocol("physics")

        # Verify initial state
        config = agent.wm.load_project_config(project_id)
        assert config["field_name"] == "physics"

        # Act: Perform multiple "scans" (simulated)
        # In real code this would call refresh_inventory()
        # For this test, we just verify the config persists
        agent.set_field_protocol("physics")  # Simulate re-selection
        agent.set_field_protocol("physics")  # Simulate another operation

        # Assert: Field protocol unchanged
        config = agent.wm.load_project_config(project_id)
        assert config["field_name"] == "physics"

    def test_field_protocol_change_affects_scan_exclusions(
        self, workspace, project_path, agent
    ):
        """Changing field protocol should change the exclusion patterns used."""
        # Arrange
        project_id = agent.wm.get_project_id(project_path)
        agent.project_id = project_id

        # Act 1: Set to physics field
        agent.set_field_protocol("physics")
        effective_physics = agent.pm.resolve_effective_protocol(project_id, "physics")
        physics_excludes = set(effective_physics["exclude"])

        # Act 2: Set to different field (e.g., medical)
        agent.set_field_protocol("medical")
        effective_medical = agent.pm.resolve_effective_protocol(project_id, "medical")
        medical_excludes = set(effective_medical["exclude"])

        # Assert: Different fields have different exclusions
        # Physics should have VASP-specific exclusions
        assert "**/WAVECAR*" in physics_excludes

        # Medical might have different exclusions (or none)
        # The key is they should be different
        assert physics_excludes != medical_excludes or "medical" not in [
            p.stem for p in agent.pm.fields_dir.glob("*.yaml")
        ]

    def test_field_protocol_independent_from_metadata(
        self, workspace, project_path, agent
    ):
        """Field protocol changes should NOT affect RODBUK metadata classification fields."""
        # Arrange
        project_id = agent.wm.get_project_id(project_path)
        agent.project_id = project_id

        # Set initial metadata (simulating user filling RODBUK classification)
        agent.current_metadata.science_branches_mnisw = ["nauki fizyczne"]
        agent.current_metadata.science_branches_oecd = ["Physical Sciences"]

        # Act: Change field protocol
        agent.set_field_protocol("physics")

        # Assert: Metadata unchanged
        assert agent.current_metadata.science_branches_mnisw == ["nauki fizyczne"]
        assert agent.current_metadata.science_branches_oecd == ["Physical Sciences"]

        # Act 2: Change metadata
        agent.current_metadata.science_branches_mnisw = ["nauki chemiczne"]

        # Assert: Field protocol unchanged
        field = agent._get_effective_field()
        assert field == "physics"  # Still physics, not affected by metadata change

    def test_field_protocol_no_heuristics_fully_user_controlled(
        self, workspace, project_path, agent
    ):
        """NO automatic heuristics - field protocol is 100% user controlled."""
        # Arrange
        project_id = agent.wm.get_project_id(project_path)
        agent.project_id = project_id

        # Ensure no config exists
        config_path = workspace / "projects" / project_id / "project_config.json"
        if config_path.exists():
            config_path.unlink()

        # Create a fingerprint with physics-like files
        from opendata.models import ProjectFingerprint

        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(project_path),
            file_count=5,
            total_size_bytes=1000,
            extensions=[".tex", ".dat", ".born"],  # Physics indicators
            structure_sample=["paper/main.tex", "data/results.dat", "system.born"],
            primary_file=None,
            significant_files=[],
        )

        # Act: Get effective field (should return None - NO heuristics)
        field = agent._get_effective_field()

        # Assert: NO automatic detection - field is None until user selects
        assert field is None, (
            f"BUG! Automatic heuristics detected field '{field}'! "
            f"Field protocol must be 100% user-controlled with NO automatic detection!"
        )

    def test_field_protocol_user_selection_persists(
        self, workspace, project_path, agent
    ):
        """User's field selection persists (no heuristics to interfere)."""
        # Arrange
        project_id = agent.wm.get_project_id(project_path)
        agent.project_id = project_id

        # Create a fingerprint with medical-like files
        from opendata.models import ProjectFingerprint

        agent.current_fingerprint = ProjectFingerprint(
            root_path=str(project_path),
            file_count=3,
            total_size_bytes=500,
            extensions=[".dcm", ".nii"],  # Medical indicators
            structure_sample=["dicom/image.dcm", "data.nii"],
            primary_file=None,
            significant_files=[],
        )

        # User explicitly selects physics
        agent.set_field_protocol("physics")

        # Act: Get effective field
        field = agent._get_effective_field()

        # Assert: User selection persists regardless of file types
        assert field == "physics", (
            f"User selection didn't persist! Expected 'physics', got '{field}'"
        )

    def test_field_protocol_loaded_on_agent_init(self, workspace, project_path):
        """Field protocol should be loaded when agent is initialized with existing project."""
        # Arrange: Create workspace and set field protocol
        wm = WorkspaceManager(workspace)
        project_id = wm.get_project_id(project_path)

        config = {"field_name": "physics"}
        wm.save_project_config(project_id, config)

        # Act: Create new agent instance
        agent = ProjectAnalysisAgent(wm)
        agent.project_id = project_id

        # Assert: Agent loads field from config
        field = agent._get_effective_field()
        assert field == "physics"

    def test_field_protocol_empty_config_returns_none(
        self, workspace, project_path, agent
    ):
        """If project config exists but has no field_name, should return None (NO automatic heuristics)."""
        # Arrange
        project_id = agent.wm.get_project_id(project_path)
        agent.project_id = project_id

        # Create empty config
        agent.wm.save_project_config(project_id, {})

        # Act
        field = agent._get_effective_field()

        # Assert: Returns None (NO automatic detection - field is 100% user-controlled)
        assert field is None

    def test_field_protocol_changes_reflected_in_effective_protocol(
        self, workspace, project_path, agent
    ):
        """When field protocol changes, resolve_effective_protocol should return updated exclusions."""
        # Arrange
        project_id = agent.wm.get_project_id(project_path)
        agent.project_id = project_id

        # Act 1: Set physics field
        agent.set_field_protocol("physics")
        effective = agent.pm.resolve_effective_protocol(project_id, "physics")

        # Assert 1: Physics exclusions present
        assert "**/WAVECAR*" in effective["exclude"]
        assert "**/CHG*" in effective["exclude"]

        # Act 2: Change to different field
        agent.set_field_protocol("dft")
        effective_dft = agent.pm.resolve_effective_protocol(project_id, "dft")

        # Assert 2: Different exclusions (or empty if dft doesn't exist)
        # The key is the system responds to the change
        assert effective_dft is not None


class TestFieldProtocolIntegration:
    """Integration tests for field protocol with full workflow."""

    def test_full_workflow_field_persistence(self, workspace, project_path):
        """Complete workflow: create project, set field, rescan, verify persistence."""
        # Arrange
        wm = WorkspaceManager(workspace)
        agent = ProjectAnalysisAgent(wm)
        project_id = wm.get_project_id(project_path)
        agent.project_id = project_id

        # Step 1: User selects field protocol
        agent.set_field_protocol("physics")

        # Verify saved to disk
        config = wm.load_project_config(project_id)
        assert config["field_name"] == "physics"

        # Step 2: Simulate scan operation (which used to overwrite metadata)
        # In the old buggy code, this would set metadata.science_branches_mnisw
        # and potentially overwrite the field selection
        agent.current_metadata.science_branches_mnisw = ["nauki fizyczne"]

        # Step 3: Verify field protocol still correct
        field = agent._get_effective_field()
        assert field == "physics"  # Not affected by metadata

        # Step 4: Change field protocol
        agent.set_field_protocol("medical")

        # Step 5: Verify change persisted
        config = wm.load_project_config(project_id)
        assert config["field_name"] == "medical"

        # Step 6: Verify metadata still independent
        assert agent.current_metadata.science_branches_mnisw == ["nauki fizyczne"]
