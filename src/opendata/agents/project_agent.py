import yaml
import json
import re
from typing import List, Optional, Dict, Any, Tuple, Callable
from pathlib import Path
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

    def clear_chat_history(self):
        """Clears the chat history and persists the change."""
        self.chat_history = []
        self.save_state()

    def clear_metadata(self):
        """Resets the metadata to a fresh state and persists the change."""
        self.current_metadata = Metadata.model_construct()
        self.save_state()

    def reset_agent_state(self):
        """Resets the agent state in memory without persisting to disk."""
        self.current_metadata = Metadata.model_construct()
        self.chat_history = []
        self.current_fingerprint = None
        self.project_id = None

    def start_analysis(
        self,
        project_dir: Path,
        progress_callback: Optional[Callable[[str], None]] = None,
        force_rescan: bool = False,
        stop_event: Optional[Any] = None,
    ) -> str:
        """Initial scan and heuristic extraction phase."""
        self.project_id = self.wm.get_project_id(project_dir)

        # Try loading existing state first, unless forced rescan
        if not force_rescan and self.load_project(project_dir):
            if progress_callback:
                progress_callback("Loaded existing project state.")

            # Update current_metadata to the loaded one explicitly to ensure UI sees it
            # (though load_project already sets self.current_metadata)

            return self.chat_history[-1][1] if self.chat_history else "Project loaded."

        # NEW PROJECT or FORCED RESCAN: Clear current state
        self.current_metadata = Metadata.model_construct()
        self.chat_history = []
        self.current_fingerprint = None

        if progress_callback:
            progress_callback(f"Scanning {project_dir}...")
        self.current_fingerprint = scan_project_lazy(
            project_dir, progress_callback=progress_callback, stop_event=stop_event
        )

        if stop_event and stop_event.is_set():
            return "Scan cancelled by user."

        # Run Heuristics
        heuristics_data = {}
        candidate_main_files = []
        from opendata.utils import walk_project_files, format_size

        total_files = self.current_fingerprint.file_count
        current_file_idx = 0
        total_size_str = format_size(self.current_fingerprint.total_size_bytes)

        for p in walk_project_files(project_dir, stop_event=stop_event):
            if stop_event and stop_event.is_set():
                break
            if p.is_file():
                current_file_idx += 1
                if progress_callback:
                    # Provide statistics in the first field, full path in second, and checking status in third
                    progress_callback(
                        f"{total_size_str} - {current_file_idx}/{total_files}",
                        str(p.relative_to(project_dir)),
                        f"Checking {p.name}...",
                    )

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
            # Use relative path for better UX and consistency
            rel_main_file = main_file.relative_to(project_dir)

            # Detect auxiliary files that will be auto-included
            aux_files = []
            root_aux_extensions = {".md", ".yaml", ".yml"}
            for p in project_dir.iterdir():
                if p.is_file() and p.suffix.lower() in root_aux_extensions:
                    if p != main_file:  # Don't list main file twice
                        aux_files.append(f"`{p.name}`")

            aux_msg = ""
            if aux_files:
                aux_msg = f" along with {', '.join(aux_files)}"

            msg += f"\n\nI found **{rel_main_file}**. This appears to be your principal publication. Shall I process its full text{aux_msg} to extract all metadata at once? (This will send these files to the AI)."
        else:
            msg += "\n\nShould I use AI to analyze the paper titles or would you like to provide an arXiv/DOI link?"

        self.chat_history.append(("agent", msg))
        self.save_state()
        return msg

    def process_user_input(
        self,
        user_text: str,
        ai_service: Any,
        skip_user_append: bool = False,
        on_update: Optional[Callable[[], None]] = None,
    ) -> str:
        """Main iterative loop with Context Persistence and Tool recognition."""
        if not skip_user_append:
            self.chat_history.append(("user", user_text))
            if on_update:
                on_update()

        # 1. EXTRACT @FILES
        extra_files = []
        at_matches = re.findall(r"@([^\s,]+)", user_text)
        if at_matches and self.current_fingerprint:
            project_dir = Path(self.current_fingerprint.root_path)
            for fname in at_matches:
                # Try finding by name in the whole project (first match)
                # or just relative to root if it contains separators
                if "/" in fname or "\\" in fname:
                    p = project_dir / fname
                    if p.exists():
                        extra_files.append(p)
                else:
                    # Look in root first
                    p = project_dir / fname
                    if p.exists():
                        extra_files.append(p)
                    else:
                        # Recursive search for the filename
                        found = list(project_dir.glob(f"**/{fname}"))
                        if found:
                            extra_files.append(found[0])

        # ZERO-TOKEN CONFIRMATION CHECK
        # We check if the last agent message was the "Deep Read" proposal and user said "Yes"
        last_agent_msg = (
            self.chat_history[-2][1]
            if len(self.chat_history) >= 2 and self.chat_history[-2][0] == "agent"
            else ""
        )
        if "Shall I process" in last_agent_msg and "full text" in last_agent_msg:
            # Check if user said "yes" (possibly with @files)
            clean_input = re.sub(r"@([^\s,]+)", "", user_text).strip().lower()
            if any(ok in clean_input for ok in ["yes", "y", "sure", "ok", "okay"]):
                # IMMEDIATE SYSTEM FEEDBACK
                file_list = []
                from opendata.utils import walk_project_files

                project_dir = Path(self.current_fingerprint.root_path)

                # Main file
                candidate_main_files = []
                for p in walk_project_files(project_dir):
                    if p.is_file() and p.suffix.lower() in [".tex", ".docx"]:
                        candidate_main_files.append(p)
                main_file = None
                if candidate_main_files:
                    main_file = sorted(
                        candidate_main_files,
                        key=lambda x: x.stat().st_size,
                        reverse=True,
                    )[0]
                    file_list.append(f"`{main_file.name}` (main)")

                # Auto-included root files
                for p in project_dir.iterdir():
                    if p.is_file() and p.suffix.lower() in {".md", ".yaml", ".yml"}:
                        # Check if it was already listed as main (unlikely for md/yaml but safe)
                        if main_file and p == main_file:
                            continue
                        file_list.append(f"`{p.name}` (auto)")

                # User-requested files
                for p in extra_files:
                    if p.name not in [f.split("`")[1] for f in file_list]:
                        file_list.append(f"`{p.name}` (user)")

                feedback = f"[System] Analyzing project using: {', '.join(file_list)}... This might take a minute."
                self.chat_history.append(("agent", feedback))
                self.save_state()
                if on_update:
                    on_update()

                return self.analyze_full_text(
                    ai_service, extra_files=extra_files, on_update=on_update
                )

        enhanced_input = user_text
        # ADD EXTRA FILES TO CONTEXT IF @ MENTIONED in standard chat
        if extra_files and self.current_fingerprint:
            extra_context = []
            from opendata.utils import FullTextReader

            project_dir = Path(self.current_fingerprint.root_path)
            for p in extra_files:
                content = FullTextReader.read_full_text(p)
                if content:
                    rel_p = (
                        p.relative_to(project_dir)
                        if p.is_relative_to(project_dir)
                        else p.name
                    )
                    extra_context.append(
                        f"--- USER-REQUESTED FILE: {rel_p} ---\n{content}"
                    )

            if extra_context:
                enhanced_input = (
                    f"{user_text}\n\n[CONTEXT FROM ATTACHED FILES]\n"
                    + "\n".join(extra_context)
                )

        # 2. TOOL RECOGNITION (arXiv/DOI/ORCID)
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

    def analyze_full_text(
        self,
        ai_service: Any,
        extra_files: Optional[List[Path]] = None,
        on_update: Optional[Callable[[], None]] = None,
    ) -> str:
        """
        Executes the One-Shot Full Text Extraction.
        """
        if not self.current_fingerprint:
            return "Error: No project context available."

        project_dir = Path(self.current_fingerprint.root_path)
        from opendata.utils import walk_project_files, FullTextReader

        # 1. Gather Auxiliary Context (README, YAML, MD from root)
        aux_content = []
        root_aux_extensions = {".md", ".yaml", ".yml"}
        for p in project_dir.iterdir():
            if p.is_file() and p.suffix.lower() in root_aux_extensions:
                # Skip the main file if it happens to be MD (rare but possible)
                content = FullTextReader.read_full_text(p)
                if content:
                    aux_content.append(f"--- AUXILIARY: {p.name} ---\n{content}")

        # Add @files if provided
        if extra_files:
            for p in extra_files:
                content = FullTextReader.read_full_text(p)
                if content:
                    rel_p = (
                        p.relative_to(project_dir)
                        if p.is_relative_to(project_dir)
                        else p.name
                    )
                    aux_content.append(f"--- USER-REQUESTED: {rel_p} ---\n{content}")

        auxiliary_context = (
            "\n\n".join(aux_content) if aux_content else "No auxiliary files found."
        )

        # 2. Identify and read the Main File
        candidate_main_files = []
        for p in walk_project_files(project_dir):
            if p.is_file() and p.suffix.lower() in [".tex", ".docx"]:
                candidate_main_files.append(p)

        if not candidate_main_files:
            return "I couldn't find the main file anymore. Let's proceed with standard chat."

        main_file = sorted(
            candidate_main_files, key=lambda x: x.stat().st_size, reverse=True
        )[0]
        rel_main_file = main_file.relative_to(project_dir)

        # 3. Read content
        full_text = FullTextReader.read_full_text(main_file)
        if len(full_text) < 100:
            return f"The file {rel_main_file} seems too empty. Please double check it."

        # 4. Construct Mega-Prompt
        prompt = self.prompt_manager.render(
            "full_text_extraction",
            {"document_text": full_text, "auxiliary_context": auxiliary_context},
        )

        # 5. Call AI (Ensure tools are enabled for search)
        ai_response = ai_service.ask_agent(prompt)

        # Wrap it to reuse the parser logic
        wrapped_response = f"METADATA:\n```json\n{ai_response}\n```\nQUESTION: I have extracted the metadata using the full text and grounded search."

        clean_msg = self._extract_metadata_from_ai_response(wrapped_response)

        final_msg = f"I've analyzed the full text of **{rel_main_file}**.\n\n"
        final_msg += f"**Title Found:** {self.current_metadata.title}\n"
        final_msg += f"**Authors:** {len(self.current_metadata.authors or [])} found.\n"
        final_msg += "\nPlease review the metadata tab to see the details. What would you like to refine?"

        self.chat_history.append(("agent", final_msg))
        self.save_state()
        if on_update:
            on_update()
        return final_msg

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

            # Handle abstract: ensure it's a string
            if "abstract" in updates:
                updates["abstract"] = str(updates["abstract"])

            # Handle description: RODBUK expects List[str], but AI might send str
            if "description" in updates and isinstance(updates["description"], str):
                updates["description"] = [updates["description"]]
                print("[DEBUG] Converted description from str to list")

            # Handle keywords: ensure it's a list
            if "keywords" in updates and isinstance(updates["keywords"], str):
                updates["keywords"] = [updates["keywords"]]
                print("[DEBUG] Converted keywords from str to list")

            # Handle kind_of_data: ensure it's a string (AI might return list)
            if "kind_of_data" in updates and isinstance(updates["kind_of_data"], list):
                if len(updates["kind_of_data"]) > 0:
                    updates["kind_of_data"] = str(updates["kind_of_data"][0])
                else:
                    updates["kind_of_data"] = None
                print("[DEBUG] Converted kind_of_data from list to str")

            # Handle authors: ensure PersonOrOrg objects
            if "authors" in updates and isinstance(updates["authors"], list):
                processed_authors = []
                for author in updates["authors"]:
                    if isinstance(author, dict):
                        # Ensure identifier_scheme is set if identifier is present
                        if author.get("identifier") and not author.get(
                            "identifier_scheme"
                        ):
                            author["identifier_scheme"] = "ORCID"
                        processed_authors.append(author)
                    elif isinstance(author, str):
                        # Convert string to PersonOrOrg dict
                        processed_authors.append({"name": author})
                updates["authors"] = processed_authors

            # Handle contacts: fix common AI mistakes with schema field names
            if "contacts" in updates and isinstance(updates["contacts"], list):
                processed_contacts = []
                for contact in updates["contacts"]:
                    if isinstance(contact, dict):
                        # AI often uses 'name' instead of 'person_to_contact'
                        if "name" in contact and "person_to_contact" not in contact:
                            contact["person_to_contact"] = contact.pop("name")

                        # Fix for Pydantic validation: if person_to_contact or email is missing,
                        # try to fill it with placeholders if it's an intermediate extraction
                        # but usually it's better to just log it.
                        # In this case, we'll ensure the keys exist if they are absolutely required
                        # for model_validate.
                        if "person_to_contact" in contact and "email" not in contact:
                            # Heuristic: sometimes AI puts email in notes or just forgets it.
                            # We'll add a dummy one if it's missing to avoid crash during extraction,
                            # but ideally the prompt should enforce it.
                            contact["email"] = "missing@example.com"

                        processed_contacts.append(contact)
                updates["contacts"] = processed_contacts

            # Handle related_publications
            if "related_publications" in updates and isinstance(
                updates["related_publications"], list
            ):
                processed_pubs = []
                for pub in updates["related_publications"]:
                    if isinstance(pub, dict) and pub.get("title"):
                        processed_pubs.append(pub)
                updates["related_publications"] = processed_pubs

            current_dict.update(updates)
            self.current_metadata = Metadata.model_validate(current_dict)
            print(
                f" [DEBUG] Metadata updated successfully. Title: {self.current_metadata.title}"
            )

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON in METADATA section: {e}")
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
