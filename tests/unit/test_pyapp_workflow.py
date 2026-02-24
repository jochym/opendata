"""Tests for PyApp workflow configuration."""
import yaml
from pathlib import Path


def test_pyapp_build_workflow_uses_embedded_wheel():
    """Verify pyapp-build-binary.yml uses PYAPP_PROJECT_PATH for embedded wheel builds."""
    workflow_path = Path(".github/workflows/pyapp-build-binary.yml")
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    
    build_job = workflow["jobs"]["build"]
    build_step = None
    for step in build_job["steps"]:
        if step.get("name") == "Build with PyApp":
            build_step = step
            break
    
    assert build_step is not None, "Build with PyApp step not found"
    
    run_script = build_step["run"]
    
    # Verify PYAPP_PROJECT_PATH is used (embedded wheel mode)
    assert "PYAPP_PROJECT_PATH=" in run_script, \
        "Should use PYAPP_PROJECT_PATH for embedded wheel builds"
    
    # Verify PYAPP_EXEC_MODULE or PYAPP_EXEC_SPEC is used
    assert "PYAPP_EXEC_MODULE=" in run_script or "PYAPP_EXEC_SPEC=" in run_script, \
        "Should use PYAPP_EXEC_MODULE or PYAPP_EXEC_SPEC for entry point"
    
    # Verify PYAPP_EXEC_FUNCTION is NOT used (doesn't exist in PyApp)
    assert "PYAPP_EXEC_FUNCTION=" not in run_script, \
        "PYAPP_EXEC_FUNCTION does not exist in PyApp v0.29.0"
    
    # Verify wheel file is copied and path is absolute
    assert "WHEEL_ABS_PATH=" in run_script, \
        "Should compute absolute path to wheel file"


def test_main_workflow_includes_macos_intel():
    """Verify main.yml includes macOS Intel build for pyApp."""
    workflow_path = Path(".github/workflows/main.yml")
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    
    build_pyapp_job = workflow["jobs"]["build-pyapp-binaries"]
    matrix = build_pyapp_job["strategy"]["matrix"]["include"]
    
    # Find macOS Intel entry
    macos_intel = None
    for entry in matrix:
        if entry.get("target") == "macos-x86_64":
            macos_intel = entry
            break
    
    assert macos_intel is not None, \
        "macOS Intel build should be included in pyApp build matrix"
    assert macos_intel["artifact_name"] == "opendata-macos-intel-pyapp", \
        "macOS Intel artifact should be named opendata-macos-intel-pyapp"
    
    # Verify verify job also includes macOS Intel
    verify_pyapp_job = workflow["jobs"]["verify-pyapp-binaries"]
    verify_matrix = verify_pyapp_job["strategy"]["matrix"]["include"]
    
    macos_intel_verify = None
    for entry in verify_matrix:
        if entry.get("artifact_name") == "opendata-macos-intel-pyapp":
            macos_intel_verify = entry
            break
    
    assert macos_intel_verify is not None, \
        "macOS Intel should be included in pyApp verification matrix"
