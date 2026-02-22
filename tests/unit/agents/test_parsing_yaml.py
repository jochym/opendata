import pytest
from opendata.agents.parsing import extract_metadata_from_ai_response
from opendata.models import Metadata


def test_parsing_yaml_basic():
    """
    RED: Test should fail because current parser expects JSON (braces)
    and uses json.loads.
    """
    current = Metadata()
    ai_response = """
METADATA:
title: YAML Title
authors:
  - name: Jochym, Paweł T.
    affiliation: IFJ PAN
"""
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)

    assert updated.title == "YAML Title"
    assert len(updated.authors) == 1
    assert updated.authors[0].name == "Jochym, Paweł T."


def test_parsing_yaml_with_analysis():
    """
    RED: Test for nested YAML structure (ANALYSIS + METADATA).
    """
    current = Metadata()
    ai_response = """
METADATA:
ANALYSIS:
  summary: YAML analysis works.
  missing_fields: []
METADATA:
  title: Nested YAML Title
"""
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)

    assert updated.title == "Nested YAML Title"
    assert analysis is not None
    assert analysis.summary == "YAML analysis works."
