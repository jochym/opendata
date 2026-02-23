from opendata.agents.parsing import extract_metadata_from_ai_response
from opendata.models import Metadata

def test_parsing_yaml_basic():
    """Test behavior: Parser should correctly parse simple YAML metadata."""
    current = Metadata()
    ai_response = "METADATA:\ntitle: YAML Title\nauthors:\n  - name: Jochym, Paweł T.\n    affiliation: IFJ PAN"
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)
    assert updated.title == "YAML Title"

def test_parsing_yaml_with_analysis():
    """Test behavior: Parser should correctly parse YAML with ANALYSIS and METADATA."""
    current = Metadata()
    # Use a single YAML block with keys at the same level
    ai_response = "METADATA:\nANALYSIS:\n  summary: YAML analysis works.\n  missing_fields: []\nMETADATA:\n  title: Nested YAML Title"
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)
    assert updated.title == "Nested YAML Title"
    assert analysis.summary == "YAML analysis works."

def test_parsing_yaml_with_question_section():
    """Test behavior: Parser should correctly handle QUESTION: section after METADATA."""
    current = Metadata()
    ai_response = "METADATA:\ntitle: Title with Question\nkeywords: [test]\nQUESTION: Is this metadata correct?"
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)
    assert updated.title == "Title with Question"
    assert "Is this metadata correct?" in msg

def test_parsing_handles_metadata_null():
    """Test behavior: Parser should handle METADATA: null gracefully."""
    current = Metadata()
    ai_response = "METADATA:\nMETADATA: null"
    msg, analysis, updated = extract_metadata_from_ai_response(ai_response, current)
    assert msg is not None
