import json
import re
import yaml
import logging
from pathlib import Path
from typing import Tuple, Optional, Any
from opendata.models import Metadata, AIAnalysis
from opendata.i18n.translator import _
from opendata.ai.telemetry import AITelemetry

logger = logging.getLogger("opendata.agents.parsing")


def extract_metadata_from_ai_response(
    response_text: str, current_metadata: Metadata
) -> Tuple[str, Optional[AIAnalysis], Metadata]:
    """
    Extract METADATA JSON from AI response and merge into current_metadata.
    Handles both legacy and new (ANALYSIS + METADATA) structures.
    Returns: (clean_text_for_chat, ai_analysis_object, updated_metadata_object)
    """
    # 0. Extract Telemetry ID if present
    interaction_id = AITelemetry.extract_id(response_text)
    if interaction_id:
        logger.info(f"Processing AI Response ID: {interaction_id}")
        response_text = AITelemetry.strip_id_tag(response_text)

    clean_text = response_text
    current_analysis = None
    updated_metadata = current_metadata

    def save_failed_response(text: str, error: str):
        """Helper to collect problematic AI responses for test development."""
        try:
            from datetime import datetime
            import os

            # Use workspace from metadata if available, else fallback
            ws_path = Path.home() / ".opendata_tool"
            debug_dir = ws_path / "debug" / "failed_responses"
            debug_dir.mkdir(parents=True, exist_ok=True)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_id = interaction_id or "no_id"
            filename = f"failed_{ts}_{safe_id}.txt"

            with open(debug_dir / filename, "w", encoding="utf-8") as f:
                f.write(f"ERROR: {error}\n\nRAW RESPONSE:\n{text}")
            logger.info(f"Saved failed AI response to {debug_dir / filename}")
        except Exception as e:
            logger.error(f"Failed to save debug response: {e}")

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

        # Determine if we are dealing with JSON or YAML
        # Try to extract JSON object even if AI prepends explanatory text
        # First check for explicit markers, then try to find JSON object in content
        is_json = json_section.startswith("{") or json_section.startswith("```json")
        
        # If not obviously JSON but contains JSON-like content, try to extract it
        if not is_json and "{" in json_section and "}" in json_section:
            # Check if it looks like JSON (has quotes around keys)
            if re.search(r'"[^"]+"\s*:', json_section):
                is_json = True

        if is_json:
            json_section = re.sub(r"^```json\s*", "", json_section)
            json_section = re.sub(r"\s*```$", "", json_section)

            start = json_section.find("{")
            if start == -1:
                return (
                    clean_text if clean_text else response_text,
                    None,
                    updated_metadata,
                )

            # Note: Simple brace counting doesn't handle braces in string literals
            # This is a known limitation. For robust JSON extraction, use YAML format instead.
            brace_count = 0
            end = -1
            in_string = False
            for i in range(start, len(json_section)):
                char = json_section[i]
                # Toggle string state (ignoring escaped quotes for simplicity)
                if char == '"' and (i == 0 or json_section[i-1] != '\\'):
                    in_string = not in_string
                # Only count braces outside strings
                if not in_string:
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break

            if end == -1:
                return (
                    clean_text if clean_text else response_text,
                    None,
                    updated_metadata,
                )

            json_str = json_section[start:end]
            json_str = re.sub(r"\bNone\b", "null", json_str)
            json_str = re.sub(r"\bTrue\b", "true", json_str)
            json_str = re.sub(r"\bFalse\b", "false", json_str)

            try:
                # Basic cleanup of common AI JSON errors
                # 1. Trailing commas in arrays/objects: [1, 2,] -> [1, 2]
                json_str_clean = re.sub(r",\s*([\]}])", r"\1", json_str)
                data = json.loads(json_str_clean)
            except json.JSONDecodeError:
                # 2. Single quotes recovery
                if json_str.count("'") > json_str.count('"'):
                    try:
                        # Also apply trailing comma fix to single-quoted version
                        sq_json = json_str.replace("'", '"')
                        sq_json = re.sub(r",\s*([\]}])", r"\1", sq_json)
                        data = json.loads(sq_json)
                    except json.JSONDecodeError:
                        raise
                else:
                    raise
        else:
            # YAML Path
            yaml_content = json_section
            # Strip potential markdown blocks
            yaml_content = re.sub(r"^```(?:yaml)?\s*", "", yaml_content)
            yaml_content = re.sub(r"\s*```$", "", yaml_content)

            # QUESTION: already split off at line 70-72, yaml_content is clean
            try:
                data = yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                logger.error(f"YAML parse failed: {e}")
                return (
                    clean_text if clean_text else response_text,
                    None,
                    updated_metadata,
                )

        if not data or not isinstance(data, dict):
            return clean_text if clean_text else response_text, None, updated_metadata

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

                        # Normalization of non_compliant (AI often sends objects instead of strings)
                        if target_key == "noncompliant" and isinstance(v, list):
                            normalized_v = []
                            for item in v:
                                if isinstance(item, dict):
                                    f = item.get("field", "unknown")
                                    r = item.get("reason", "")
                                    normalized_v.append(f"{f}: {r}" if r else f)
                                else:
                                    normalized_v.append(str(item))
                            v = normalized_v

                        normalized_analysis[target_key] = v

                    current_analysis = AIAnalysis.model_validate(normalized_analysis)
            except Exception as e:
                logger.error(f"Failed to validate AIAnalysis: {e}", exc_info=True)
        else:
            updates = data

        current_dict = updated_metadata.model_dump(exclude_unset=True)
        locked = set(updated_metadata.locked_fields or [])

        updates = {k: v for k, v in updates.items() if v is not None}
        if locked:
            for key in list(updates.keys()):
                if key in locked:
                    del updates[key]

        # Normalization of Software (AI often sends objects instead of strings)
        if "software" in updates and isinstance(updates["software"], list):
            normalized_software = []
            for item in updates["software"]:
                if isinstance(item, dict):
                    name = item.get("name", "Unknown")
                    version = item.get("version")
                    normalized_software.append(f"{name} {version}" if version else name)
                else:
                    normalized_software.append(str(item))
            updates["software"] = normalized_software

        if "abstract" in updates:
            updates["abstract"] = str(updates["abstract"])
        if "description" in updates and isinstance(updates["description"], str):
            updates["description"] = [updates["description"]]
        if "keywords" in updates and isinstance(updates["keywords"], str):
            updates["keywords"] = [updates["keywords"]]

        # Kind of Data normalization (single string expected)
        if "kind_of_data" in updates:
            if isinstance(updates["kind_of_data"], list):
                updates["kind_of_data"] = (
                    str(updates["kind_of_data"][0]) if updates["kind_of_data"] else None
                )
            else:
                updates["kind_of_data"] = (
                    str(updates["kind_of_data"]) if updates["kind_of_data"] else None
                )

        # Contacts normalization
        if "contacts" in updates and isinstance(updates["contacts"], list):
            processed_contacts = []
            for contact in updates["contacts"]:
                if isinstance(contact, dict):
                    # Map 'name' to 'person_to_contact' if missing
                    if "name" in contact and "person_to_contact" not in contact:
                        contact["person_to_contact"] = contact.pop("name")

                    if "person_to_contact" in contact and "email" not in contact:
                        contact["email"] = "missing@example.com"

                    # Handle multiple affiliations (model expects single string)
                    if "affiliations" in contact and isinstance(
                        contact["affiliations"], list
                    ):
                        contact["affiliation"] = ", ".join(contact.pop("affiliations"))
                    elif "affiliation" in contact and isinstance(
                        contact["affiliation"], list
                    ):
                        contact["affiliation"] = ", ".join(contact["affiliation"])

                    processed_contacts.append(contact)
            updates["contacts"] = processed_contacts
        elif "contact_email" in updates and updates["contact_email"]:
            # Handle flat contact_email field from AI
            email = updates.pop("contact_email")
            name = updates.pop("contact_name", "Primary Contact")
            updates["contacts"] = [{"person_to_contact": name, "email": email}]

        # Related publications normalization
        if "related_publications" in updates and isinstance(
            updates["related_publications"], list
        ):
            processed_pubs = []
            for pub in updates["related_publications"]:
                if isinstance(pub, dict) and pub.get("title"):
                    if not pub.get("relation_type"):
                        pub["relation_type"] = "isSupplementTo"

                    # Handle authors as list (model expects string)
                    if "authors" in pub and isinstance(pub["authors"], list):
                        pub["authors"] = ", ".join(pub["authors"])

                    processed_pubs.append(pub)
            updates["related_publications"] = processed_pubs

        # Authors normalization
        if "authors" in updates and isinstance(updates["authors"], list):
            processed_authors = []
            for author in updates["authors"]:
                if isinstance(author, dict):
                    if author.get("identifier") and not author.get("identifier_scheme"):
                        author["identifier_scheme"] = "ORCID"
                    # Handle ORCID in 'orcid' field instead of 'identifier'
                    if author.get("orcid") and not author.get("identifier"):
                        author["identifier"] = author.pop("orcid")
                        author["identifier_scheme"] = "ORCID"

                    # Handle multiple affiliations (model expects single string)
                    if "affiliations" in author and isinstance(
                        author["affiliations"], list
                    ):
                        author["affiliation"] = ", ".join(author.pop("affiliations"))
                    elif "affiliation" in author and isinstance(
                        author["affiliation"], list
                    ):
                        author["affiliation"] = ", ".join(author["affiliation"])

                    processed_authors.append(author)
                elif isinstance(author, str):
                    processed_authors.append({"name": author})
            updates["authors"] = processed_authors

        # Alternative titles mapping
        if "short_title" in updates and updates["short_title"]:
            if "alternative_titles" not in updates:
                updates["alternative_titles"] = []
            if updates["short_title"] not in updates["alternative_titles"]:
                updates["alternative_titles"].append(updates.pop("short_title"))

        # Funding normalization (handle grant_number vs grantnumber and string entries)
        if "funding" in updates and isinstance(updates["funding"], list):
            processed_funding = []
            for fund in updates["funding"]:
                if isinstance(fund, dict):
                    # Create a new dict to avoid modifying the original in-place if needed
                    new_fund = dict(fund)
                    if "grant_number" in new_fund and "grantnumber" not in new_fund:
                        new_fund["grantnumber"] = new_fund.pop("grant_number")
                    processed_funding.append(new_fund)
                elif isinstance(fund, str):
                    # If AI sends a string, wrap it in a dict
                    processed_funding.append({"agency": fund, "grantnumber": ""})
            updates["funding"] = processed_funding

        # Contributors mapping (move to notes if field doesn't exist in model)
        if "contributors" in updates and isinstance(updates["contributors"], list):
            contrib_str = "Contributors: " + ", ".join(
                [str(c) for c in updates["contributors"]]
            )
            if "notes" not in updates or not updates["notes"]:
                updates["notes"] = contrib_str
            elif contrib_str not in updates["notes"]:
                updates["notes"] = str(updates["notes"]) + "\n\n" + contrib_str
            del updates["contributors"]

        # Merge strategy: avoid overwriting rich data with placeholders or empty values
        for key, value in updates.items():
            if value is None or value == "":
                continue

            # If we have a long string (like abstract) and AI sends a very short one,
            # it might be a placeholder or a mistake.
            current_val = getattr(updated_metadata, key, None)
            if isinstance(value, str) and isinstance(current_val, str):
                if len(current_val) > 100 and len(value) < 50 and "..." in value:
                    logger.warning(
                        f"Ignoring suspicious update for {key}: '{value}' seems like a placeholder."
                    )
                    continue

            current_dict[key] = value

        try:
            updated_metadata = Metadata.model_validate(current_dict)
        except Exception as e:
            save_failed_response(response_text, f"Metadata validation failed: {e}")
            raise

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
        # Filter out 'error' and other non-metadata keys that might come from AI error bodies
        changed_fields = [
            f for f in updates.keys() if f.lower() not in ["error", "status", "message"]
        ]
        if changed_fields:
            clean_text = "✅ **Metadata updated.**\n\nModified fields:\n" + "\n".join(
                [f"- {f.replace('_', ' ').title()}" for f in changed_fields]
            )
        else:
            if "error" in updates:
                clean_text = f"❌ **AI Error:** {updates['error']}"
            else:
                clean_text = "ℹ️ No metadata changes detected in the response."

    return (
        clean_text,
        current_analysis,
        updated_metadata,
    )
