import pytest
from opendata.agents.parsing import extract_metadata_from_ai_response
from opendata.models import Metadata


def test_funding_normalization_string():
    ai_response = """
METADATA:
{
  "METADATA": {
    "funding": [
      "National Science Centre (NCN, Poland) UMO-2014/13/B/ST3/04393"
    ]
  }
}
"""
    current_metadata = Metadata()
    clean_msg, analysis, updated_metadata = extract_metadata_from_ai_response(
        ai_response, current_metadata
    )

    assert len(updated_metadata.funding) == 1
    assert (
        updated_metadata.funding[0]["agency"]
        == "National Science Centre (NCN, Poland) UMO-2014/13/B/ST3/04393"
    )


def test_contributors_mapping_to_notes():
    ai_response = """
METADATA:
{
  "METADATA": {
    "contributors": [
      "Parlinski, Krzysztof",
      "Piekarz, Przemysław"
    ]
  }
}
"""
    current_metadata = Metadata()
    clean_msg, analysis, updated_metadata = extract_metadata_from_ai_response(
        ai_response, current_metadata
    )

    assert (
        "Contributors: Parlinski, Krzysztof, Piekarz, Przemysław"
        in updated_metadata.notes
    )


def test_non_compliant_dict_normalization():
    ai_response = """
METADATA:
{
  "ANALYSIS": {
    "summary": "Test",
    "non_compliant": [
      {"field": "license", "reason": "Use 4.0"}
    ]
  }
}
"""
    current_metadata = Metadata()
    clean_msg, analysis, updated_metadata = extract_metadata_from_ai_response(
        ai_response, current_metadata
    )

    assert analysis is not None
    assert "license: Use 4.0" in analysis.non_compliant


def test_related_publications_authors_list():
    ai_response = """
METADATA:
{
  "METADATA": {
    "related_publications": [
      {
        "title": "Test Paper",
        "authors": ["Author A", "Author B"],
        "relation_type": "isSupplementTo"
      }
    ]
  }
}
"""
    current_metadata = Metadata()
    clean_msg, analysis, updated_metadata = extract_metadata_from_ai_response(
        ai_response, current_metadata
    )

    assert updated_metadata.related_publications[0].authors == "Author A, Author B"
