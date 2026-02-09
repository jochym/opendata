import yaml
import re
import platform
import sys
import datetime
from typing import List, Optional, Dict, Any, Tuple, Callable
from pathlib import Path
from opendata.models import (
    Metadata,
    ProjectFingerprint,
    AIAnalysis,
    PersonOrOrg,
    Contact,
)
from opendata.extractors.base import ExtractorRegistry
from opendata.workspace import WorkspaceManager
from opendata.utils import scan_project_lazy, PromptManager, FullTextReader
from opendata.agents.parsing import extract_metadata_from_ai_response
from opendata.agents.tools import handle_external_tools


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
        self,
        project_dir: Path,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
        stop_event: Optional[Any] = None,
    ):
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
        exclude_patterns = effective.get("exclude")

        # 1. Quick fingerpint update
        res = scan_project_lazy(
            project_dir,
            progress_callback=progress_callback,
            stop_event=stop_event,
            exclude_patterns=exclude_patterns,
        )
        self.current_fingerprint, full_files = res

        if stop_event and stop_event.is_set():
            return

        # 2. Update SQLite Inventory
        try:
            from opendata.storage.project_db import ProjectInventoryDB

            db = ProjectInventoryDB(self.wm.get_project_db_path(self.project_id))
            db.update_inventory(full_files)
        except Exception as e:
            print(f"[ERROR] Failed to refresh inventory in SQLite: {e}")

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

        # NEW PROJECT or FORCED RESCAN
        self.current_metadata = Metadata.model_construct()
        self.chat_history = []
        self.current_fingerprint = None

        if progress_callback:
            progress_callback(f"Scanning {project_dir}...", "", "")

        field_name = (
            self.current_metadata.science_branches_mnisw[0]
            if self.current_metadata.science_branches_mnisw
            else None
        )
        effective = self.pm.resolve_effective_protocol(self.project_id, field_name)
        exclude_patterns = effective.get("exclude")

        # 1. Start Analysis
        res = scan_project_lazy(
            project_dir,
            progress_callback=progress_callback,
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
            print(f"[ERROR] Failed to save inventory to SQLite: {e}")

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
            rel_main_file = main_file.relative_to(project_dir)
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
    ) -> str:
        """Main iterative loop with Context Persistence and Tool recognition."""
        if not skip_user_append:
            self.chat_history.append(("user", user_text))
            if on_update:
                on_update()

        if user_text.strip().lower().startswith("/bug"):
            return self._handle_bug_command(user_text)

        # 1. EXTRACT @FILES
        extra_files = []
        at_matches = re.findall(r"@([^\s,]+)", user_text)
        if at_matches and self.current_fingerprint:
            project_dir = Path(self.current_fingerprint.root_path)
            for fname in at_matches:
                if "/" in fname or "\\" in fname:
                    p = project_dir / fname
                    if p.exists():
                        extra_files.append(p)
                else:
                    p = project_dir / fname
                    if p.exists():
                        extra_files.append(p)
                    else:
                        found = list(project_dir.glob(f"**/{fname}"))
                        if found:
                            extra_files.append(found[0])

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
            if extra_context:
                enhanced_input = (
                    f"{enhanced_input}\n\n[CONTEXT FROM ATTACHED FILES]\n"
                    + "\n".join(extra_context)
                )

        # 4. CALL AI
        context = self.generate_ai_prompt()
        history_str = "\n".join(
            [f"{role}: {m}" for role, m in self.chat_history[-10:-1]]
        )
        full_prompt = self.prompt_manager.render(
            "chat_wrapper",
            {"history": history_str, "user_input": enhanced_input, "context": context},
        )

        ai_response = ai_service.ask_agent(full_prompt)
        wrapped_response = (
            f"METADATA:\n{ai_response}"
            if "METADATA:" not in ai_response
            else ai_response
        )

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
        """Updates metadata based on form answers and clears current analysis."""
        if not self.current_analysis:
            return "No active analysis to answer."

        current_dict = self.current_metadata.model_dump(exclude_unset=True)
        processed_answers = {}
        list_fields = [
            "science_branches_oecd",
            "science_branches_mnisw",
            "keywords",
            "description",
            "software",
        ]

        for k, v in answers.items():
            processed_answers[k] = [v] if k in list_fields and isinstance(v, str) else v

        current_dict.update(processed_answers)
        self.current_metadata = Metadata.model_validate(current_dict)
        self.current_analysis = None

        human_answers = []
        for k, v in processed_answers.items():
            label = k.replace("_", " ").title()
            val_str = ", ".join(map(str, v)) if isinstance(v, list) else str(v)
            human_answers.append(f"- **{label}**: {val_str}")

        self.chat_history.append(
            ("user", f"Updated fields:\n\n" + "\n".join(human_answers))
        )
        msg = "Thank you! I've updated the metadata with your answers."
        self.chat_history.append(("agent", msg))
        self.save_state()

        if on_update:
            on_update()
        return msg

    def generate_ai_prompt(self) -> str:
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
        if effective.get("prompts"):
            protocols_str = "ACTIVE PROTOCOLS & USER RULES:\n" + "\n".join(
                [f"{i}. {p}" for i, p in enumerate(effective["prompts"], 1)]
            )
        else:
            protocols_str = "None active."

        return self.prompt_manager.render(
            "system_prompt",
            {
                "fingerprint": fingerprint_summary,
                "metadata": current_data,
                "protocols": protocols_str,
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
