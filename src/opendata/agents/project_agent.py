from typing import List, Optional, Dict, Any, Tuple, Callable
from pathlib import Path
import yaml
import json
import re
from opendata.models import Metadata, ProjectFingerprint
from opendata.extractors.base import ExtractorRegistry, PartialMetadata
from opendata.workspace import WorkspaceManager
from opendata.utils import scan_project_lazy, PromptManager


class ProjectAnalysisAgent:
    """
    Agent specialized in analyzing research directories and proposing metadata.
    Maintains the state of the 'Chat Loop' and uses external tools (arXiv, DOI, ORCID).
    """

    def __init__(self, wm: WorkspaceManager):
        self.wm = wm
        self.registry = ExtractorRegistry()
        self._setup_extractors()
        self.prompt_manager = PromptManager()
        self.project_id: Optional[str] = None

        self.current_fingerprint: Optional[ProjectFingerprint] = None
        self.current_metadata = Metadata.model_construct()
        self.chat_history: List[Tuple[str, str]] = []  # (Role, Message)

    def _setup_extractors(self):
        from opendata.extractors.latex import LatexExtractor
        from opendata.extractors.docx import DocxExtractor
        from opendata.extractors.medical import DicomExtractor
        from opendata.extractors.citations import BibtexExtractor
        from opendata.extractors.hierarchical import Hdf5Extractor
        from opendata.extractors.physics import (
            VaspExtractor,
            LatticeDynamicsExtractor,
            ColumnarDataExtractor,
        )

        self.registry.register(LatexExtractor())
        self.registry.register(DocxExtractor())
        self.registry.register(DicomExtractor())
        self.registry.register(BibtexExtractor())
        self.registry.register(Hdf5Extractor())
        self.registry.register(VaspExtractor())
        self.registry.register(LatticeDynamicsExtractor())
        self.registry.register(ColumnarDataExtractor())

    def load_project(self, project_path: Path):
        """Loads an existing project or initializes a new one."""
        self.project_id = self.wm.get_project_id(project_path)
        metadata, history, fingerprint = self.wm.load_project_state(self.project_id)

        if metadata:
            self.current_metadata = metadata
            self.chat_history = history
            self.current_fingerprint = fingerprint
            return True
        return False

    def save_state(self):
        """Persists the current state to the workspace."""
        if self.project_id:
            self.wm.save_project_state(
                self.project_id,
                self.current_metadata,
                self.chat_history,
                self.current_fingerprint,
            )

    def start_analysis(
        self,
        project_dir: Path,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Initial scan and heuristic extraction phase."""
        self.project_id = self.wm.get_project_id(project_dir)

        # Try loading existing state first
        if self.load_project(project_dir):
            if progress_callback:
                progress_callback("Loaded existing project state.")
            return self.chat_history[-1][1] if self.chat_history else "Project loaded."

        if progress_callback:
            progress_callback(f"Scanning {project_dir}...")
        self.current_fingerprint = scan_project_lazy(
            project_dir, progress_callback=progress_callback
        )

        # Run Heuristics
        heuristics_data = {}
        candidate_main_files = []
        from opendata.utils import walk_project_files

        for p in walk_project_files(project_dir):
            if p.is_file():
                if progress_callback:
                    progress_callback(f"Checking {p.name}...")

                # Identify potential main text files (LaTeX, Docx)
                if p.suffix.lower() in [".tex", ".docx"]:
                    candidate_main_files.append(p)

                for extractor in self.registry.get_extractors_for(p):
                    partial = extractor.extract(p)
                    for key, val in partial.model_dump(exclude_unset=True).items():
                        if val:
                            if isinstance(val, list) and key in heuristics_data:
                                # Merge lists instead of overwriting
                                for item in val:
                                    if item not in heuristics_data[key]:
                                        heuristics_data[key].append(item)
                            else:
                                heuristics_data[key] = val

        self.current_metadata = Metadata.model_construct(**heuristics_data)

        msg = f"I've scanned {self.current_fingerprint.file_count} files in your project. "
        found_fields = list(heuristics_data.keys())
        if found_fields:
            msg += f"I automatically found some data for: {', '.join(found_fields)}. "
        else:
            msg += "I couldn't find obvious metadata files like LaTeX or BibTeX. "

        # Specialized Physics Reasoning
        physics_tools = []
        for s in self.current_fingerprint.structure_sample:
            s_up = s.upper()
            if any(x in s_up for x in ["INCAR", "OUTCAR", "POSCAR"]):
                if "VASP" not in physics_tools:
                    physics_tools.append("VASP")
            if "phonopy" in s.lower() and "Phonopy" not in physics_tools:
                physics_tools.append("Phonopy")
            if "alamode" in s.lower() and "ALAMODE" not in physics_tools:
                physics_tools.append("ALAMODE")

        if physics_tools:
            msg += f"I noticed you are using {', '.join(physics_tools)}. "
            msg += "This looks like a computational physics project. "

        # First approximation question
        if candidate_main_files:
            # Sort by size/name to pick the most likely "main" paper
            main_file = sorted(
                candidate_main_files, key=lambda x: x.stat().st_size, reverse=True
            )[0]
            rel_main_file = main_file.relative_to(project_dir)
            msg += f"\n\nI think **{rel_main_file}** might be the main research paper. Is it okay to use it as the primary source for a first approximation of the metadata?"
        else:
            msg += "\n\nShould I use AI to analyze the paper titles or would you like to provide an arXiv/DOI link?"

        self.chat_history.append(("agent", msg))
        self.save_state()
        return msg

    def process_user_input(
        self, user_text: str, ai_service: Any, skip_user_append: bool = False
    ) -> str:
        """Main iterative loop with Context Persistence and Tool recognition."""
        if not skip_user_append:
            self.chat_history.append(("user", user_text))

        # 1. TOOL RECOGNITION (arXiv/DOI/ORCID)
        arxiv_match = re.search(r"arxiv[:\s]*([\d\.]+)", user_text, re.IGNORECASE)
        doi_match = re.search(r"doi[:\s]*(10\.\d{4,}/[^\s]+)", user_text, re.IGNORECASE)
        orcid_match = re.search(
            r"orcid[:\s]*(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", user_text, re.IGNORECASE
        )
        orcid_search_match = re.search(
            r"orcid (?:for|of) ([^,\?\.]+)", user_text, re.IGNORECASE
        )

        enhanced_input = user_text
        if arxiv_match:
            arxiv_id = arxiv_match.group(1)
            raw_data = ai_service.fetch_arxiv_metadata(arxiv_id)
            enhanced_input = f"The user provided arXiv ID {arxiv_id}. Here is raw metadata: {raw_data}. USE THIS TO UPDATE METADATA."
        elif doi_match:
            doi_id = doi_match.group(1)
            json_data = ai_service.fetch_doi_metadata(doi_id)
            enhanced_input = f"The user provided DOI {doi_id}. Here is the metadata: {json_data}. USE THIS TO UPDATE METADATA."
        elif orcid_match:
            orcid_id = orcid_match.group(1)
            json_data = ai_service.fetch_orcid_metadata(orcid_id)
            enhanced_input = f"The user provided ORCID {orcid_id}. Here is the profile: {json_data}. UPDATE AUTHOR INFO."
        elif orcid_search_match:
            author_name = orcid_search_match.group(1).strip()
            results = ai_service.search_orcid_by_name(author_name)
            enhanced_input = f"User wants ORCID search for '{author_name}'. Top matches: {results}. ASK USER TO CONFIRM ONE."

        # 2. CONTEXT PERSISTENCE
        context = self.generate_ai_prompt()
        history_str = "\n".join(
            [f"{role}: {m}" for role, m in self.chat_history[-10:-1]]
        )

        full_prompt = self.prompt_manager.render(
            "chat_wrapper",
            {
                "history": history_str,
                "user_input": enhanced_input,
                "context": context,  # This is the system prompt rendered in generate_ai_prompt
            },
        )

        ai_response = ai_service.ask_agent(full_prompt)

        # 3. IMMEDIATE METADATA EXTRACTION FROM RESPONSE
        clean_msg = self._extract_metadata_from_ai_response(ai_response)

        self.chat_history.append(("agent", clean_msg))
        self.save_state()
        return clean_msg

    def _extract_metadata_from_ai_response(self, response_text: str) -> str:
        """
        Extract METADATA JSON from AI response and merge into current_metadata.
        Returns only the QUESTION part for display to user.
        """
        clean_text = response_text

        # Check if METADATA marker exists
        if "METADATA:" not in response_text:
            return clean_text

        try:
            # Split the response into sections
            parts = response_text.split("METADATA:", 1)
            after_metadata = parts[1]

            # Find where QUESTION starts (if it exists)
            if "QUESTION:" in after_metadata:
                json_section, question_section = after_metadata.split("QUESTION:", 1)
                clean_text = question_section.strip()
            else:
                json_section = after_metadata
                clean_text = ""

            # Extract JSON - look for the outermost braces
            # Remove optional markdown code fences
            json_section = json_section.strip()
            json_section = re.sub(r"^```json\s*", "", json_section)
            json_section = re.sub(r"\s*```$", "", json_section)

            # Find the first { and the matching closing }
            start = json_section.find("{")
            if start == -1:
                print("No JSON object found in METADATA section")
                return clean_text if clean_text else response_text

            # Count braces to find the matching closing brace
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
                print("Could not find matching closing brace in METADATA")
                return clean_text if clean_text else response_text

            json_str = json_section[start:end]
            print(f"[DEBUG] Extracted JSON ({len(json_str)} chars):")
            print(json_str)
            print("[DEBUG] End of JSON extraction")

            # Pre-process to fix common AI mistakes
            # 1. Replace Python None with JSON null
            json_str = re.sub(r"\bNone\b", "null", json_str)
            # 2. Replace Python True/False with lowercase
            json_str = re.sub(r"\bTrue\b", "true", json_str)
            json_str = re.sub(r"\bFalse\b", "false", json_str)
            # 3. Try to fix single quotes (risky, but common AI error)
            # Only if double quotes seem missing
            if json_str.count('"') < json_str.count("'") / 2:
                print(
                    "[DEBUG] Detected single quotes, attempting to convert to double quotes"
                )
                json_str = json_str.replace("'", '"')

            # Parse and merge the metadata
            try:
                updates = json.loads(json_str)
                print(f"[DEBUG] Parsed metadata keys: {list(updates.keys())}")
            except json.JSONDecodeError as json_err:
                print(f"[ERROR] JSON Parse Error: {json_err}")
                print(f"[ERROR] Error at position {json_err.pos}")
                if json_err.pos < len(json_str):
                    # Show context around the error
                    start_ctx = max(0, json_err.pos - 50)
                    end_ctx = min(len(json_str), json_err.pos + 50)
                    context = json_str[start_ctx:end_ctx]
                    print(f"[ERROR] Context around error position:")
                    print(f"[ERROR] ...{context}...")
                    print(
                        f"[ERROR] Character at error: repr={repr(json_str[json_err.pos])}"
                    )
                raise

            # Merge with existing metadata
            current_dict = self.current_metadata.model_dump(exclude_unset=True)

            # Pre-process updates to match schema expectations
            # First, remove all null values (they shouldn't override existing data)
            updates = {k: v for k, v in updates.items() if v is not None}
            print(
                f"[DEBUG] Filtered out null values, remaining keys: {list(updates.keys())}"
            )

            # Handle description: RODBUK expects List[str], but AI might send str
            if "description" in updates and isinstance(updates["description"], str):
                updates["description"] = [updates["description"]]
                print("[DEBUG] Converted description from str to list")

            # Handle keywords: ensure it's a list
            if "keywords" in updates and isinstance(updates["keywords"], str):
                updates["keywords"] = [updates["keywords"]]
                print("[DEBUG] Converted keywords from str to list")

            # Handle authors: ensure PersonOrOrg objects
            if "authors" in updates and isinstance(updates["authors"], list):
                processed_authors = []
                for author in updates["authors"]:
                    if isinstance(author, dict):
                        # Already a dict, will be validated by Pydantic
                        processed_authors.append(author)
                    elif isinstance(author, str):
                        # Convert string to PersonOrOrg dict
                        processed_authors.append({"name": author})
                updates["authors"] = processed_authors

            current_dict.update(updates)
            self.current_metadata = Metadata.model_validate(current_dict)
            print(
                f"[DEBUG] Metadata updated successfully. Title: {self.current_metadata.title}"
            )

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON in METADATA section: {e}")
            print(
                f"[ERROR] Attempted to parse: {json_str if 'json_str' in locals() else 'N/A'}"
            )
            return response_text
        except Exception as e:
            print(f"[ERROR] Failed to extract metadata from AI response: {e}")
            import traceback

            traceback.print_exc()
            return response_text

        return clean_text if clean_text else "Thank you, I've updated the metadata."

    def generate_ai_prompt(self) -> str:
        if not self.current_fingerprint:
            return "No project scanned."
        fingerprint_summary = self.current_fingerprint.model_dump_json(indent=2)

        # We explicitly include the current metadata in the prompt so the AI can see what we already have
        current_data = yaml.dump(
            self.current_metadata.model_dump(exclude_unset=True), allow_unicode=True
        )

        # Domain protocols injection (if implemented/available)
        protocols = "None active."

        return self.prompt_manager.render(
            "system_prompt",
            {
                "fingerprint": fingerprint_summary,
                "metadata": current_data,
                "protocols": protocols,
            },
        )
