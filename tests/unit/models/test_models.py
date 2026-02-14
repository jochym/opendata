from pathlib import Path
from opendata.models import Metadata, PersonOrOrg, Contact
import pytest


def test_metadata_defaults():
    """Test that mandatory defaults are set correctly."""
    m = Metadata()
    assert m.license == "CC-BY-4.0"
    assert m.languages == ["English"]
    assert m.authors == []
    assert m.keywords == []


def test_metadata_validation():
    # Test valid metadata
    m = Metadata(title="Test Project")
    assert m.title == "Test Project"
    assert m.authors == []


def test_metadata_ensure_list_fields():
    """Test the ensure_list_fields validator thoroughly."""
    # 1. Comma-separated string -> List
    m = Metadata(keywords="physics, simulation")
    assert m.keywords == ["physics", "simulation"]

    # 2. Single string -> List
    m = Metadata(keywords="physics")
    assert m.keywords == ["physics"]

    # 3. None -> Empty List
    m = Metadata(keywords=None)
    assert m.keywords == []

    # 4. String with brackets (JSON-like) -> Single item (don't split)
    # The validator logic is: if "," in v and "[" not in v: split
    # So "[physics, chemistry]" has a comma but ALSO a bracket, so it should NOT split.
    m = Metadata(keywords="[physics, chemistry]")
    assert m.keywords == ["[physics, chemistry]"]


def test_person_or_org_validation():
    p = PersonOrOrg(name="Jochym, Paweł", affiliation="IFJ PAN")
    assert p.name == "Jochym, Paweł"
    assert p.affiliation == "IFJ PAN"


def test_contact_validation():
    c = Contact(person_to_contact="Paweł Jochym", email="pawel.jochym@ifj.edu.pl")
    assert c.person_to_contact == "Paweł Jochym"
    assert c.email == "pawel.jochym@ifj.edu.pl"


def test_invalid_email():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Contact(person_to_contact="Test", email="invalid-email")


def test_ai_analysis_aliases():
    """Test that AI analysis fields map correctly from their aliases."""
    from opendata.models import AIAnalysis

    data = {
        "summary": "Test summary",
        "missingfields": ["license"],  # Alias
        "noncompliant": ["title"],  # Alias
        "filesuggestions": [],  # Alias
    }
    analysis = AIAnalysis.model_validate(data)
    assert analysis.missing_fields == ["license"]
    assert analysis.non_compliant == ["title"]


def test_kind_of_data_alias():
    """Test that kind_of_data accepts 'kindof_data' alias."""
    data = {"kindof_data": "Simulation"}
    m = Metadata.model_validate(data)
    assert m.kind_of_data == "Simulation"
