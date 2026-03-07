import unittest.mock

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


def test_bug_command_creates_pending_report_dict(agent, tmp_path):
    """Bug command must store a pending_bug_report dict for the UI dialog."""
    project_path = tmp_path / "my_project"
    project_path.mkdir()
    agent.load_project(project_path)

    agent._handle_bug_command("/bug application crashes on startup")

    report = agent._pending_bug_report
    assert report is not None
    assert isinstance(report, dict)
    # Title must include the user's description
    assert "application crashes on startup" in report["title"]
    # User description is stored separately for the editable text field
    assert "application crashes on startup" in report["description"]
    # Auto-generated context section is present
    assert "System Info" in report["system_body"]
    # YAML file path is in extra_files
    assert len(report["extra_files"]) == 1


def test_handle_bug_command_saves_yaml_report(agent, tmp_path):
    """Bug command must still save a local YAML diagnostic report."""
    project_path = tmp_path / "my_project"
    project_path.mkdir()
    agent.load_project(project_path)

    agent._handle_bug_command("/bug something went wrong")

    bug_files = list(agent.wm.bug_reports_dir.glob("bug_report_*.yaml"))
    assert len(bug_files) == 1


def test_handle_bug_command_yaml_path_in_extra_files(agent, tmp_path):
    """The auto-saved YAML report path must appear in extra_files."""
    project_path = tmp_path / "my_project"
    project_path.mkdir()
    agent.load_project(project_path)

    agent._handle_bug_command("/bug yaml attachment test")

    bug_files = list(agent.wm.bug_reports_dir.glob("bug_report_*.yaml"))
    assert len(bug_files) == 1
    yaml_path = str(bug_files[0])
    assert yaml_path in agent._pending_bug_report["extra_files"]


def test_handle_bug_command_no_description(agent, tmp_path):
    """Bug command without description must still populate pending_bug_report."""
    project_path = tmp_path / "my_project"
    project_path.mkdir()
    agent.load_project(project_path)

    agent._handle_bug_command("/bug")

    assert agent._pending_bug_report is not None
    assert agent._pending_bug_report["title"].startswith("Bug:")


def test_submit_bug_via_github_api_calls_correct_endpoint(agent):
    """_submit_bug_via_github_api must POST to the correct GitHub API endpoint."""
    fake_issue_url = "https://github.com/jochym/opendata/issues/999"
    mock_response = unittest.mock.MagicMock()
    mock_response.read.return_value = (
        f'{{"html_url": "{fake_issue_url}"}}'.encode()
    )
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = unittest.mock.MagicMock(return_value=False)

    with unittest.mock.patch("urllib.request.urlopen", return_value=mock_response):
        result = agent._submit_bug_via_github_api("Test title", "Test body", "token", ["bug"])

    assert result == fake_issue_url


def test_submit_bug_via_github_api_returns_none_on_failure(agent):
    """_submit_bug_via_github_api must return None when the network call fails."""
    with unittest.mock.patch(
        "urllib.request.urlopen", side_effect=OSError("network error")
    ):
        result = agent._submit_bug_via_github_api("title", "body", "token", ["bug"])

    assert result is None

