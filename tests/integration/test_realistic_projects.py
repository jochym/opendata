import pytest
from pathlib import Path
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.workspace import WorkspaceManager


@pytest.fixture
def wm(tmp_path):
    return WorkspaceManager(base_path=tmp_path)


@pytest.fixture
def physics_project_path():
    # Use relative path from this test file to the fixtures directory
    return Path(__file__).parent.parent / "fixtures" / "physics_project"


@pytest.fixture
def chemistry_project_path():
    return Path(__file__).parent.parent / "fixtures" / "chemistry_project"


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
    from opendata.extractors.latex import LatexExtractor
    from opendata.extractors.physics import VaspExtractor, LatticeDynamicsExtractor
    from opendata.extractors.citations import BibtexExtractor

    registry = ExtractorRegistry()
    registry.register(LatexExtractor())
    registry.register(VaspExtractor())
    registry.register(LatticeDynamicsExtractor())
    registry.register(BibtexExtractor())

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

    # Check if BibTeX extractor worked
    bib_results = heuristics_data.get("BibtexExtractor", [])
    assert len(bib_results) > 0
    # The fixture has one entry with title "Phonon-mediated superconductivity..."
    assert any("Phonon-mediated superconductivity" in str(r.title) for r in bib_results)


def test_chemistry_project_heuristic_extraction(wm, chemistry_project_path):
    agent = ProjectAnalysisAgent(wm=wm)
    # Ensure extractors are set up (agent does this by default, but we want to be sure)
    # The agent.__init__ calls _setup_extractors if registry is None.

    # We need to run the scanner manually to check extraction results,
    # as refresh_inventory only does file scanning.
    agent.refresh_inventory(chemistry_project_path)

    # Verify basic fingerprinting
    assert agent.current_fingerprint is not None
    assert agent.current_fingerprint.file_count >= 2
    assert any(".csv" in ext for ext in agent.current_fingerprint.extensions)

    # Since there is no Markdown extractor in heuristics, we verify that
    # the agent can at least IDENTIFY the markdown file as significant
    # during the AI Heuristics phase.

    from unittest.mock import MagicMock

    mock_ai = MagicMock()
    # Mock AI response to simulate finding the draft
    # AIHeuristicsService expects a specific JSON structure with "SELECTION" and "ANALYSIS"
    # and validates paths against the inventory DB.
    mock_ai.ask_agent.return_value = """
{
  "ANALYSIS": "Found a markdown draft and a data file.",
  "SELECTION": [
    {"path": "manuscript/draft.md", "reason": "Draft paper"},
    {"path": "data/spectra/FTIR_MOF_IFJ_1.csv", "reason": "Spectral data"}
  ]
}
"""

    # Run heuristics phase
    agent.run_heuristics_phase(
        project_dir=chemistry_project_path,
        ai_service=mock_ai,
        progress_callback=lambda m, f, s: None,
    )

    # Verify the agent correctly processed the AI response
    assert agent.current_fingerprint.significant_files == [
        "manuscript/draft.md",
        "data/spectra/FTIR_MOF_IFJ_1.csv",
    ]
    assert agent.heuristics_run is True
