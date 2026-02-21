import yaml
import re
import platform
import sys
import datetime
import logging
import threading
import asyncio
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
from opendata.i18n.translator import _

from opendata.extractors.base import ExtractorRegistry
from opendata.workspace import WorkspaceManager
from opendata.utils import scan_project_lazy, PromptManager, FullTextReader, format_size
from opendata.agents.parsing import extract_metadata_from_ai_response
from opendata.agents.tools import handle_external_tools
from opendata.agents.scanner import ScannerService
from opendata.agents.persistence import ProjectStateManager
from opendata.agents.engine import AnalysisEngine


logger = logging.getLogger("opendata.agents.project_agent")


class ProjectAnalysisAgent:
    """
    Agent specialized in analyzing research directories and proposing metadata.
    Maintains the state of the 'Chat Loop' and uses external tools (arXiv, DOI, ORCID).
    """

    def __init__(
        self,
        wm: WorkspaceManager,
        pm: Any | None = None,
        registry: ExtractorRegistry | None = None,
        prompt_manager: PromptManager | None = None,
    ):
        self.wm = wm
        from opendata.protocols.manager import ProtocolManager

        self.pm = pm or ProtocolManager(wm)
        self.registry = registry or ExtractorRegistry()
        if registry is None:
            self._setup_extractors()
        self.prompt_manager = prompt_manager or PromptManager()
        self.project_id: Optional[str] = None

        self.current_fingerprint: Optional[ProjectFingerprint] = None
        self.current_metadata = Metadata()
        self.current_analysis: Optional[AIAnalysis] = None
        self.chat_history: List[Tuple[str, str]] = []  # (Role, Message)
        self.heuristics_run = False

        # Specialized services
        self.scanner = ScannerService(wm)
        self.state_manager = ProjectStateManager(wm)
        self.engine = AnalysisEngine(self.prompt_manager)

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
        pid, metadata, history, fingerprint, analysis = self.state_manager.load_project(
            project_path
        )
        self.project_id = pid
        if metadata:
            self.current_metadata = metadata
            self.chat_history = history
            self.current_fingerprint = fingerprint
            self.current_analysis = analysis

            # Ensure file suggestions are synced with fingerprint significant files
            if self.current_fingerprint and self.current_fingerprint.significant_files:
                if not self.current_analysis:
                    from opendata.models import AIAnalysis

                    self.current_analysis = AIAnalysis(summary="Restored state")

                existing_paths = {
                    fs.path for fs in self.current_analysis.file_suggestions
                }
                for path in self.current_fingerprint.significant_files:
                    if path not in existing_paths:
                        from opendata.models import FileSuggestion

                        self.current_analysis.file_suggestions.append(
                            FileSuggestion(path=path, reason=_("Supporting file"))
                        )

            self.heuristics_run = bool(
                self.current_fingerprint and self.current_fingerprint.significant_files
            )
            return True
        return False

    def _normalize_metadata(self):
        """Ensures all metadata fields are properly typed as Pydantic objects."""
        from opendata.models import RelatedResource

        if self.current_metadata.authors:
            self.current_metadata.authors = [
                a if isinstance(a, PersonOrOrg) else PersonOrOrg.model_validate(a)
                for a in self.current_metadata.authors
            ]
        if self.current_metadata.contacts:
            self.current_metadata.contacts = [
                c if isinstance(c, Contact) else Contact.model_validate(c)
                for c in self.current_metadata.contacts
            ]
        if self.current_metadata.related_publications:
            self.current_metadata.related_publications = [
                p
                if isinstance(p, RelatedResource)
                else RelatedResource.model_validate(p)
                for p in self.current_metadata.related_publications
            ]
        if self.current_metadata.related_datasets:
            self.current_metadata.related_datasets = [
                d
                if isinstance(d, RelatedResource)
                else RelatedResource.model_validate(d)
                for d in self.current_metadata.related_datasets
            ]

    def save_state(self):
        """Persists the current state to the workspace."""
        if not self.project_id:
            return
        self._normalize_metadata()
        self.state_manager.save_state(
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
        self.current_metadata = Metadata()
        self.current_analysis = None
        self.save_state()

    def reset_agent_state(self):
        """Resets the agent state in memory without persisting to disk."""
        self.current_metadata = Metadata()
        self.chat_history = []
        self.current_fingerprint = None
        self.project_id = None

    def _get_effective_field(self) -> Optional[str]:
        """Gets the user-selected field protocol from project config.

        NO HEURISTICS - Returns ONLY what user explicitly selected.
        """
        # Check project config (user's explicit selection)
        if self.project_id:
            config = self.wm.load_project_config(self.project_id)
            if config.get("field_name"):
                return config["field_name"]

        # No user selection = no field protocol
        return None

    def set_field_protocol(self, field_name: Any):
        """User explicitly selects a field protocol."""
        # Handle NiceGUI dict value if necessary
        if isinstance(field_name, dict):
            field_name = field_name.get("label", field_name.get("value", ""))

        if self.project_id:
            config = self.wm.load_project_config(self.project_id)
            config["field_name"] = str(field_name)
            self.wm.save_project_config(self.project_id, config)
            logger.info(f"Field protocol set to: {field_name}")

    def refresh_inventory(
        self,
        project_dir: Path,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
        stop_event: Optional[Any] = None,
        force: bool = False,
    ) -> str:
        """
        Performs a fast file scan and updates the SQLite inventory without running heuristics or AI.
        """
        self.project_id = self.wm.get_project_id(project_dir)

        if force:
            self.current_fingerprint = None

        # 1. Determine field first to have exclusions ready for scanning
        field_name = self._get_effective_field()
        effective = self.pm.resolve_effective_protocol(self.project_id, field_name)
        exclude_patterns = effective.get("exclude", [])

        if not self.current_fingerprint:
            if progress_callback:
                progress_callback(_("Scanning project structure..."), "", "")

            try:
                fp, inventory = scan_project_lazy(
                    project_dir, progress_callback, stop_event, exclude_patterns
                )
                self.current_fingerprint = fp
                self.wm.update_inventory(self.project_id, inventory)
            except Exception as e:
                logger.error(
                    f"Scan failed for project {self.project_id}: {e}", exc_info=True
                )
                return _("Scan failed: {error}").format(error=str(e))

        # 2. Re-check field after scan (heuristics might have improved)
        new_field = self._get_effective_field()
        if new_field != field_name:
            field_name = new_field
            effective = self.pm.resolve_effective_protocol(self.project_id, field_name)

        # 3. DO NOT update metadata - field protocol is separate from RODBUK classification
        #    science_branches_mnisw is for RODBUK repository classification only
        #    Field protocol is stored in project_config.json

        from opendata.utils import format_size

        total_size = self.current_fingerprint.total_size_bytes

        self.save_state()
        return _(
            "Inventory refreshed. Project contains {count} files, total size: {size}."
        ).format(
            count=self.current_fingerprint.file_count, size=format_size(total_size)
        )

    def _update_heuristics_state(self):
        """Internal helper to sync heuristics_run flag and primary file."""
        if not self.current_fingerprint:
            return

        # 1. Update heuristics_run flag
        self.heuristics_run = len(self.current_fingerprint.significant_files) > 0

        # 2. Update primary file if needed
        if not self.current_fingerprint.primary_file and self.current_analysis:
            for fs in self.current_analysis.file_suggestions:
                if "Main article" in fs.reason and fs.path.endswith((".tex", ".docx")):
                    self.current_fingerprint.primary_file = fs.path
                    break

    def add_significant_file(self, path: str, category: str = "other"):
        """Adds a file to significant files with a category."""
        if not self.current_fingerprint:
            return

        # Ensure path is relative to root
        if path not in self.current_fingerprint.significant_files:
            self.current_fingerprint.significant_files.append(path)

        # Update or create suggestion
        from opendata.models import FileSuggestion, AIAnalysis

        category_labels = {
            "main_article": "Main article/paper",
            "visualization_scripts": "Visualization scripts",
            "data_files": "Data files",
            "documentation": "Documentation",
            "other": "Supporting file",
        }
        reason = category_labels.get(category, "Supporting file")

        if not self.current_analysis:
            self.current_analysis = AIAnalysis(summary="Manual selection")

        # Find existing or add new
        existing = next(
            (fs for fs in self.current_analysis.file_suggestions if fs.path == path),
            None,
        )
        if existing:
            existing.reason = reason
        else:
            self.current_analysis.file_suggestions.append(
                FileSuggestion(path=path, reason=reason)
            )

        self._update_heuristics_state()
        self.save_state()

    def remove_significant_file(self, path: str):
        """Removes a file from significant files."""
        if not self.current_fingerprint:
            return

        if path in self.current_fingerprint.significant_files:
            self.current_fingerprint.significant_files.remove(path)

        if self.current_analysis:
            self.current_analysis.file_suggestions = [
                fs for fs in self.current_analysis.file_suggestions if fs.path != path
            ]

        # Clear primary file if it was the one removed
        if self.current_fingerprint.primary_file == path:
            self.current_fingerprint.primary_file = None

        self._update_heuristics_state()
        self.save_state()

    def update_file_role(self, path: str, category: str):
        """Updates the role of an existing significant file."""
        self.add_significant_file(path, category)

    def set_significant_files_manual(self, selections: list[dict[str, str]]) -> str:
        """
        User manually selects significant files with categories.
        Replaces AI heuristics phase entirely.

        Args:
            selections: List of dicts with 'path' and 'category' keys.
                       Categories: main_article, visualization_scripts, data_files, documentation, other

        Returns:
            Confirmation message for chat history.
        """
        if not self.current_fingerprint:
            return _("Error: No inventory found. Please scan the project first.")

        # 1. Validate and filter selections against inventory
        inventory_paths = set(self.current_fingerprint.structure_sample)
        valid_selections = []
        for sel in selections:
            path = sel.get("path", "")
            if path in inventory_paths:
                valid_selections.append(sel)

        # 2. Update significant files list
        self.current_fingerprint.significant_files = [
            sel["path"] for sel in valid_selections
        ]

        # 3. Auto-set primary file if article found
        for sel in valid_selections:
            if sel.get("category") == "main_article":
                path = sel["path"]
                if path.endswith((".tex", ".docx")):
                    self.current_fingerprint.primary_file = path
                    break

        # 4. Store categories in analysis for context injection
        from opendata.models import FileSuggestion, AIAnalysis

        category_labels = {
            "main_article": "Main article/paper",
            "visualization_scripts": "Visualization scripts",
            "data_files": "Data files",
            "documentation": "Documentation",
            "other": "Supporting file",
        }

        file_suggestions = []
        for sel in valid_selections:
            category = sel.get("category", "other")
            reason = category_labels.get(category, category)
            file_suggestions.append(FileSuggestion(path=sel["path"], reason=reason))

        # Create or update analysis object
        if not self.current_analysis:
            self.current_analysis = AIAnalysis(summary="Manual file selection")
        self.current_analysis.file_suggestions = file_suggestions

        # 5. Set heuristics_run flag to enable AI Analyze button
        self.heuristics_run = True

        # 6. Add chat message
        if valid_selections:
            files_msg = ", ".join([f"`{sel['path']}`" for sel in valid_selections])
            msg = _(
                "### Manual File Selection\n\nSelected {count} files: {files}\n\n*Ready for deep content analysis. Click **AI Analyze** to proceed.*"
            ).format(count=len(valid_selections), files=files_msg)
            self.chat_history.append(("agent", msg))
        else:
            msg = _("Cleared all file selections.")
            self.chat_history.append(("agent", msg))

        self.save_state()
        return msg

    def run_ai_analysis_phase(
        self,
        ai_service: Any,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
        stop_event: Optional[Any] = None,
    ) -> str:
        """
        Phase 3: Runs the AI analysis loop to refine metadata.
        Injects full text of significant files found in heuristics.
        """
        if not self.current_fingerprint:
            return _("Error: No inventory found. Please scan the project first.")

        if progress_callback:
            progress_callback(_("Consulting AI for project summary..."), "", "")

        # 1. Gather Context from Significant Files
        project_dir = Path(self.current_fingerprint.root_path)
        all_context_files = set(self.current_fingerprint.significant_files)
        if self.current_fingerprint.primary_file:
            all_context_files.add(self.current_fingerprint.primary_file)

        # Read content
        extra_context = []
        for rel_path in sorted(list(all_context_files)):
            p = project_dir / rel_path
            if p.exists():
                content = FullTextReader.read_full_text(p)
                if content:
                    extra_context.append(f"--- FILE CONTENT: {rel_path} ---\n{content}")

        # 2. Prepare Prompt
        field_name = self._get_effective_field()
        effective = self.pm.resolve_effective_protocol(self.project_id, field_name)

        initial_prompt = _(
            "Please analyze the gathered project heuristics and the provided file contents to generate a comprehensive summary and draft metadata."
        )

        if extra_context:
            initial_prompt += "\n\n[CONTEXT FROM PROJECT FILES]\n" + "\n".join(
                extra_context
            )

        from opendata.ui.state import ScanState

        mode = ScanState.agent_mode if hasattr(ScanState, "agent_mode") else "metadata"

        clean_msg, analysis, metadata = self.engine.run_ai_loop(
            ai_service=ai_service,
            user_input=initial_prompt,
            chat_history=[],  # Start fresh analysis context
            current_metadata=self.current_metadata,
            fingerprint=self.current_fingerprint,
            effective_protocol=effective,
            mode=mode,
            stop_event=stop_event,
        )

        if stop_event and stop_event.is_set():
            return _("AI analysis cancelled by user.")

        if analysis:
            # Preserve manually selected file suggestions
            if self.current_analysis and self.current_analysis.file_suggestions:
                analysis.file_suggestions = self.current_analysis.file_suggestions
            self.current_analysis = analysis

        self.current_metadata = metadata
        self.chat_history.append(("agent", clean_msg))
        self.save_state()
        return clean_msg

    def process_user_input(
        self,
        user_text: str,
        ai_service: Any,
        skip_user_append: bool = False,
        on_update: Optional[Callable[[], None]] = None,
        mode: str = "metadata",
        stop_event: Optional[Any] = None,
    ) -> str:
        """Main iterative loop delegated to AnalysisEngine."""
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
                        # Add found files to extra_files so they are read into context
                        extra_files.extend(found)
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

        # 3. ADD EXTRA FILES TO CONTEXT
        enhanced_input = user_text
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
                    extra_context.append(
                        f"--- USER-REQUESTED FILE: {rel_p} ---\n{content}"
                    )
                    read_files.append(f"`{rel_p}`")

            if extra_context:
                self.chat_history.append(
                    (
                        "agent",
                        f"[System] context expanded with content of: {', '.join(read_files)}",
                    )
                )
                if on_update:
                    on_update()

                enhanced_input = (
                    f"{user_text}\n\n[CONTEXT FROM ATTACHED FILES]\n"
                    + "\n".join(extra_context)
                )

        # 4. CALL ENGINE
        field_name = self._get_effective_field()
        effective = self.pm.resolve_effective_protocol(self.project_id, field_name)

        def on_system_msg(msg: str):
            self.chat_history.append(("agent", f"[System] {msg}"))

        clean_msg, analysis, metadata = self.engine.run_ai_loop(
            ai_service=ai_service,
            user_input=enhanced_input,
            chat_history=self.chat_history,
            current_metadata=self.current_metadata,
            fingerprint=self.current_fingerprint,
            effective_protocol=effective,
            mode=mode,
            on_update=on_update,
            on_system_msg=on_system_msg,
            stop_event=stop_event,
        )

        # SELECTIVE METADATA UPDATE IN CURATOR MODE
        if mode == "curator":
            logger.info(
                "Curator mode active: allowing only data-related metadata updates."
            )
            allowed_curator_fields = {
                "kind_of_data",
                "software",
                "notes",
                "related_publications",
                "related_datasets",
            }

            current_dict = self.current_metadata.model_dump()
            new_dict = metadata.model_dump()

            for field in allowed_curator_fields:
                if field in new_dict and new_dict[field]:
                    if field == "notes" and current_dict.get("notes"):
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

        if analysis:
            self.current_analysis = analysis

        self.current_metadata = metadata
        self.chat_history.append(("agent", clean_msg))
        self.save_state()
        if on_update:
            on_update()
        return clean_msg

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
            "related_publications",
            "related_datasets",
        ]

        current_dict = self.current_metadata.model_dump(exclude_unset=True)
        processed_answers = {}

        for k, v in answers.items():
            if not v:
                continue

            # Skip fields that are just user commentary or don't match model structure
            if k == "authors" and isinstance(v, str) and "names" in v.lower():
                continue  # User answered a choice question about authorship policy

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
            logger.error(
                f"Metadata validation failed during form submission: {e}", exc_info=True
            )
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
        """Delegates prompt generation to AnalysisEngine."""
        field_name = self._get_effective_field()
        effective = self.pm.resolve_effective_protocol(self.project_id, field_name)
        return self.engine.generate_ai_prompt(
            mode, self.current_metadata, self.current_fingerprint, effective
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
