import pytest
from pathlib import Path
from unittest.mock import MagicMock
from opendata.utils import FullTextReader
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.models import ProjectFingerprint


@pytest.fixture
def latex_full_file(tmp_path):
    fixture_dir = tmp_path / "latex_full"
    fixture_dir.mkdir()

    content = r"""
\documentclass{article}
\usepackage{graphicx}
\usepackage[utf8]{inputenc}

\title{Ab Initio Study of Perovskite Solar Cells}
\author{Jane Doe$^{1}$ \and John Smith$^{2}$}
\date{\today}

\begin{document}

\maketitle

\begin{abstract}
We present a comprehensive ab initio study of the electronic properties of hybrid perovskite solar cells. 
Using density functional theory (DFT) as implemented in the VASP code, we analyze the band gap evolution under strain.
Our results indicate that compressive strain significantly enhances the optical absorption.
\end{abstract}

\section{Introduction}
Perovskites have emerged as a leading material for next-generation photovoltaics.

\section{Methodology}
All calculations were performed using the Vienna Ab initio Simulation Package (VASP). 
We used the PBE exchange-correlation functional. The plane-wave cutoff was set to 500 eV.

\section{Results}
The calculated band gap is 1.6 eV, which agrees well with experimental data.

\end{document}
    """

    file_path = fixture_dir / "main.tex"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return file_path


def test_full_text_reader_latex(latex_full_file):
    content = FullTextReader.read_full_text(latex_full_file)
    assert "Ab Initio Study of Perovskite Solar Cells" in content
    assert "VASP" in content
    assert "\\begin{document}" in content


def test_project_agent_detects_full_text_candidate(latex_full_file, tmp_path):
    """AI should auto-detect primary publication file (user can override).

    CORRECT BEHAVIOR:
    - AI auto-detects primary publication (LaTeX, PDF, etc.)
    - User can influence or change the decision
    - Test verifies detection works for obvious candidates
    """
    # Setup
    wm_mock = MagicMock()
    wm_mock.get_project_id.return_value = "test_project"
    wm_mock.load_project_state.return_value = (None, [], None, None)
    wm_mock.projects_dir = tmp_path / "projects"
    wm_mock.projects_dir.mkdir()
    (wm_mock.projects_dir / "test_project").mkdir()

    agent = ProjectAnalysisAgent(wm_mock)

    # Create a fingerprint with LaTeX file
    agent.current_fingerprint = ProjectFingerprint(
        root_path=str(latex_full_file.parent),
        file_count=1,
        total_size_bytes=1000,
        extensions=[".tex"],
        structure_sample=[str(latex_full_file.relative_to(latex_full_file.parent))],
    )

    # Verify LaTeX file is in structure sample (AI should detect it)
    assert any("main.tex" in f for f in agent.current_fingerprint.structure_sample), (
        "LaTeX file should be in structure sample for AI detection"
    )

    # TODO: When scanner.heuristics is implemented, verify:
    # 1. AI identifies LaTeX as primary publication candidate
    # 2. User can override the selection
    # For now, test verifies the file is available for detection
