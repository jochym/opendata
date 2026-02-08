import yaml
import json
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
    Question,
    PersonOrOrg,
    Contact,
)
from opendata.extractors.base import ExtractorRegistry, PartialMetadata
from opendata.workspace import WorkspaceManager
from opendata.utils import scan_project_lazy, PromptManager
from opendata.i18n.translator import setup_i18n, _

logger = logging.getLogger(__name__)


class ProjectAnalysisAgent:
    def __init__(self, wm: WorkspaceManager):
        self.logger = logger
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

    def refresh_inventory(
        self, project_dir: Path, progress_callback=None, stop_event=None
    ):
        """Performs a fast file scan and updates the SQLite inventory without heuristics."""
        self.logger.info(f"DEBUG: refresh_inventory START for {project_dir}")
        self.project_id = self.wm.get_project_id(project_dir)

        field_name = (
            self.current_metadata.science_branches_mnisw[0]
            if self.current_metadata.science_branches_mnisw
            else None
        )
        effective = self.pm.resolve_effective_protocol(self.project_id, field_name)
        exclude_patterns = effective.get("exclude")

        # 1. Update Fingerprint and get file list for DB
        res = scan_project_lazy(
            project_dir,
            progress_callback=progress_callback,
            stop_event=stop_event,
            exclude_patterns=exclude_patterns,
        )
        self.current_fingerprint, full_files = res

        if stop_event and stop_event.is_set():
            return

        # 2. Update SQLite
        try:
            from opendata.storage.project_db import ProjectInventoryDB

            db = ProjectInventoryDB(self.wm.get_project_db_path(self.project_id))
            db.update_inventory(full_files)
            self.logger.info(
                f"DEBUG: refresh_inventory SUCCESS. {len(full_files)} files."
            )
        except Exception as e:
            self.logger.error(f"DEBUG: Failed to refresh inventory: {e}")
            raise e

        self.save_state()

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

        self.current_metadata = Metadata.model_construct()
        self.chat_history = []
        self.current_fingerprint = None

        if progress_callback:
            progress_callback(f"Scanning {project_dir}...", "", "")

        self.logger.info(f"DEBUG: start_analysis actual scan START for {project_dir}")
        field_name = (
            self.current_metadata.science_branches_mnisw[0]
            if self.current_metadata.science_branches_mnisw
            else None
        )
        effective = self.pm.resolve_effective_protocol(self.project_id, field_name)
        exclude_patterns = effective.get("exclude")

        if stop_event and stop_event.is_set():
            self.logger.warning("DEBUG: stop_event ALREADY SET. Clearing it.")
            stop_event.clear()

        # Integrated scan: statistics and file inventory in one pass
        res = scan_project_lazy(
            project_dir,
            progress_callback=progress_callback,
            stop_event=stop_event,
            exclude_patterns=exclude_patterns,
        )
        self.current_fingerprint, full_files = res

        self.logger.info(
            f"DEBUG: Fingerprint complete. Files: {self.current_fingerprint.file_count}"
        )

        if stop_event and stop_event.is_set():
            return "Scan cancelled by user."

        # Persistent Inventory: Save all files to SQLite (Already collected in scan_project_lazy)
        try:
            from opendata.storage.project_db import ProjectInventoryDB

            msg_status = "Saving file inventory to database..."
            try:
                from opendata.i18n.translator import _

                msg_status = _("Saving file inventory to database...")
            except:
                pass

            if progress_callback:
                progress_callback(msg_status, "", "")

            db = ProjectInventoryDB(self.wm.get_project_db_path(self.project_id))
            db.update_inventory(full_files)
            self.logger.info(
                f"DEBUG: SQLite inventory updated with {len(full_files)} files."
            )
        except Exception as e:
            self.logger.error(f"DEBUG: Failed to save inventory: {e}")

        # Run Heuristics
        heuristics_data = {}
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

            if p_stat is not None:  # It's a file
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
                    # Filter only fields that exist in our Metadata model to avoid validation errors
                    metadata_fields = Metadata.model_fields.keys()
                    for key, val in partial.model_dump(exclude_unset=True).items():
                        if val and key in metadata_fields:
                            if isinstance(val, list) and key in heuristics_data:
                                for item in val:
                                    if item not in heuristics_data[key]:
                                        heuristics_data[key].append(item)
                            else:
                                heuristics_data[key] = val

        # Heuristics extraction finished, now create a valid Metadata model
        self.current_metadata = Metadata.model_validate(heuristics_data)

        # Normalize authors and contacts to ensure they are full objects
        if self.current_metadata.authors:
            self.current_metadata.authors = [
                PersonOrOrg.model_validate(a) if isinstance(a, dict) else a
                for a in self.current_metadata.authors
            ]

        if self.current_metadata.contacts:
            self.current_metadata.contacts = [
                Contact.model_validate(c) if isinstance(c, dict) else c
                for c in self.current_metadata.contacts
            ]

        msg = f"I've scanned {self.current_fingerprint.file_count} files in your project. "
        found_fields = list(heuristics_data.keys())
        if found_fields:
            msg += f"I automatically found some data for: {', '.join(found_fields)}. "
        else:
            msg += "I couldn't find obvious metadata files. "

        if candidate_main_files:
            main_file = sorted(
                candidate_main_files, key=lambda x: x.stat().st_size, reverse=True
            )[0]
            rel_main_file = main_file.relative_to(project_dir)
            msg += f"\n\nI found **{rel_main_file}**. Shall I process its full text to extract metadata?"
        else:
            msg += "\n\nShould I use AI to analyze the paper titles?"

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
        """Main iterative loop."""
        if not skip_user_append:
            self.chat_history.append(("user", user_text))
            if on_update:
                on_update()

        if user_text.strip().lower().startswith("/bug"):
            return self._handle_bug_command(user_text)

        # Context persistence
        context = self.generate_ai_prompt()
        history_str = "\n".join(
            [f"{role}: {m}" for role, m in self.chat_history[-10:-1]]
        )

        full_prompt = self.prompt_manager.render(
            "chat_wrapper",
            {
                "history": history_str,
                "user_input": user_text,
                "context": context,
            },
        )

        ai_response = ai_service.ask_agent(full_prompt)
        clean_msg = self._extract_metadata_from_ai_response(
            f"METADATA:\n{ai_response}"
            if "METADATA:" not in ai_response
            else ai_response
        )

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
        """
        if not self.current_analysis:
            return "No active analysis to answer."

        current_dict = self.current_metadata.model_dump(exclude_unset=True)

        processed_answers = {}
        for k, v in answers.items():
            if k in [
                "science_branches_oecd",
                "science_branches_mnisw",
                "keywords",
                "description",
                "software",
            ]:
                processed_answers[k] = [v] if isinstance(v, str) else v
            else:
                processed_answers[k] = v

        current_dict.update(processed_answers)
        self.current_metadata = Metadata.model_validate(current_dict)

        msg = "Thank you! I've updated the metadata with your answers."
        self.current_analysis = None

        human_answers = []
        for k, v in processed_answers.items():
            label = k.replace("_", " ").title()
            val_str = ", ".join(map(str, v)) if isinstance(v, list) else str(v)
            human_answers.append(f"- **{label}**: {val_str}")

        summary = "\n".join(human_answers)
        self.chat_history.append(("user", f"Updated fields:\n\n{summary}"))
        self.chat_history.append(("agent", msg))
        self.save_state()

        if on_update:
            on_update()

        return msg

    def _extract_metadata_from_ai_response(self, response_text: str) -> str:
        """Parses METADATA block from AI response."""
        self.current_analysis = None
        if "METADATA:" not in response_text:
            return response_text

        try:
            parts = response_text.split("METADATA:", 1)
            json_section = parts[1].strip()

            # Extract JSON braces
            start = json_section.find("{")
            end = json_section.rfind("}") + 1
            if start == -1 or end == 0:
                return response_text

            data = json.loads(json_section[start:end])

            if "METADATA" in data and "ANALYSIS" in data:
                updates = data["METADATA"]
                self.current_analysis = AIAnalysis.model_validate(data["ANALYSIS"])
            else:
                updates = data

            current_dict = self.current_metadata.model_dump(exclude_unset=True)
            current_dict.update(updates)
            self.current_metadata = Metadata.model_validate(current_dict)
            return response_text.split("METADATA:")[0].strip() or "Metadata updated."
        except Exception as e:
            self.logger.error(f"Failed to parse metadata: {e}")
            return response_text

    def generate_ai_prompt(self) -> str:
        if not self.current_fingerprint:
            return "No project scanned."
        return self.prompt_manager.render(
            "system_prompt",
            {
                "fingerprint": self.current_fingerprint.model_dump_json(),
                "metadata": yaml.dump(
                    self.current_metadata.model_dump(exclude_unset=True),
                    allow_unicode=True,
                ),
                "protocols": "None active.",
            },
        )

    def _handle_bug_command(self, user_text: str) -> str:
        # Diagnostic report logic (simplified for session)
        return "Bug report generated (Simulation)."
