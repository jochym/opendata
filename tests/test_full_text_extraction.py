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
    # Setup
    wm_mock = MagicMock()
    wm_mock.get_project_id.return_value = "test_project"
    wm_mock.load_project_state.return_value = (None, [], None)

    agent = ProjectAnalysisAgent(wm_mock)

    # Run scan
    response = agent.start_analysis(latex_full_file.parent)

    # Verify
    assert "main.tex" in response
    assert "process its full text" in response


def test_project_agent_triggers_full_text_analysis(latex_full_file):
    # Setup
    wm_mock = MagicMock()
    wm_mock.get_project_id.return_value = "test_project"
    wm_mock.load_project_state.return_value = (None, [], None)

    agent = ProjectAnalysisAgent(wm_mock)

    # Mock fingerprint to simulate state after scan
    agent.current_fingerprint = ProjectFingerprint(
        root_path=str(latex_full_file.parent),
        file_count=1,
        total_size_bytes=1000,
        extensions=[".tex"],
        structure_sample=["main.tex"],
    )

    # Mock chat history to simulate "Shall I process..." question
    agent.chat_history = [
        ("agent", "Shall I process the full text of main.tex?"),
    ]

    # Mock AI Service
    ai_service_mock = MagicMock()
    ai_service_mock.ask_agent.return_value = """
    {
        "ANALYSIS": {
            "summary": "Extracted data.",
            "missing_fields": [],
            "non_compliant": [],
            "conflicting_data": [],
            "questions": []
        },
        "METADATA": {
            "title": "Ab Initio Study of Perovskite Solar Cells",
            "authors": [{"name": "Jane Doe"}, {"name": "John Smith"}],
            "description": ["We present a comprehensive ab initio study..."],
            "keywords": ["Perovskite", "DFT", "VASP"],
            "kind_of_data": "text"
        }
    }
    """

    # Action: User says "Yes"
    response = agent.process_user_input("Yes", ai_service_mock)

    # Verify
    assert agent.current_metadata.title == "Ab Initio Study of Perovskite Solar Cells"
    assert len(agent.current_metadata.authors) == 2
    assert "VASP" in str(agent.current_metadata.keywords)
    assert ai_service_mock.ask_agent.called
    # Check if the prompt contained the full text
    call_args = ai_service_mock.ask_agent.call_args[0][0]
    assert "Ab Initio Study of Perovskite Solar Cells" in call_args
    assert "Methodology" in call_args


def test_project_agent_handles_structured_analysis_response(latex_full_file):
    # Setup
    wm_mock = MagicMock()
    wm_mock.get_project_id.return_value = "test_project"
    wm_mock.load_project_state.return_value = (None, [], None)
    agent = ProjectAnalysisAgent(wm_mock)

    agent.current_fingerprint = ProjectFingerprint(
        root_path=str(latex_full_file.parent),
        file_count=1,
        total_size_bytes=1000,
        extensions=[".tex"],
        structure_sample=["main.tex"],
    )

    ai_service_mock = MagicMock()
    # New structured response
    ai_service_mock.ask_agent.return_value = """
    METADATA:
    {
        "ANALYSIS": {
            "summary": "Found title and authors, but email is missing.",
            "missing_fields": ["email"],
            "non_compliant": [],
            "conflicting_data": [
                {
                    "field": "title",
                    "sources": [
                        {"source": "main.tex", "value": "Title A"},
                        {"source": "README.md", "value": "Title B"}
                    ]
                }
            ],
            "questions": [
                {
                    "field": "contacts",
                    "label": "Email",
                    "question": "What is the contact email?",
                    "type": "text"
                }
            ]
        },
        "METADATA": {
            "title": "Title A",
            "authors": [{"name": "Jane Doe"}]
        }
    }
    """

    # Trigger analysis
    agent.analyze_full_text(ai_service_mock)

    # Verify Analysis
    assert agent.current_analysis is not None
    assert (
        agent.current_analysis.summary
        == "Found title and authors, but email is missing."
    )
    assert "email" in agent.current_analysis.missing_fields
    assert len(agent.current_analysis.questions) == 1
    assert agent.current_analysis.conflicting_data[0]["field"] == "title"

    # Verify Metadata
    assert agent.current_metadata.title == "Title A"

    # Action: Submit answers
    agent.submit_analysis_answers({"title": "Title B"})

    # Verify final state
    assert agent.current_metadata.title == "Title B"
    assert agent.current_analysis is None  # Should be cleared after submission
