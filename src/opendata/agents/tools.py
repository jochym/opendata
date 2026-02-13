import re
from typing import Any


def handle_external_tools(user_text: str, ai_service: Any) -> str | None:
    """
    Recognizes arXiv, DOI, ORCID and fetches metadata to enhance input.
    Returns enhanced_input if tool was matched, else None.
    """
    arxiv_match = re.search(r"arxiv[:\s]*([\d\.]+)", user_text, re.IGNORECASE)
    doi_match = re.search(r"doi[:\s]*(10\.\d{4,}/[^\s]+)", user_text, re.IGNORECASE)
    orcid_match = re.search(
        r"orcid[:\s]*(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", user_text, re.IGNORECASE
    )
    orcid_search_match = re.search(
        r"orcid (?:for|of) ([^,\?\.]+)", user_text, re.IGNORECASE
    )

    if arxiv_match:
        arxiv_id = arxiv_match.group(1)
        raw_data = ai_service.fetch_arxiv_metadata(arxiv_id)
        return f"The user provided arXiv ID {arxiv_id}. Here is raw metadata: {raw_data}. USE THIS TO UPDATE METADATA."
    if doi_match:
        doi_id = doi_match.group(1)
        json_data = ai_service.fetch_doi_metadata(doi_id)
        return f"The user provided DOI {doi_id}. Here is the metadata: {json_data}. USE THIS TO UPDATE METADATA."
    if orcid_match:
        orcid_id = orcid_match.group(1)
        json_data = ai_service.fetch_orcid_metadata(orcid_id)
        return f"The user provided ORCID {orcid_id}. Here is the profile: {json_data}. UPDATE AUTHOR INFO."
    if orcid_search_match:
        author_name = orcid_search_match.group(1).strip()
        results = ai_service.search_orcid_by_name(author_name)
        return f"User wants ORCID search for '{author_name}'. Top matches: {results}. ASK USER TO CONFIRM ONE."

    return None
