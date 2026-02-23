from opendata.agents.parsing import extract_metadata_from_ai_response
from opendata.models import Metadata

def test_parsing_yaml_basic():
    """
    Test behavior: Parser should correctly parse simple YAML metadata.
    """
    current = Metadata()
    ai_response = """METADATA:
title: YAML Title
authors:
  - name: Jochym, Paweł T.
    affiliation: IFJ PAN"""
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)

    assert updated.title == "YAML Title"
    assert len(updated.authors) == 1
    assert updated.authors[0].name == "Jochym, Paweł T."

def test_parsing_yaml_with_analysis():
    """
    Test behavior: Parser should correctly parse YAML with ANALYSIS and METADATA sections.
    """
    current = Metadata()
    ai_response = """METADATA:
ANALYSIS:
  summary: YAML analysis works.
  missing_fields: []
METADATA:
  title: Nested YAML Title"""
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)

    assert updated.title == "Nested YAML Title"
    assert analysis is not None
    assert analysis.summary == "YAML analysis works."

def test_parsing_yaml_with_question_section():
    """
    Test behavior: Parser should correctly handle QUESTION: section after METADATA.
    """
    current = Metadata()
    ai_response = """METADATA:
title: Title with Question
keywords: [test]
QUESTION: Is this metadata correct?"""
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)
    
    assert updated.title == "Title with Question"
    assert updated.keywords == ["test"]
    assert "Is this metadata correct?" in msg

def test_parsing_handles_metadata_null():
    """
    Test behavior: Parser should handle METADATA: null gracefully.
    Addresses low-confidence Copilot comment about AttributeError.
    """
    current = Metadata()
    ai_response = """METADATA:
METADATA: null"""
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)
    
    assert msg is not None
    assert updated is not None
