import urllib.parse

import pytest

from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.models import ProjectFingerprint
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


def test_handle_bug_command_generates_github_url(agent, tmp_path):
    """Bug command must generate a pre-filled GitHub issue URL for zero-friction reporting."""
    project_path = tmp_path / "my_project"
    project_path.mkdir()
    agent.load_project(project_path)

    agent._handle_bug_command("/bug application crashes on startup")

    # A GitHub issue URL must be stored for the UI to open
    assert agent._pending_bug_report_url is not None
    url = agent._pending_bug_report_url
    assert url.startswith("https://github.com/jochym/opendata/issues/new")
    assert "labels=bug" in url

    # Title must include the user's description
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    assert "title" in params
    title = urllib.parse.unquote(params["title"][0])
    assert "application crashes on startup" in title

    # Body must contain system info and description
    body = urllib.parse.unquote(params["body"][0])
    assert "application crashes on startup" in body
    assert "OS" in body or "System Info" in body


def test_handle_bug_command_saves_yaml_report(agent, tmp_path):
    """Bug command must still save a local YAML diagnostic report as a fallback."""
    project_path = tmp_path / "my_project"
    project_path.mkdir()
    agent.load_project(project_path)

    agent._handle_bug_command("/bug something went wrong")

    bug_files = list(agent.wm.bug_reports_dir.glob("bug_report_*.yaml"))
    assert len(bug_files) == 1


def test_handle_bug_command_response_contains_link(agent, tmp_path):
    """Bug command response message must contain a clickable GitHub issue link."""
    project_path = tmp_path / "my_project"
    project_path.mkdir()
    agent.load_project(project_path)

    msg = agent._handle_bug_command("/bug test description")

    assert "github.com/jochym/opendata/issues/new" in msg
    # Confirm the link is embedded in markdown syntax
    assert "](https://github.com" in msg


def test_handle_bug_command_no_description(agent, tmp_path):
    """Bug command without description must still generate a valid GitHub URL."""
    project_path = tmp_path / "my_project"
    project_path.mkdir()
    agent.load_project(project_path)

    agent._handle_bug_command("/bug")

    assert agent._pending_bug_report_url is not None
    assert "github.com/jochym/opendata/issues/new" in agent._pending_bug_report_url

