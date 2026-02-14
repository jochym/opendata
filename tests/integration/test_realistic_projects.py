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

    # In version 0.21.0, heuristics are separate from refresh_inventory
    # and they are AI-driven. However, we can still test if the local extractors
    # are working via the scanner service which is used by the agent.
    from opendata.extractors.base import ExtractorRegistry

    registry = ExtractorRegistry()
    from opendata.extractors.latex import LatexExtractor
    from opendata.extractors.physics import VaspExtractor, LatticeDynamicsExtractor

    registry.register(LatexExtractor())
    registry.register(VaspExtractor())
    registry.register(LatticeDynamicsExtractor())

    # Test local extraction directly to verify fixtures and extractors
    heuristics_data = agent.scanner.run_heuristics(
        physics_project_path,
        agent.current_fingerprint,
        exclude_patterns=[],
        registry=registry,
    )

    # Check if LaTeX extractor found the title and authors
    latex_results = heuristics_data.get("LatexExtractor", [])
    assert len(latex_results) > 0
    metadata = latex_results[0]
    assert "Phonon-mediated superconductivity" in metadata.title
    assert any("Jochym" in a["name"] for a in metadata.authors)

    # Check if VASP extractor worked
    vasp_results = heuristics_data.get("VaspExtractor", [])
    assert any("VASP Calculation" in str(r.title) for r in vasp_results)


def test_chemistry_project_heuristic_extraction(wm, chemistry_project_path):
    agent = ProjectAnalysisAgent(wm=wm)
    agent.refresh_inventory(chemistry_project_path)

    metadata = agent.current_metadata
    # Check if it found the files in fingerprint.
    # We have: manuscript/draft.md, data/spectra/FTIR_MOF_IFJ_1.csv
    # Total files: 2 (if we didn't create more)
    assert agent.current_fingerprint.file_count >= 2
    assert any(".csv" in ext for ext in agent.current_fingerprint.extensions)
