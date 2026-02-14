import pytest
from pathlib import Path
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.workspace import WorkspaceManager


@pytest.fixture
def wm(tmp_path):
    return WorkspaceManager(base_path=tmp_path)


@pytest.fixture
def physics_project_path():
    return Path("/home/jochym/Projects/OpenData/tests/fixtures/physics_project")


@pytest.fixture
def chemistry_project_path():
    return Path("/home/jochym/Projects/OpenData/tests/fixtures/chemistry_project")


def test_physics_project_heuristic_extraction(wm, physics_project_path):
    agent = ProjectAnalysisAgent(wm=wm)
    # Mocking progress_callback to avoid UI dependencies
    agent.refresh_inventory(
        physics_project_path, progress_callback=lambda m, f, s: None
    )

    metadata = agent.current_metadata
    # Check if LaTeX extractor found the title and authors
    # Note: If multiple extractors find a title, the last one wins in the current implementation (line 221 in project_agent.py)
    # VASP extractor (INCAR/POSCAR) might overwrite the LaTeX title if processed later.
    assert metadata.title is not None
    assert (
        "Phonon-mediated superconductivity" in metadata.title
        or "VASP Calculation" in metadata.title
    )
    assert any("Jochym" in a.name for a in metadata.authors)

    # Check if VASP extractor worked
    msg = agent.refresh_inventory(physics_project_path)
    assert "VASP" in msg
    assert "Phonopy" in msg


def test_chemistry_project_heuristic_extraction(wm, chemistry_project_path):
    agent = ProjectAnalysisAgent(wm=wm)
    agent.refresh_inventory(chemistry_project_path)

    metadata = agent.current_metadata
    # Check if it found the files in fingerprint.
    # We have: manuscript/draft.md, data/spectra/FTIR_MOF_IFJ_1.csv
    # Total files: 2 (if we didn't create more)
    assert agent.current_fingerprint.file_count >= 2
    assert any(".csv" in ext for ext in agent.current_fingerprint.extensions)
