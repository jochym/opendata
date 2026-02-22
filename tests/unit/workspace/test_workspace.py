import pytest
from opendata.workspace import WorkspaceManager
from pathlib import Path
import tempfile


def test_delete_project_removes_from_cache():
    """Test behavior: delete_project should clear cache and remove project."""
    wm = WorkspaceManager()
    tmpdir = Path(tempfile.mkdtemp())
    project_id = wm.get_project_id(tmpdir)
    
    # Create project state
    wm.save_project_config(project_id, {"test": "data"})
    
    # Verify exists
    projects = wm.list_projects()
    assert len(projects) > 0
    
    # Delete
    success = wm.delete_project(project_id)
    assert success is True
    
    # Verify cache is cleared
    assert wm._projects_cache is None
    
    # Verify gone from list
    projects = wm.list_projects()
    project_ids = [p["id"] for p in projects]
    assert project_id not in project_ids


def test_delete_nonexistent_project():
    """Test behavior: deleting nonexistent project should not crash."""
    wm = WorkspaceManager()
    success = wm.delete_project("nonexistent-project-id")
    # Should return True (considered deleted if doesn't exist)
    assert success is True
