import json
from opendata.agents.parsing import extract_metadata_from_ai_response
from opendata.models import Metadata


def test_extract_metadata_clean_json():
    current = Metadata(title="Old Title")
    ai_input = """
METADATA:
{
  "title": "New Title",
  "keywords": ["physics", "simulation"]
}
"""
    msg, analysis, metadata = extract_metadata_from_ai_response(ai_input, current)
    assert metadata.title == "New Title"
    assert metadata.keywords == ["physics", "simulation"]
    assert "✅ **Metadata updated.**" in msg


def test_extract_metadata_with_text():
    current = Metadata(title="Old Title")
    ai_input = """
I have analyzed the project. Here is the updated metadata:

METADATA:
{
  "title": "Analyzed Title"
}

I also found some missing fields.
"""
    msg, analysis, metadata = extract_metadata_from_ai_response(ai_input, current)
    assert metadata.title == "Analyzed Title"


def test_extract_metadata_markdown_json():
    current = Metadata()
    ai_input = """
METADATA:
```json
{
  "title": "Markdown Title"
}
```
"""
    msg, analysis, metadata = extract_metadata_from_ai_response(ai_input, current)
    assert metadata.title == "Markdown Title"


def test_extract_metadata_with_analysis():
    current = Metadata()
    ai_input = """
METADATA:
{
  "ANALYSIS": {
    "summary": "Project looks good.",
    "missing_fields": ["license"]
  },
  "METADATA": {
    "title": "Analysis Title"
  }
}
"""
    msg, analysis, metadata = extract_metadata_from_ai_response(ai_input, current)
    assert metadata.title == "Analysis Title"
    assert analysis is not None
    assert analysis.summary == "Project looks good."
    assert "license" in analysis.missing_fields


def test_extract_metadata_malformed_json_recovery():
    current = Metadata(title="Old")
    ai_input = """
METADATA:
{
  'title': 'Single Quotes Title'
}
"""
    msg, analysis, metadata = extract_metadata_from_ai_response(ai_input, current)
    assert metadata.title == "Single Quotes Title"


def test_extract_metadata_prose_only_skips_parsing():
    """Prose-only guard: when METADATA section contains only text, skip parsing."""
    current = Metadata(title="Old Title")
    ai_input = """
I've analyzed your project. The files look good for packaging.
You have a nice mix of data files and scripts.

METADATA:
This is just explanatory text without any structured data.
The project appears to be a physics simulation with VASP.
I recommend including the OUTCAR files and the analysis scripts.
"""
    msg, analysis, metadata = extract_metadata_from_ai_response(ai_input, current)
    assert metadata.title == "Old Title"
    assert analysis is None
    assert "explanatory text" in msg
