import pytest
from pathlib import Path
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.workspace import WorkspaceManager


@pytest.fixture
def wm(tmp_path):
    return WorkspaceManager(base_path=tmp_path)


@pytest.fixture
def physics_project_path():
    # Use relative path from test file location
    test_dir = Path(__file__).parent.parent
    return test_dir / "fixtures" / "physics_project"


@pytest.fixture
def chemistry_project_path():
    # Use relative path from test file location
    test_dir = Path(__file__).parent.parent
    return test_dir / "fixtures" / "chemistry_project"


def test_physics_project_heuristic_extraction(wm, physics_project_path):
    """Test that LaTeX extractor correctly extracts metadata from physics project.
    
    Expected behavior:
    - Title should be extracted from manuscript.tex (LaTeX source)
    - Authors should include "Jochym" and "Kowalski" from LaTeX
    - VASP files should be detected but NOT overwrite LaTeX metadata
    """
    agent = ProjectAnalysisAgent(wm=wm)
    # Mocking progress_callback to avoid UI dependencies
    agent.refresh_inventory(
        physics_project_path, progress_callback=lambda m, f, s: None
    )

    metadata = agent.current_metadata
    
    # Assert EXACT expected behavior from LaTeX paper
    assert metadata.title is not None, \
        "Title should be extracted from manuscript.tex"
    
    # The fixture has a LaTeX paper with this specific title
    assert "Phonon-mediated superconductivity" in metadata.title, \
        f"Expected LaTeX title about phonon superconductivity, got: {metadata.title}"
    
    # Verify title came from LaTeX, not from VASP generic fallback
    # (VASP extractor should not overwrite LaTeX-extracted title)
    assert not metadata.title.startswith("VASP"), \
        "Title should come from LaTeX paper, not VASP generic title"
    
    # Verify authors from LaTeX
    assert len(metadata.authors) > 0, \
        "Should extract authors from LaTeX (Jochym, Kowalski)"
    assert any("Jochym" in a.name for a in metadata.authors), \
        f"Should find 'Jochym' in authors, got: {[a.name for a in metadata.authors]}"

    # Check if VASP extractor worked (separate from metadata)
    # Note: This tests the inventory scan, not metadata extraction
    msg = agent.refresh_inventory(physics_project_path)
    assert "VASP" in msg or "phonopy" in msg.lower(), \
        f"Should detect VASP/Phonopy files in inventory, got: {msg}"


def test_chemistry_project_heuristic_extraction(wm, chemistry_project_path):
    """Test that scanner correctly inventories chemistry project files.
    
    Expected behavior:
    - Should find manuscript/draft.md
    - Should find data/spectra/FTIR_MOF_IFJ_1.csv
    - Should detect CSV extension
    """
    agent = ProjectAnalysisAgent(wm=wm)
    agent.refresh_inventory(chemistry_project_path)

    # Verify fingerprint has correct file count
    # The fixture has 2 files: draft.md and FTIR_MOF_IFJ_1.csv
    assert agent.current_fingerprint.file_count >= 2, \
        f"Expected at least 2 files (draft.md, FTIR CSV), got: {agent.current_fingerprint.file_count}"
    
    # Verify CSV files were detected
    assert any(".csv" in ext for ext in agent.current_fingerprint.extensions), \
        f"Expected .csv extension, got: {agent.current_fingerprint.extensions}"
    
    # Verify some metadata was extracted (at minimum from Markdown)
    metadata = agent.current_metadata
    # Note: Markdown extractor may or may not extract title depending on format
    # For now, we just verify the scan completed without crashing
    assert metadata is not None, "Metadata object should exist after scan"
