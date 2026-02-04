import pytest
import zipfile
import yaml
import json
from pathlib import Path
from opendata.packager import PackagingService
from opendata.models import Metadata, PersonOrOrg, Contact


@pytest.fixture
def temp_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def sample_project(tmp_path):
    project = tmp_path / "research_project"
    project.mkdir()
    (project / "README.md").write_text("# Test Project")
    (project / "LICENSE").write_text("MIT License")
    (project / "data.csv").write_text("1,2,3\n4,5,6")
    (project / "subdir").mkdir()
    (project / "subdir" / "notes.txt").write_text("Some notes")
    return project


@pytest.fixture
def sample_metadata():
    return Metadata(
        title="Test Project",
        authors=[PersonOrOrg(name="Doe, John", affiliation="Test Univ")],
        contacts=[Contact(person_to_contact="John Doe", email="john@example.com")],
        science_branches_mnisw=["Physics"],
        science_branches_oecd=["Physical sciences"],
    )


def test_generate_metadata_package(temp_workspace, sample_project, sample_metadata):
    service = PackagingService(temp_workspace)
    pkg_path = service.generate_metadata_package(
        sample_project, sample_metadata, "test_pkg"
    )

    assert pkg_path.exists()
    assert pkg_path.suffix == ".zip"

    with zipfile.ZipFile(pkg_path, "r") as zf:
        file_list = zf.namelist()

        # Check metadata
        assert "metadata.yaml" in file_list
        assert "metadata.json" in file_list

        # Check docs
        assert "README.md" in file_list
        assert "LICENSE" in file_list

        # Check exclusions (IMPORTANT)
        assert "data.csv" not in file_list
        assert "subdir/notes.txt" not in file_list
        assert "notes.txt" not in file_list

        # Verify content of metadata.yaml
        with zf.open("metadata.yaml") as f:
            content = yaml.safe_load(f)
            assert content["title"] == "Test Project"


def test_validation_logic(temp_workspace, sample_metadata):
    service = PackagingService(temp_workspace)

    # Valid metadata
    assert len(service.validate_for_rodbuk(sample_metadata)) == 0

    # Invalid metadata
    invalid_metadata = Metadata(title="Short")
    errors = service.validate_for_rodbuk(invalid_metadata)
    assert len(errors) > 0
    assert any("author" in e.lower() for e in errors)
