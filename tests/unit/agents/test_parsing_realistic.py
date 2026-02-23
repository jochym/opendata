import pytest
import yaml
from pathlib import Path
from opendata.agents.parsing import extract_metadata_from_ai_response
from opendata.models import Metadata, PersonOrOrg


@pytest.fixture
def realistic_metadata():
    fixture_path = (
        Path(__file__).parent.parent.parent / "fixtures" / "realistic_metadata.yaml"
    )
    with open(fixture_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["projects"]


def test_parsing_3c_sic_full_response(realistic_metadata):
    """
    Test behavior: Parser should correctly extract complex author data,
    affiliations, and funding from a structured AI response.

    This tests CORRECT behavior (mapping nested structures, ORCID normalization).
    """
    expected = realistic_metadata["3C-SiC"]
    current = Metadata()

    # Simulate a realistic AI response for 3C-SiC in YAML format
    # Use simplified abstract to avoid YAML escape issues with LaTeX
    ai_response = f"""
I have analyzed the project. Here is the updated metadata for RODBUK:

METADATA:
ANALYSIS:
  summary: "Project 3C-SiC analysis complete."
  missing_fields: []
  non_compliant: []
METADATA:
  title: "{expected["title"]}"
  authors:
    - name: "Jochym, Paweł T."
      affiliations:
        - "Institute of Nuclear Physics, Polish Academy of Sciences, Krakow, Poland"
      orcid: "0000-0003-0427-7333"
    - name: "Łażewski, Jan"
      affiliation: "Institute of Nuclear Physics, Polish Academy of Sciences, Krakow, Poland"
      identifier: "0000-0002-7585-8875"
      identifier_scheme: "ORCID"
  contacts:
    - name: "Paweł T. Jochym"
      email: "pawel.jochym@ifj.edu.pl"
      affiliation: "IFJ PAN"
  abstract: "We present a first-principles study of the lattice thermal conductivity of cubic silicon carbide (3C-SiC) calculated via the solution of the Boltzmann transport equation (BTE)."
  keywords:
    - "{expected["keywords"][0]}"
    - "{expected["keywords"][1]}"
  funding:
    - agency: "National Science Centre (NCN, Poland)"
      grant_number: "UMO-2014/13/B/ST3/04393"
  software:
    - "VASP"
    - "Alamode"
    - "Phono3Py"
"""

    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)

    # Assertions for CORRECT behavior
    assert updated.title == expected["title"]
    assert len(updated.authors) == 2

    # Test ORCID normalization (from 'orcid' field to 'identifier')
    assert updated.authors[0].identifier == "0000-0003-0427-7333"
    assert updated.authors[0].identifier_scheme == "ORCID"

    # Test affiliation normalization (list to string)
    assert "Krakow, Poland" in updated.authors[0].affiliation

    # Test Contact normalization ('name' to 'person_to_contact')
    assert updated.contacts[0].person_to_contact == "Paweł T. Jochym"

    # Test Funding normalization
    assert updated.funding[0]["agency"] == "National Science Centre (NCN, Poland)"
    assert updated.funding[0]["grantnumber"] == "UMO-2014/13/B/ST3/04393"


def test_parsing_fesi_author_list_and_trackchanges(realistic_metadata):
    """
    Test behavior: Parser should handle long author lists and
    be resistant to 'trackchanges' noise if AI accidentally includes it.
    """
    expected = realistic_metadata["FeSi"]
    current = Metadata()

    # Simulate AI response with many authors and some 'noise' in YAML format
    ai_response = """
METADATA:
title: "Ab initio study of the anharmonic properties and thermal conductivity in beta-FeSi2"
authors:
  - "Pastukh, Svitlana"
  - "Sternik, Małgorzata"
  - "Jochym, Paweł T."
  - "Łażewski, Jan"
  - "Ptok, Andrzej"
  - "Stankov, Svetoslav"
  - "Piekarz, Przemysław"
notes: "Extracted from LaTeX source with \\\\trackchange{old}{new}{color} markers."
"""
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)

    assert len(updated.authors) == 7
    assert all(isinstance(a, PersonOrOrg) for a in updated.authors)
    assert updated.authors[0].name == "Pastukh, Svitlana"
    assert "trackchange" in updated.notes


def test_parsing_placeholder_protection():
    """
    Test behavior: Parser MUST NOT overwrite rich existing data with AI placeholders.
    """
    rich_abstract = (
        "This is a very long and detailed abstract that took a lot of work to extract. "
        "It contains comprehensive information about the research methodology, results, and conclusions. "
        "The abstract exceeds 100 characters to trigger the placeholder protection mechanism."
    )
    current = Metadata(abstract=rich_abstract)

    # AI sends a placeholder response in YAML format
    ai_response = """
METADATA:
abstract: "Abstract remains the same..."
"""
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)

    # Should PROTECT the rich abstract
    assert updated.abstract == rich_abstract


def test_parsing_yaml_robustness():
    """
    Test behavior: Parser should handle YAML without errors.
    YAML is naturally more robust than JSON (no trailing comma issues).
    """
    current = Metadata()
    ai_response = """
METADATA:
title: Single Quote Title
keywords:
  - physics
  - anharmonicity
"""
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)
    assert updated.title == "Single Quote Title"
    assert updated.keywords == ["physics", "anharmonicity"]


def test_parsing_locked_fields_protection():
    """
    Test behavior: Fields in 'locked_fields' MUST NOT be updated by AI.
    """
    current = Metadata(title="User Title", locked_fields=["title"])
    ai_response = """
METADATA:
title: "AI Title"
keywords:
  - "new"
"""
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)
    assert updated.title == "User Title"
    assert updated.keywords == ["new"]
