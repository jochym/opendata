"""
End-to-End Tests for OpenData Tool - Full Workflow

⚠️  AI INTERACTION TEST - LOCAL EXECUTION ONLY

This test uses AI services and should:
- Run LOCALLY only (NOT in CI/CD/GitHub Actions)
- Use OpenAI interface for better quotas
- Start app with: python src/opendata/main.py --api

To run:
    python src/opendata/main.py --api --headless
    pytest tests/end_to_end/test_full_workflow.py -v

To skip AI tests:
    pytest -m "not ai_interaction" -v
"""

import pytest
import shutil
import logging
from pathlib import Path
from opendata.workspace import WorkspaceManager
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.ai.service import AIService
from opendata.models import UserSettings

# Mark as AI interaction test (local only)
pytestmark = pytest.mark.ai_interaction

# Setup logging to capture everything
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("tests.e2e")


@pytest.fixture
def real_project_path():
    """Points to the realistic project fixture."""
    # Use the realistic project fixture
    path = Path(__file__).parent.parent / "fixtures" / "realistic_projects" / "3C-SiC"
    if not path.exists():
        # Fallback for backward compatibility
        path = Path("/home/jochym/calc/3C-SiC/Project")
        if not path.exists():
            pytest.skip(f"Project path {path} not found. Skipping E2E test.")
    return path


@pytest.fixture
def workspace(tmp_path):
    """Creates a temporary workspace for the test, copying real protocol configs."""
    ws_path = tmp_path / ".opendata_tool"

    # Copy real protocol configs from user's workspace to match UI testing
    real_protocols = Path.home() / ".opendata_tool" / "protocols"
    if real_protocols.exists():
        test_protocols = ws_path / "protocols"
        import shutil

        shutil.copytree(real_protocols, test_protocols)
        logger.info(f"Copied real protocol configs to {test_protocols}")

    # Copy project-specific protocol for the test project
    # Calculate project ID from fixture path (same as workspace does)
    import hashlib

    fixture_path = (
        Path(__file__).parent.parent / "fixtures" / "realistic_projects" / "3C-SiC"
    )
    test_project_id = (
        hashlib.md5(str(fixture_path).encode()).hexdigest()
        if fixture_path.exists()
        else "ec7e33c23da584709f6322cb52b01d52"
    )

    real_projects = Path.home() / ".opendata_tool" / "projects"
    real_project_protocol = real_projects / test_project_id / "protocol.yaml"
    if real_project_protocol.exists():
        test_project_dir = ws_path / "projects" / test_project_id
        test_project_dir.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.copy(real_project_protocol, test_project_dir / "protocol.yaml")
        logger.info(f"Copied project protocol to {test_project_dir / 'protocol.yaml'}")

    return ws_path


@pytest.fixture
def ai_service(workspace):
    """
    Initializes the AI service for testing.

    ⚠️  LOCAL TESTING ONLY - Uses OpenAI interface for better quotas

    Configuration:
    - Loads user's settings from ~/.opendata_tool/settings.yaml
    - Forces OpenAI provider (better quotas than Google GenAI)
    - Uses model from settings or defaults to gemini-3-flash-preview
    """
    # Copy the user's actual settings.yaml to the test workspace
    real_settings = Path.home() / ".opendata_tool" / "settings.yaml"
    if real_settings.exists():
        workspace.mkdir(parents=True, exist_ok=True)
        test_settings = workspace / "settings.yaml"
        shutil.copy(real_settings, test_settings)
        logger.info(f"Copied real settings to {test_settings}")
    else:
        pytest.skip("settings.yaml not found. Skipping E2E test.")

    # Load settings from the copied file
    import yaml

    with open(test_settings, "r") as f:
        settings_dict = yaml.safe_load(f)

    # FORCE OpenAI provider for better quotas (local testing only)
    settings_dict["ai_provider"] = "openai"

    # Create UserSettings with OpenAI provider
    settings = UserSettings(**settings_dict)

    # Initialize AIService with OpenAI provider
    service = AIService(workspace, settings)

    # Authenticate using the underlying provider
    provider = service.provider
    if hasattr(provider, "authenticate"):
        if not provider.authenticate(silent=True):
            pytest.skip("AI Provider could not authenticate. Skipping E2E test.")

    # Use model from settings or default
    model = settings.openai_model or "gemini-3-flash-preview"
    service.switch_model(model)

    logger.info(f"AI Service initialized with OpenAI provider, model: {model}")

    return service


def test_e2e_full_extraction_flow(real_project_path, workspace, ai_service):
    """
    End-to-End test simulating the full user workflow:
    1. Scan Project (Initial)
    2. Select Field Protocol (Physics)
    3. Re-scan Project (with Physics exclusions)
    4. AI Heuristics (File Selection)
    5. AI Analysis (Metadata Extraction)
    6. Verification
    """
    wm = WorkspaceManager(workspace)
    agent = ProjectAnalysisAgent(wm)

    # --- STEP 1: INITIAL SCANNING ---
    logger.info("--- STEP 1: INITIAL SCANNING ---")
    scan_msg = agent.refresh_inventory(real_project_path, force=True)
    assert "Inventory refreshed" in scan_msg
    assert agent.current_fingerprint is not None
    initial_file_count = agent.current_fingerprint.file_count
    logger.info(f"Initial scan: {initial_file_count} files.")

    # --- STEP 2: FIELD SELECTION ---
    logger.info("--- STEP 2: FIELD SELECTION ---")
    # Manually select "physics" field protocol using the proper method
    agent.set_field_protocol("physics")
    field = agent._get_effective_field()
    assert field == "physics"
    logger.info(f"Field selected: {field}")

    # --- STEP 3: RE-SCAN WITH PHYSICS PROTOCOL ---
    logger.info("--- STEP 3: RE-SCAN WITH PHYSICS PROTOCOL ---")
    # Re-scanning should now use physics exclusions
    scan_msg = agent.refresh_inventory(real_project_path, force=True)
    assert "Inventory refreshed" in scan_msg
    physics_file_count = agent.current_fingerprint.file_count
    logger.info(f"Physics scan: {physics_file_count} files.")

    # Verify effective protocol combination (System + User + Field + Project)
    effective = agent.pm.resolve_effective_protocol(agent.project_id, field)

    # Log the actual combined patterns for debugging
    logger.info(
        f"Combined exclusion patterns ({len(effective['exclude'])}): {effective['exclude']}"
    )

    # System exclusions (always present)
    assert "**/.*" in effective["exclude"], "System exclusions missing"
    assert "**/__pycache__" in effective["exclude"], "System exclusions missing"

    # User exclusions (from ~/.opendata_tool/protocols/user.yaml)
    assert "slurm-*.out" in effective["exclude"], (
        "User exclusions missing (slurm-*.out)"
    )
    assert "**/tmp/*" in effective["exclude"], "User exclusions missing (**/tmp/*)"

    # Field exclusions (physics-specific, from ~/.opendata_tool/protocols/fields/physics.yaml)
    assert "**/WAVECAR*" in effective["exclude"], "Physics field exclusions missing"
    assert "**/CHG*" in effective["exclude"], "Physics field exclusions missing"
    assert "**/POTCAR" in effective["exclude"], (
        "Physics field exclusions missing (POTCAR)"
    )
    assert "**/*.xml" in effective["exclude"], (
        "Physics field exclusions missing (*.xml)"
    )

    # Project exclusions (from ~/.opendata_tool/projects/{id}/protocol.yaml)
    assert "**/analysis_TAKE*/*" in effective["exclude"], "Project exclusions missing"

    # Field prompts (from physics.yaml)
    assert any("VASP" in p for p in effective["prompts"]), "Physics prompts missing"
    assert any("POSCAR" in p for p in effective["prompts"]), (
        "Physics prompts missing (POSCAR)"
    )

    # Verify file count decreased significantly due to exclusions
    assert physics_file_count < initial_file_count, (
        f"Exclusions not working! Count stayed at {initial_file_count}"
    )

    logger.info(
        f"Effective protocol correctly combined all layers. Files reduced from {initial_file_count} to {physics_file_count}"
    )

    # --- STEP 4: MANUAL FILE SELECTION (Replaces AI Heuristics) ---
    logger.info("--- STEP 4: MANUAL FILE SELECTION ---")

    # Simulate user manually selecting files
    # In a real UI, this would be done via the tree selector
    agent.add_significant_file("paper/main.tex", "main_article")
    agent.add_significant_file("OpenData.yaml", "other")
    agent.add_significant_file("ReadMe.md", "documentation")

    expected_files = ["paper/main.tex", "OpenData.yaml", "ReadMe.md"]
    assert agent.heuristics_run is True
    assert "paper/main.tex" in agent.current_fingerprint.significant_files
    assert agent.current_fingerprint.primary_file == "paper/main.tex"

    # --- STEP 5: AI ANALYSIS (Metadata Extraction) ---
    logger.info("--- STEP 5: AI ANALYSIS ---")
    # ELIMINATION: Force the analysis to focus ONLY on the expected files as requested
    agent.current_fingerprint.significant_files = [
        f
        for f in agent.current_fingerprint.significant_files
        if any(f.endswith(exp) for exp in expected_files)
    ]
    logger.info(
        f"Restricted analysis context to: {agent.current_fingerprint.significant_files}"
    )

    analysis_msg = agent.run_ai_analysis_phase(ai_service)
    logger.info(f"Analysis Result: {analysis_msg}")

    # --- STEP 6: VERIFICATION ---
    logger.info("--- STEP 6: VERIFICATION ---")
    metadata = agent.current_metadata

    # Log extracted metadata for review
    logger.info("=" * 80)
    logger.info("EXTRACTED METADATA:")
    logger.info("=" * 80)
    logger.info(f"Title: {metadata.title}")
    if metadata.authors:
        author_names = [getattr(a, "name", str(a)) for a in metadata.authors]
        logger.info(f"Authors ({len(author_names)}): {author_names}")
    logger.info(
        f"Abstract: {metadata.abstract[:200]}..."
        if metadata.abstract and len(metadata.abstract) > 200
        else f"Abstract: {metadata.abstract}"
    )
    logger.info(f"Keywords: {metadata.keywords}")
    logger.info(f"Software: {metadata.software}")
    logger.info(f"Funding: {metadata.funding}")
    logger.info(f"License: {metadata.license}")
    logger.info(f"Kind of Data: {metadata.kind_of_data}")
    logger.info("=" * 80)

    # Check mandatory fields
    assert metadata.title, "Title is missing"
    assert "Thermal conductivity" in metadata.title

    assert metadata.authors, "Authors are missing"
    assert len(metadata.authors) >= 2, (
        "Should have at least 2 authors (Jochym, Łażewski)"
    )

    assert metadata.description, "Description is missing"
    desc_text = "\n".join(metadata.description)
    assert len(desc_text) > 200, "Description is too short"

    assert metadata.keywords, "Keywords are missing"
    assert metadata.software, "Software list is missing"
    assert any("VASP" in s for s in metadata.software), "VASP not found in software"

    # Check for the specific fields that were problematic
    assert metadata.abstract, "Abstract is missing!"
    assert len(metadata.abstract) > 100, "Abstract seems too short/placeholder"

    # Check funding
    assert metadata.funding, "Funding is missing"
    funding_str = str(metadata.funding)
    assert "National Science Centre" in funding_str or "NCN" in funding_str
    assert "UMO-2014/13/B/ST3/04393" in funding_str

    # Check science branches (AI should auto-detect from project content)
    # Note: This is RODBUK classification, AI should attempt to detect
    if metadata.science_branches_mnisw:
        branches_str = str(metadata.science_branches_mnisw).lower()
        assert "physics" in branches_str or "fizyczne" in branches_str, (
            f"Expected physics-related branch (auto-detected), got: {metadata.science_branches_mnisw}"
        )
    # If empty, AI couldn't detect - user can fill manually (acceptable)

    logger.info("--- TEST SUCCESSFUL: All metadata extracted correctly ---")
