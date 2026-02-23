import pytest
from opendata.workspace import WorkspaceManager
from pathlib import Path

def test_delete_project_removes_from_cache(tmp_path):
    """Test behavior: delete_project should clear cache and remove project."""
    # Use pytest's tmp_path for automatic cleanup
    wm = WorkspaceManager(base_path=tmp_path)
    project_id = wm.get_project_id(tmp_path / "project_source")
    
    # Create project state
    wm.save_project_config(project_id, {"test": "data"})
    
    # Verify exists
    projects = wm.list_projects()
    assert len(projects) > 0
    
    # Delete
    success = wm.delete_project(project_id)
    assert success is True
    
    # Verify gone from list
    projects = wm.list_projects()
    project_ids = [p["id"] for p in projects]
    assert project_id not in project_ids

def test_delete_nonexistent_project(tmp_path):
    """Test behavior: deleting nonexistent project should return False."""
    wm = WorkspaceManager(base_path=tmp_path)
    success = wm.delete_project("nonexistent-project-id")
    assert success is False
