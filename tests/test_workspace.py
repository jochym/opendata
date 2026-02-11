import pytest
from pathlib import Path
from opendata.workspace import WorkspaceManager
from opendata.models import Metadata, ProjectFingerprint


def test_project_id_generation(tmp_path):
    wm = WorkspaceManager(tmp_path)
    p1 = tmp_path / "project1"
    p2 = tmp_path / "project2"
    p1.mkdir()
    p2.mkdir()

    id1 = wm.get_project_id(p1)
    id2 = wm.get_project_id(p2)

    assert id1 != id2
    assert len(id1) == 32  # MD5 hash length


def test_save_load_project_state(tmp_path):
    wm = WorkspaceManager(tmp_path)
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    project_id = wm.get_project_id(project_dir)

    metadata = Metadata(title="Test Project", authors=[{"name": "John Doe"}])
    history = [("user", "hello"), ("agent", "hi")]
    fingerprint = ProjectFingerprint(
        root_path=str(project_dir),
        file_count=10,
        total_size_bytes=1000,
        extensions=[".txt"],
        structure_sample=["file.txt"],
    )

    wm.save_project_state(project_id, metadata, history, fingerprint)

    l_metadata, l_history, l_fingerprint, l_analysis = wm.load_project_state(project_id)

    assert l_metadata.title == "Test Project"
    assert l_history == history
    assert l_fingerprint.file_count == 10


def test_list_projects(tmp_path):
    wm = WorkspaceManager(tmp_path)
    p1 = tmp_path / "p1"
    p1.mkdir()
    pid1 = wm.get_project_id(p1)

    metadata = Metadata(title="Project One")
    wm.save_project_state(pid1, metadata, [], None)

    projects = wm.list_projects()
    assert len(projects) == 1
    assert projects[0]["title"] == "Project One"
