import pytest
from pathlib import Path
from unittest.mock import MagicMock
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.models import Metadata, ProjectFingerprint
from opendata.workspace import WorkspaceManager


@pytest.fixture
def mock_wm(tmp_path):
    wm = WorkspaceManager(base_path=tmp_path)
    return wm


@pytest.fixture
def agent(mock_wm):
    # We can inject mocks here if needed, but for now using real components
    # with a temp workspace is good for integration-lite tests
    return ProjectAnalysisAgent(wm=mock_wm)


def test_agent_load_project_new(agent, tmp_path):
    project_path = tmp_path / "my_project"
    project_path.mkdir()

    # Should return False as it's a new project
    assert agent.load_project(project_path) is False
    assert agent.project_id is not None


def test_agent_save_load_state(agent, tmp_path):
    project_path = tmp_path / "my_project"
    project_path.mkdir()
    agent.load_project(project_path)

    agent.current_metadata.title = "Agent Title"
    agent.chat_history.append(("user", "Hello"))
    agent.save_state()

    # Create new agent and load
    new_agent = ProjectAnalysisAgent(wm=agent.wm)
    assert new_agent.load_project(project_path) is True
    assert new_agent.current_metadata.title == "Agent Title"
    assert new_agent.chat_history == [("user", "Hello")]


def test_agent_clear_history(agent, tmp_path):
    project_path = tmp_path / "my_project"
    project_path.mkdir()
    agent.load_project(project_path)

    agent.chat_history.append(("user", "Hello"))
    agent.clear_chat_history()

    assert agent.chat_history == []

    # Verify it was saved
    new_agent = ProjectAnalysisAgent(wm=agent.wm)
    new_agent.load_project(project_path)
    assert new_agent.chat_history == []


def test_agent_generate_ai_prompt(agent, tmp_path):
    project_path = tmp_path / "my_project"
    project_path.mkdir()
    agent.load_project(project_path)
    agent.current_fingerprint = ProjectFingerprint(
        root_path=str(project_path),
        file_count=0,
        total_size_bytes=0,
        extensions=[],
        structure_sample=[],
    )

    prompt = agent.generate_ai_prompt()
    assert "CURRENT METADATA DRAFT" in prompt
    assert "RODBUK" in prompt
