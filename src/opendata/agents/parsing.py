import json
import logging
import re

from opendata.i18n.translator import _
from opendata.models import AIAnalysis, Metadata

logger = logging.getLogger("opendata.agents.parsing")


def extract_metadata_from_ai_response(
    response_text: str, current_metadata: Metadata
) -> tuple[str, AIAnalysis | None, Metadata]:
    """
    Extract METADATA JSON from AI response and merge into current_metadata.
    Handles both legacy and new (ANALYSIS + METADATA) structures.
    Returns: (clean_text_for_chat, ai_analysis_object, updated_metadata_object)
    """
    clean_text = response_text
    current_analysis = None
    updated_metadata = current_metadata

    if "METADATA:" not in response_text:
        # Check if the response is an error message
        if response_text.startswith("AI Error:") or response_text.startswith("❌"):
            return response_text, None, updated_metadata
        if not response_text.strip():
            return (
                "❌ **Error:** Received empty response from AI.",
                None,
                updated_metadata,
            )

        return clean_text, None, updated_metadata

    try:
        parts = response_text.split("METADATA:", 1)
        after_metadata = parts[1]

        if "QUESTION:" in after_metadata:
            json_section, question_section = after_metadata.split("QUESTION:", 1)
            clean_text = question_section.strip()
        else:
            json_section = after_metadata
            clean_text = ""

        json_section = json_section.strip()
        json_section = re.sub(r"^```json\s*", "", json_section)
        json_section = re.sub(r"\s*```$", "", json_section)

        start = json_section.find("{")
        if start == -1:
            return clean_text if clean_text else response_text, None, updated_metadata

        brace_count = 0
        end = -1
        for i in range(start, len(json_section)):
            if json_section[i] == "{":
                brace_count += 1
            elif json_section[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break

        if end == -1:
            return clean_text if clean_text else response_text, None, updated_metadata

        json_str = json_section[start:end]
        json_str = re.sub(r"\bNone\b", "null", json_str)
        json_str = re.sub(r"\bTrue\b", "true", json_str)
        json_str = re.sub(r"\bFalse\b", "false", json_str)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            if json_str.count("'") > json_str.count('"'):
                data = json.loads(json_str.replace("'", '"'))
            else:
                raise

        if ("METADATA" in data) or ("ANALYSIS" in data):
            updates = data.get("METADATA", {})
            try:
                analysis_data = data.get("ANALYSIS")
                if analysis_data:
                    # Normalize keys for AIAnalysis model aliases (missing_fields -> missingfields)
                    normalized_analysis = {}
                    mapping = {
                        "missing_fields": "missingfields",
                        "non_compliant": "noncompliant",
                        "conflicting_data": "conflictingdata",
                        "file_suggestions": "filesuggestions",
                    }
                    for k, v in analysis_data.items():
                        target_key = mapping.get(k, k)
                        normalized_analysis[target_key] = v

                    current_analysis = AIAnalysis.model_validate(normalized_analysis)
            except Exception as e:
                print(f"[ERROR] Failed to validate AIAnalysis: {e}")
        else:
            updates = data

        current_dict = updated_metadata.model_dump(exclude_unset=True)
        locked = set(updated_metadata.locked_fields or [])

        updates = {k: v for k, v in updates.items() if v is not None}
        if locked:
            for key in list(updates.keys()):
                if key in locked:
                    del updates[key]

        if "abstract" in updates:
            updates["abstract"] = str(updates["abstract"])
        if "description" in updates and isinstance(updates["description"], str):
            updates["description"] = [updates["description"]]
        if "keywords" in updates and isinstance(updates["keywords"], str):
            updates["keywords"] = [updates["keywords"]]
        if "kind_of_data" in updates and isinstance(updates["kind_of_data"], list):
            updates["kind_of_data"] = (
                str(updates["kind_of_data"][0]) if updates["kind_of_data"] else None
            )

        # Authors normalization
        if "authors" in updates and isinstance(updates["authors"], list):
            processed_authors = []
            for author in updates["authors"]:
                if isinstance(author, dict):
                    if author.get("identifier") and not author.get("identifier_scheme"):
                        author["identifier_scheme"] = "ORCID"
                    processed_authors.append(author)
                elif isinstance(author, str):
                    processed_authors.append({"name": author})
            updates["authors"] = processed_authors

        # Contacts normalization
        if "contacts" in updates and isinstance(updates["contacts"], list):
            processed_contacts = []
            for contact in updates["contacts"]:
                if isinstance(contact, dict):
                    if "name" in contact and "person_to_contact" not in contact:
                        contact["person_to_contact"] = contact.pop("name")
                    if "person_to_contact" in contact and "email" not in contact:
                        contact["email"] = "missing@example.com"
                    processed_contacts.append(contact)
            updates["contacts"] = processed_contacts

        # Related publications normalization
        if "related_publications" in updates and isinstance(
            updates["related_publications"], list
        ):
            updates["related_publications"] = [
                pub
                for pub in updates["related_publications"]
                if isinstance(pub, dict) and pub.get("title")
            ]

        current_dict.update(updates)
        updated_metadata = Metadata.model_validate(current_dict)

        if current_analysis:
            if current_analysis.file_suggestions:
                summary_prefix = f"💡 **AI Curator found {len(current_analysis.file_suggestions)} file suggestions!** Review them in the **Package** tab.\n\n"
            else:
                summary_prefix = ""

            msg = f"{summary_prefix}**{current_analysis.summary}**\n\n"

            # Check if all mandatory RODBUK fields are present
            mandatory = ["title", "authors", "description", "license", "keywords"]
            missing_mandatory = [
                f for f in mandatory if not getattr(updated_metadata, f, None)
            ]

            if not missing_mandatory and not current_analysis.missing_fields:
                msg += _(
                    "✅ **Metadata seems complete!** Now, please go to the **Package** tab to select which files to include. You will find AI-assisted selection tools there to help ensure reproducibility.\n\n"
                )

            if current_analysis.missing_fields:
                msg += f"⚠️ **Missing RODBUK fields:** {', '.join(current_analysis.missing_fields)}\n"
            if current_analysis.non_compliant:
                msg += f"❗ **Non-compliant data:** {', '.join(current_analysis.non_compliant)}\n"
            if current_analysis.conflicting_data:
                msg += (
                    "⚠️ **Conflicts detected!** Check the form below to resolve them.\n"
                )
            if current_analysis.questions:
                msg += "\nI've prepared a form below with specific questions to help clarify the metadata or project structure."
            return msg.strip(), current_analysis, updated_metadata

    except Exception as e:
        logger.error(f"Failed to extract metadata from AI response: {e}")
        error_msg = (
            f"❌ **Error parsing AI response:** {str(e)}\n\n"
            f"The metadata could not be updated automatically.\n\n"
            f"**Raw AI Response:**\n\n{response_text}"
        )
        return error_msg, None, updated_metadata

    # Fallback if no specific analysis object was returned
    if not clean_text or clean_text == "Thank you, I've updated the metadata.":
        changed_fields = list(updates.keys())
        if changed_fields:
            clean_text = "✅ **Metadata updated.**\n\nModified fields:\n" + "\n".join(
                [f"- {f.replace('_', ' ').title()}" for f in changed_fields]
            )
        else:
            clean_text = "ℹ️ No metadata changes detected in the response."

    return (
        clean_text,
        current_analysis,
        updated_metadata,
    )
