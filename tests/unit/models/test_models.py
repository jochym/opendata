from pathlib import Path
from opendata.models import Metadata, PersonOrOrg, Contact
import pytest


def test_metadata_validation():
    # Test valid metadata
    m = Metadata(title="Test Project")
    assert m.title == "Test Project"
    assert m.authors == []


def test_metadata_ensure_list_fields():
    # Test that string inputs for list fields are converted to lists
    m = Metadata(keywords="physics, simulation")
    assert m.keywords == ["physics", "simulation"]

    m = Metadata(keywords="physics")
    assert m.keywords == ["physics"]


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
