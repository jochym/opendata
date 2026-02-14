import pytest
from opendata.agents.parsing import extract_metadata_from_ai_response
from opendata.models import Metadata, PersonOrOrg, Contact


def test_parsing_normalization_authors():
    """Test that author strings are converted to PersonOrOrg objects."""
    current = Metadata()
    ai_input = """
METADATA:
{
  "authors": ["Jochym, Paweł", {"name": "Kowalski, Jan", "identifier": "0000-0001-2345-6789"}]
}
"""
    _, _, metadata = extract_metadata_from_ai_response(ai_input, current)

    assert len(metadata.authors) == 2
    assert isinstance(metadata.authors[0], PersonOrOrg)
    assert metadata.authors[0].name == "Jochym, Paweł"

    assert isinstance(metadata.authors[1], PersonOrOrg)
    assert metadata.authors[1].name == "Kowalski, Jan"
    assert metadata.authors[1].identifier == "0000-0001-2345-6789"
    # Check auto-assigned scheme
    assert metadata.authors[1].identifier_scheme == "ORCID"


def test_parsing_normalization_contacts():
    """Test that contact dictionaries are normalized."""
    current = Metadata()
    ai_input = """
METADATA:
{
  "contacts": [
    {"name": "Admin User", "email": "admin@example.com"},
    {"person_to_contact": "Support Team"} 
  ]
}
"""
    _, _, metadata = extract_metadata_from_ai_response(ai_input, current)

    assert len(metadata.contacts) == 2
    # "name" should be mapped to "person_to_contact"
    assert metadata.contacts[0].person_to_contact == "Admin User"

    # Missing email should be filled with placeholder
    assert metadata.contacts[1].person_to_contact == "Support Team"
    assert metadata.contacts[1].email == "missing@example.com"


def test_parsing_locked_fields():
    """Test that locked fields are NOT updated by AI."""
    current = Metadata(title="Original Title", locked_fields=["title"])
    ai_input = """
METADATA:
{
  "title": "AI Generated Title",
  "keywords": ["new"]
}
"""
    _, _, metadata = extract_metadata_from_ai_response(ai_input, current)

    assert metadata.title == "Original Title"  # Should NOT change
    assert metadata.keywords == ["new"]  # Should change


def test_parsing_edge_cases():
    """Test various parsing edge cases."""
    current = Metadata()

    # 1. Empty response
    msg, _, _ = extract_metadata_from_ai_response("", current)
    assert "Error" in msg or "Received empty response" in msg

    # 2. No METADATA tag
    msg, _, meta = extract_metadata_from_ai_response("Just some text", current)
    assert meta == current

    # 3. JSON with single quotes (heuristic check)
    ai_input = "METADATA:\n{'title': 'Single Quote Title'}"
    _, _, meta = extract_metadata_from_ai_response(ai_input, current)
    assert meta.title == "Single Quote Title"


def test_parsing_nested_braces():
    """Test JSON extraction with nested braces in strings."""
    current = Metadata()
    ai_input = """
METADATA:
{
  "title": "A study of {111} planes",
  "keywords": ["crystallography"]
}
"""
    _, _, meta = extract_metadata_from_ai_response(ai_input, current)
    assert meta.title == "A study of {111} planes"
    assert meta.keywords == ["crystallography"]
