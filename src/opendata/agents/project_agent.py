import yaml
import re
import platform
import sys
import datetime
import logging
from typing import List, Optional, Dict, Any, Tuple, Callable
from pathlib import Path
from opendata.models import (
    Metadata,
    ProjectFingerprint,
    AIAnalysis,
    PersonOrOrg,
    Contact,
    FileSuggestion,
)

from opendata.extractors.base import ExtractorRegistry
from opendata.workspace import WorkspaceManager
from opendata.utils import scan_project_lazy, PromptManager, FullTextReader
from opendata.agents.parsing import extract_metadata_from_ai_response
from opendata.agents.tools import handle_external_tools

logger = logging.getLogger("opendata.agents.project_agent")


class ProjectAnalysisAgent:
    """
    Agent specialized in analyzing research directories and proposing metadata.
    Maintains the state of the 'Chat Loop' and uses external tools (arXiv, DOI, ORCID).
    """

    def __init__(self, wm: WorkspaceManager):
        self.wm = wm
        from opendata.protocols.manager import ProtocolManager

        self.pm = ProtocolManager(wm)
        self.registry = ExtractorRegistry()
        self._setup_extractors()
        self.prompt_manager = PromptManager()
        self.project_id: Optional[str] = None

        self.current_fingerprint: Optional[ProjectFingerprint] = None
        self.current_metadata = Metadata.model_construct()
        self.current_analysis: Optional[AIAnalysis] = None
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
        metadata, history, fingerprint, analysis = self.wm.load_project_state(
            self.project_id
        )

        if metadata:
            self.current_metadata = metadata
            self.chat_history = history
            self.current_fingerprint = fingerprint
            self.current_analysis = analysis
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
                self.current_analysis,
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
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
        force_rescan: bool = False,
        stop_event: Optional[Any] = None,
    ) -> str:
        """Initial scan and heuristic extraction phase."""
        self.project_id = self.wm.get_project_id(project_dir)

        if not force_rescan and self.load_project(project_dir):
            if progress_callback:
                progress_callback("Loaded existing project state.", "", "")
            return self.chat_history[-1][1] if self.chat_history else "Project loaded."

        # NEW PROJECT or FORCED RESCAN
        self.current_metadata = Metadata.model_construct()
        self.chat_history = []
        self.current_fingerprint = None

        if progress_callback:
            progress_callback(f"Scanning {project_dir}...", "", "")

        return self.refresh_inventory(project_dir, progress_callback, stop_event)

    def refresh_inventory(
        self,
        project_dir: Path,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
        stop_event: Optional[Any] = None,
    ) -> str:
        """
        Performs a fast file scan and updates the SQLite inventory without running heuristics or AI.
        """
        self.project_id = self.wm.get_project_id(project_dir)

        # Get field from metadata if exists
        field_name = (
            self.current_metadata.science_branches_mnisw[0]
            if self.current_metadata.science_branches_mnisw
            else None
        )
        effective = self.pm.resolve_effective_protocol(self.project_id, field_name)
        exclude_patterns = effective.get("exclude", [])

        # 1. Quick fingerpint update
        def wrapped_cb(msg, fpath="", spath=""):
            if progress_callback:
                progress_callback(msg, fpath, spath)

        res = scan_project_lazy(
            project_dir,
            progress_callback=wrapped_cb,
            stop_event=stop_event,
            exclude_patterns=exclude_patterns,
        )
        self.current_fingerprint, full_files = res

        if stop_event and stop_event.is_set():
            return "Scan cancelled by user."

        # 2. Update SQLite Inventory
        try:
            from opendata.storage.project_db import ProjectInventoryDB

            db = ProjectInventoryDB(self.wm.get_project_db_path(self.project_id))
            db.update_inventory(full_files)
        except Exception as e:
            print(f"[ERROR] Failed to refresh inventory in SQLite: {e}")

        # Heuristics
        heuristics_data: Dict[str, Any] = {}
        candidate_main_files = []
        from opendata.utils import walk_project_files, format_size

        total_files = self.current_fingerprint.file_count
        current_file_idx = 0
        total_size_str = format_size(self.current_fingerprint.total_size_bytes)

        for p, p_stat in walk_project_files(
            project_dir, stop_event=stop_event, exclude_patterns=exclude_patterns
        ):
            if stop_event and stop_event.is_set():
                break
            if p_stat is not None:
                current_file_idx += 1
                if progress_callback:
                    progress_callback(
                        f"{total_size_str} - {current_file_idx}/{total_files}",
                        str(p.relative_to(project_dir)),
                        f"Checking {p.name}...",
                    )

                if p.suffix.lower() in [".tex", ".docx"]:
                    candidate_main_files.append(p)

                for extractor in self.registry.get_extractors_for(p):
                    partial = extractor.extract(p)
                    for key, val in partial.model_dump(exclude_unset=True).items():
                        if val:
                            if isinstance(val, list) and key in heuristics_data:
                                for item in val:
                                    if item not in heuristics_data[key]:
                                        heuristics_data[key].append(item)
                            else:
                                heuristics_data[key] = val

        self.current_metadata = Metadata.model_construct(**heuristics_data)

        # authors/contacts normalization
        if self.current_metadata.authors:
            self.current_metadata.authors = [
                a if isinstance(a, PersonOrOrg) else PersonOrOrg(**a)
                for a in self.current_metadata.authors
            ]
        if self.current_metadata.contacts:
            self.current_metadata.contacts = [
                c if isinstance(c, Contact) else Contact(**c)
                for c in self.current_metadata.contacts
            ]

        msg = f"I've scanned {self.current_fingerprint.file_count} files in your project. "
        found_fields = list(heuristics_data.keys())
        if found_fields:
            msg += f"I automatically found some data for: {', '.join(found_fields)}. "
        else:
            msg += "I couldn't find obvious metadata files like LaTeX or BibTeX. "

        # Physics Reasoning
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

        if candidate_main_files:
            main_file = sorted(
                candidate_main_files, key=lambda x: x.stat().st_size, reverse=True
            )[0]
            rel_main_file = str(main_file.relative_to(project_dir))

            # Update fingerprint with primary file
            if self.current_fingerprint:
                self.current_fingerprint.primary_file = rel_main_file

            aux_files = []
            root_aux_extensions = {".md", ".yaml", ".yml"}
            for p in project_dir.iterdir():
                if p.is_file() and p.suffix.lower() in root_aux_extensions:
                    if p != main_file:
                        aux_files.append(f"`{p.name}`")
            aux_msg = f" along with {', '.join(aux_files)}" if aux_files else ""
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
        mode: str = "metadata",
        stop_event: Optional[Any] = None,
    ) -> str:
        """Main iterative loop with Context Persistence and Tool recognition."""
        if not skip_user_append:
            self.chat_history.append(("user", user_text))
            if on_update:
                on_update()

        if user_text.strip().lower().startswith("/bug"):
            return self._handle_bug_command(user_text)

        logger.info(f"Processing user input in mode: {mode}")

        # 1. EXTRACT @FILES AND GLOBS
        extra_files = []
        at_matches = re.findall(r"@([^\s,]+)", user_text)

        if at_matches and self.current_fingerprint:
            project_dir = Path(self.current_fingerprint.root_path)
            from opendata.utils import format_file_list

            patterns_found = []
            for fname in at_matches:
                # Check for wildcards
                if any(x in fname for x in ["*", "?", "["]):
                    found = list(project_dir.glob(fname))
                    if not found and not fname.startswith("**/"):
                        found = list(project_dir.glob(f"**/{fname}"))

                    if found:
                        file_list_str = format_file_list(found, project_dir)
                        self.chat_history.append(
                            (
                                "agent",
                                f"[System] context expanded with list of {len(found)} files matching pattern `@{fname}`:\n\n{file_list_str}",
                            )
                        )
                        patterns_found.append(fname)
                        continue

                # Standard file handling
                p = project_dir / fname
                if p.exists() and p.is_file():
                    extra_files.append(p)
                else:
                    found = list(project_dir.glob(f"**/{fname}"))
                    if found and found[0].is_file():
                        extra_files.append(found[0])

            # Remove patterns from user text so AI doesn't get confused
            for pat in patterns_found:
                user_text = user_text.replace(f"@{pat}", f"(pattern @{pat} processed)")

        # 2. ZERO-TOKEN CONFIRMATION CHECK
        last_agent_msg = (
            self.chat_history[-2][1]
            if len(self.chat_history) >= 2 and self.chat_history[-2][0] == "agent"
            else ""
        )
        if (
            last_agent_msg
            and "Shall I process" in last_agent_msg
            and "full text" in last_agent_msg
        ):
            clean_input = re.sub(r"@([^\s,]+)", "", user_text).strip().lower()
            if clean_input and any(
                ok in clean_input for ok in ["yes", "y", "sure", "ok", "okay"]
            ):
                return self.analyze_full_text(
                    ai_service, extra_files=extra_files, on_update=on_update
                )

        enhanced_input = handle_external_tools(user_text, ai_service) or user_text

        # 3. ADD EXTRA FILES TO CONTEXT
        if extra_files and self.current_fingerprint:
            extra_context = []
            read_files = []
            project_dir_to_use = Path(self.current_fingerprint.root_path)
            for p in extra_files:
                content = FullTextReader.read_full_text(p)
                if content:
                    rel_p = (
                        p.relative_to(project_dir_to_use)
                        if p.is_relative_to(project_dir_to_use)
                        else p.name
                    )
                    # Content goes to enhanced_input but NOT to visible history
                    extra_context.append(
                        f"--- USER-REQUESTED FILE: {rel_p} ---\n{content}"
                    )
                    read_files.append(f"`{rel_p}`")

            if extra_context:
                # Add a stable system message about what was actually read (visible)
                self.chat_history.append(
                    (
                        "agent",
                        f"[System] context expanded with content of: {', '.join(read_files)}",
                    )
                )
                if on_update:
                    on_update()

                enhanced_input = (
                    f"{enhanced_input}\n\n[CONTEXT FROM ATTACHED FILES]\n"
                    + "\n".join(extra_context)
                )

        # 4. CALL AI (With Tool Loop)
        max_tool_iterations = 5
        for iteration in range(max_tool_iterations):
            if stop_event and stop_event.is_set():
                abort_msg = "🛑 **Analysis cancelled by user.**"
                self.chat_history.append(("agent", abort_msg))
                self.save_state()
                if on_update:
                    on_update()
                return abort_msg

            context = self.generate_ai_prompt(mode=mode)

            # Use only a window of history for context
            history_str = "\n".join(
                [f"{role}: {m}" for role, m in self.chat_history[-15:]]
            )

            full_prompt = self.prompt_manager.render(
                "chat_wrapper",
                {
                    "history": history_str,
                    "user_input": enhanced_input,
                    "context": context,
                },
            )

            # --- STATUS UPDATE: THINKING ---
            # We assume the UI shows a spinner, but we can also log or notify if needed
            # For now, relying on the spinner is standard, but we must catch errors.

            def status_callback(msg: str):
                # Add a temporary system message to history to inform user about backoff
                self.chat_history.append(("agent", f"[System] {msg}"))
                self.save_state()
                if on_update:
                    on_update()

            try:
                ai_response = ai_service.ask_agent(
                    full_prompt, on_status=status_callback
                )
            except Exception as e:
                error_msg = f"❌ **AI Communication Error:** {str(e)}"
                logger.error(f"AI Error: {e}", exc_info=True)
                self.chat_history.append(("agent", error_msg))
                self.save_state()
                if on_update:
                    on_update()
                return error_msg

            # Check for AI errors returned as text
            if ai_response.startswith("AI Error:") or ai_response.startswith(
                "AI not authenticated"
            ):
                self.chat_history.append(("agent", f"❌ **{ai_response}**"))
                self.save_state()
                if on_update:
                    on_update()
                return ai_response

            # Ensure ai_response starts with JSON context if it looks like JSON
            if (
                ai_response.strip().startswith("{")
                and "METADATA" not in ai_response
                and "ANALYSIS" not in ai_response
            ):
                # Wrap it to satisfy the extractor
                ai_response = f"METADATA:\n{ai_response}"
            elif "METADATA:" not in ai_response and "ANALYSIS" not in ai_response:
                # Try to find a JSON block even if not labeled
                json_match = re.search(r"({.*})", ai_response, re.DOTALL)
                if json_match:
                    ai_response = f"METADATA:\n{ai_response}"

            # Check for READ_FILE command
            read_match = re.search(r"READ_FILE:\s*(.+)", ai_response)
            if read_match and self.current_fingerprint:
                file_paths_str = read_match.group(1).strip()
                requested_files = [f.strip() for f in file_paths_str.split(",")]
                project_dir_to_use = Path(self.current_fingerprint.root_path)

                tool_output = []
                visible_files = []
                for rf in requested_files:
                    p = project_dir_to_use / rf
                    if p.exists() and p.is_file():
                        content = FullTextReader.read_full_text(p)
                        tool_output.append(f"--- FILE CONTENT: {rf} ---\n{content}")
                        visible_files.append(f"`{rf}`")
                    else:
                        tool_output.append(f"--- FILE NOT FOUND: {rf} ---")
                        visible_files.append(f"`{rf}` (not found)")

                # Invisible full response for context, visible placeholder for history
                self.chat_history.append(
                    (
                        "agent",
                        f"[System] AI requested content of: {', '.join(visible_files)}",
                    )
                )

                # Enhanced input for next step contains the actual data
                enhanced_input = "[System] READ_FILE Tool Results:\n\n" + "\n\n".join(
                    tool_output
                )

                if on_update:
                    on_update()
                continue  # Next iteration of the loop

            # If no READ_FILE, finish
            wrapped_response = (
                f"METADATA:\n{ai_response}"
                if "METADATA:" not in ai_response
                else ai_response
            )

            clean_msg, analysis, metadata = extract_metadata_from_ai_response(
                wrapped_response, self.current_metadata
            )

            # --- GLOB EXPANSION FOR FILE SUGGESTIONS ---
            if analysis and analysis.file_suggestions and self.current_fingerprint:
                project_dir = Path(self.current_fingerprint.root_path)
                expanded_suggestions = []
                seen_paths = set()

                for sug in analysis.file_suggestions:
                    # Check if sug.path is a glob pattern
                    if any(x in sug.path for x in ["*", "?", "["]):
                        found = list(project_dir.glob(sug.path))
                        if not found and not sug.path.startswith("**/"):
                            found = list(project_dir.glob(f"**/{sug.path}"))

                        for p in found:
                            if p.is_file():
                                rel_p = str(p.relative_to(project_dir))
                                if rel_p not in seen_paths:
                                    expanded_suggestions.append(
                                        FileSuggestion(
                                            path=rel_p,
                                            reason=f"[Pattern match: {sug.path}] {sug.reason}",
                                        )
                                    )
                                    seen_paths.add(rel_p)
                    else:
                        if sug.path not in seen_paths:
                            expanded_suggestions.append(sug)
                            seen_paths.add(sug.path)

                analysis.file_suggestions = expanded_suggestions

            # SELECTIVE METADATA UPDATE IN CURATOR MODE
            if mode == "curator":
                logger.info(
                    "Curator mode active: allowing only data-related metadata updates."
                )
                allowed_curator_fields = {
                    "kind_of_data",
                    "software",
                    "notes",
                }

                # Create a hybrid metadata: current base + allowed updates from AI
                current_dict = self.current_metadata.model_dump()
                new_dict = metadata.model_dump()

                for field in allowed_curator_fields:
                    if field in new_dict and new_dict[field]:
                        if field == "notes" and current_dict.get("notes"):
                            # Append curator's description to existing notes if it's different
                            if new_dict.get("description"):
                                desc_str = (
                                    "\n".join(new_dict["description"])
                                    if isinstance(new_dict["description"], list)
                                    else str(new_dict["description"])
                                )
                                if desc_str not in current_dict["notes"]:
                                    current_dict["notes"] += (
                                        f"\n\n[Curator Analysis]\n{desc_str}"
                                    )
                        else:
                            current_dict[field] = new_dict[field]

                # If curator provided a description, but it's blocked, we move it to notes
                if "description" in new_dict and new_dict["description"]:
                    desc_str = (
                        "\n".join(new_dict["description"])
                        if isinstance(new_dict["description"], list)
                        else str(new_dict["description"])
                    )
                    current_notes = current_dict.get("notes") or ""
                    if desc_str not in current_notes:
                        header = "[Curator Description]"
                        if header not in current_notes:
                            current_dict["notes"] = (
                                current_notes + f"\n\n{header}\n{desc_str}"
                            ).strip()

                metadata = Metadata.model_validate(current_dict)

            else:
                # In metadata mode, all fields are updatable (respecting locked_fields inside extract_metadata)
                pass

            # Only overwrite analysis if a new one was actually produced
            if analysis:
                self.current_analysis = analysis

            self.current_metadata = metadata

            self.chat_history.append(("agent", clean_msg))
            self.save_state()
            if on_update:
                on_update()
            return clean_msg

        return "Tool loop exceeded maximum iterations."

    def analyze_full_text(
        self,
        ai_service: Any,
        extra_files: Optional[List[Path]] = None,
        on_update: Optional[Callable[[], None]] = None,
    ) -> str:
        """Executes the One-Shot Full Text Extraction."""
        if not self.current_fingerprint:
            return "Error: No project context available."

        project_dir = Path(self.current_fingerprint.root_path)
        from opendata.utils import walk_project_files

        # 1. Gather Context
        aux_content = []
        root_aux_extensions = {".md", ".yaml", ".yml"}
        for p in project_dir.iterdir():
            if p.is_file() and p.suffix.lower() in root_aux_extensions:
                content = FullTextReader.read_full_text(p)
                if content:
                    aux_content.append(f"--- AUXILIARY: {p.name} ---\n{content}")

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

        # 2. Main File
        candidate_main_files = []
        for p, p_stat in walk_project_files(project_dir):
            if p_stat is not None and p.suffix.lower() in [".tex", ".docx"]:
                candidate_main_files.append(p)

        if not candidate_main_files:
            return "I couldn't find the main file. Standard chat continued."

        main_file = sorted(
            candidate_main_files, key=lambda x: x.stat().st_size, reverse=True
        )[0]
        full_text = FullTextReader.read_full_text(main_file)

        # 3. Mega-Prompt
        prompt = self.prompt_manager.render(
            "full_text_extraction",
            {"document_text": full_text, "auxiliary_context": auxiliary_context},
        )

        ai_response = ai_service.ask_agent(prompt)
        wrapped_response = f"METADATA:\n{ai_response}"
        clean_msg, analysis, metadata = extract_metadata_from_ai_response(
            wrapped_response, self.current_metadata
        )
        self.current_analysis = analysis
        self.current_metadata = metadata

        self.chat_history.append(("agent", clean_msg))
        self.save_state()
        if on_update:
            on_update()
        return clean_msg

    def submit_analysis_answers(
        self, answers: Dict[str, Any], on_update: Optional[Callable[[], None]] = None
    ) -> str:
        """
        Updates metadata based on form answers and clears current analysis.
        Adheres to robust validation and modular update logic.
        """
        if not self.current_analysis:
            return "No active analysis to answer."

        # Prepare list of fields that should be treated as lists of objects or strings
        # 'authors' and 'contacts' are lists of Pydantic models, not simple strings
        complex_list_fields = ["authors", "contacts"]
        simple_list_fields = [
            "science_branches_oecd",
            "science_branches_mnisw",
            "keywords",
            "description",
            "software",
        ]

        current_dict = self.current_metadata.model_dump(exclude_unset=True)
        processed_answers = {}

        for k, v in answers.items():
            if not v:
                continue

            # Special handling for complex list fields - don't overwrite with strings from form
            if k in complex_list_fields:
                # If the value from the form is a string (e.g. choice),
                # we need to find the matching object or ignore if it's just a label
                if isinstance(v, str):
                    # Check if this looks like a JSON or identifier,
                    # for now we skip raw string overwrites of PersonOrOrg lists
                    continue

            # Simple list fields can take strings and convert them to single-item lists
            if k in simple_list_fields and isinstance(v, str):
                processed_answers[k] = [v]
            else:
                processed_answers[k] = v

        try:
            current_dict.update(processed_answers)
            self.current_metadata = Metadata.model_validate(current_dict)
            if self.current_analysis:
                # Surgically clear only questions and conflicts, keep file suggestions
                self.current_analysis.questions = []
                self.current_analysis.conflicting_data = []
                # If no file suggestions remain either, we can clear the whole thing
                if not self.current_analysis.file_suggestions:
                    self.current_analysis = None
        except Exception as e:
            # Re-raise with context but protect agent state
            print(f"[ERROR] Metadata validation failed during form submission: {e}")
            raise e

        human_answers = []
        for k, v in processed_answers.items():
            label = k.replace("_", " ").title()
            val_str = ", ".join(map(str, v)) if isinstance(v, list) else str(v)
            human_answers.append(f"- **{label}**: {val_str}")

        self.chat_history.append(
            ("user", f"Updated fields via form:\n\n" + "\n".join(human_answers))
        )
        msg = "Thank you! I've updated the metadata with your choices."
        self.chat_history.append(("agent", msg))
        self.save_state()

        if on_update:
            on_update()
        return msg

    def generate_ai_prompt(self, mode: str = "metadata") -> str:
        if not self.current_fingerprint:
            return "No project scanned."
        fingerprint_summary = self.current_fingerprint.model_dump_json(indent=2)
        current_data = yaml.dump(
            self.current_metadata.model_dump(exclude_unset=True), allow_unicode=True
        )

        field_name = (
            self.current_metadata.science_branches_mnisw[0]
            if self.current_metadata.science_branches_mnisw
            else None
        )
        effective = self.pm.resolve_effective_protocol(self.project_id, field_name)

        protocols_str = ""
        # Legacy prompts
        if effective.get("prompts"):
            protocols_str += "ACTIVE PROTOCOLS & USER RULES:\n" + "\n".join(
                [f"{i}. {p}" for i, p in enumerate(effective["prompts"], 1)]
            )

        # Mode-specific prompts
        mode_prompts = effective.get(
            "metadata_prompts" if mode == "metadata" else "curator_prompts", []
        )
        if mode_prompts:
            if protocols_str:
                protocols_str += "\n\n"
            protocols_str += f"SPECIFIC {mode.upper()} INSTRUCTIONS:\n" + "\n".join(
                [f"{i}. {p}" for i, p in enumerate(mode_prompts, 1)]
            )

        primary_file_info = ""
        if self.current_fingerprint and self.current_fingerprint.primary_file:
            primary_file_info = (
                f"PRIMARY PUBLICATION FILE: {self.current_fingerprint.primary_file}\n"
            )

        template = (
            "system_prompt_metadata" if mode == "metadata" else "system_prompt_curator"
        )

        return self.prompt_manager.render(
            template,
            {
                "fingerprint": fingerprint_summary,
                "metadata": current_data,
                "protocols": protocols_str,
                "primary_file": primary_file_info,
            },
        )

    def _handle_bug_command(self, user_text: str) -> str:
        """Generates a diagnostic report for debugging."""
        description = user_text[4:].strip() or "No description provided."
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f"bug_report_{timestamp}.yaml"
        report_path = self.wm.bug_reports_dir / report_name

        report_data = {
            "timestamp": timestamp,
            "user_description": description,
            "system_info": {
                "os": platform.system(),
                "os_release": platform.release(),
                "python_version": sys.version,
                "platform": platform.platform(),
            },
            "project_context": {
                "project_id": self.project_id,
                "root_path": self.current_fingerprint.root_path
                if self.current_fingerprint
                else "Unknown",
                "metadata": self.current_metadata.model_dump(exclude_unset=True),
                "fingerprint_summary": {
                    "file_count": self.current_fingerprint.file_count
                    if self.current_fingerprint
                    else 0,
                    "total_size": self.current_fingerprint.total_size_bytes
                    if self.current_fingerprint
                    else 0,
                    "extensions": self.current_fingerprint.extensions
                    if self.current_fingerprint
                    else [],
                },
            },
            "recent_history": self.chat_history[-20:] if self.chat_history else [],
        }

        with open(report_path, "w", encoding="utf-8") as f:
            yaml.dump(report_data, f, allow_unicode=True, sort_keys=False)

        msg = f"🐞 **Bug report generated!**\n\nDiagnostic data has been saved to:\n`{report_path}`\n\nPlease share this file with the developers."
        self.chat_history.append(("agent", msg))
        self.save_state()
        return msg
