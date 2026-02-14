import pytest
from pathlib import Path
from opendata.protocols.manager import ProtocolManager
from opendata.models import ExtractionProtocol, ProtocolLevel
from opendata.workspace import WorkspaceManager


@pytest.fixture
def wm(tmp_path):
    return WorkspaceManager(base_path=tmp_path)


def test_protocol_resolution_order(wm):
    """Test that protocols are merged in correct order: System -> User -> Field -> Project."""
    pm = ProtocolManager(wm)

    # 1. User Protocol
    user_p = ExtractionProtocol(
        id="user",
        name="User",
        level=ProtocolLevel.USER,
        exclude_patterns=["*.user_exclude"],
    )
    pm.save_user_protocol(user_p)

    # 2. Field Protocol
    field_p = ExtractionProtocol(
        id="field_test",
        name="Test Field",
        level=ProtocolLevel.FIELD,
        exclude_patterns=["*.field_exclude"],
    )
    pm.save_field_protocol(field_p)

    # 3. Project Protocol
    project_id = "test_proj"
    proj_p = ExtractionProtocol(
        id="proj_test",
        name="Project",
        level=ProtocolLevel.PROJECT,
        exclude_patterns=["*.proj_exclude"],
    )
    pm.save_project_protocol(project_id, proj_p)

    # Resolve
    effective = pm.resolve_effective_protocol(
        project_id=project_id, field_name="Test Field"
    )

    # Check System defaults are present (e.g., **/node_modules)
    assert "**/node_modules" in effective["exclude"]

    # Check all layers are present
    assert "*.user_exclude" in effective["exclude"]
    assert "*.field_exclude" in effective["exclude"]
    assert "*.proj_exclude" in effective["exclude"]

    # Verify deduplication (add duplicate to check)
    effective_dup = pm.resolve_effective_protocol(
        project_id=project_id, field_name="Test Field"
    )
    assert effective_dup["exclude"].count("*.user_exclude") == 1


def test_builtin_fields(wm):
    """Test loading of built-in field protocols."""
    pm = ProtocolManager(wm)
    physics = pm.get_field_protocol("physics")
    assert physics.name == "Physics"
    assert "**/WAVECAR*" in physics.exclude_patterns
