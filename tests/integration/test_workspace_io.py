import pytest
from pathlib import Path
from opendata.workspace import WorkspaceManager
from opendata.models import Metadata


def test_workspace_init_custom_path(tmp_path):
    wm = WorkspaceManager(base_path=tmp_path)
    assert wm.base_path == tmp_path
    assert (tmp_path / "projects").exists()
    assert (tmp_path / "protocols").exists()


def test_project_id_consistency(tmp_path):
    wm = WorkspaceManager(base_path=tmp_path)
    project_path = Path("/some/random/project")
    pid1 = wm.get_project_id(project_path)
    pid2 = wm.get_project_id(project_path)
    assert pid1 == pid2
    assert len(pid1) == 32  # MD5 hash length


def test_save_load_project_state(tmp_path):
    wm = WorkspaceManager(base_path=tmp_path)
    project_id = "test_project"
    metadata = Metadata(title="Test Project")
    history = [("user", "Hello"), ("agent", "Hi")]

    wm.save_project_state(project_id, metadata, history, None)

    loaded_meta, loaded_hist, loaded_fp, loaded_ana = wm.load_project_state(project_id)

    assert loaded_meta.title == "Test Project"
    assert loaded_hist == history
    assert loaded_fp is None
    assert loaded_ana is None


def test_list_projects(tmp_path):
    wm = WorkspaceManager(base_path=tmp_path)
    # Create two projects
    wm.save_project_state("p1", Metadata(title="Project 1"), [], None)
    wm.save_project_state("p2", Metadata(title="Project 2"), [], None)

    projects = wm.list_projects()
    assert len(projects) == 2
    titles = [p["title"] for p in projects]
    assert "Project 1" in titles
    assert "Project 2" in titles
