from pathlib import Path
from typing import List, Dict, Optional
import yaml
import logging
from ..models import ExtractionProtocol, ProtocolLevel
from ..workspace import WorkspaceManager

logger = logging.getLogger("opendata.protocols")


class ProtocolManager:
    """Manages hierarchical extraction protocols (System, Global, Field, Project)."""

    def __init__(self, workspace: WorkspaceManager):
        self.workspace = workspace
        self.protocols_dir = self.workspace.protocols_dir
        self.fields_dir = self.protocols_dir / "fields"

        self.protocols_dir.mkdir(parents=True, exist_ok=True)
        self.fields_dir.mkdir(parents=True, exist_ok=True)

        self.system_protocol = self._init_system_protocol()

    def _get_predefined_fields(self) -> Dict[str, ExtractionProtocol]:
        """Returns standard built-in field protocols."""
        return {
            "physics": ExtractionProtocol(
                id="field_physics",
                name="Physics",
                level=ProtocolLevel.FIELD,
                exclude_patterns=[
                    "**/WAVECAR*",
                    "**/CHG*",
                    "**/PROCAR*",
                    "**/EIGENVAL*",
                    "**/DOSCAR*",
                    "**/LOCPOT*",
                    "**/XDATCAR*",
                ],
                extraction_prompts=[
                    "Check for VASP, Phonopy, and ALAMODE software versions."
                ],
            ),
            "computational_physics": ExtractionProtocol(
                id="field_comp_phys",
                name="Computational Physics",
                level=ProtocolLevel.FIELD,
                exclude_patterns=[
                    "**/WAVECAR*",
                    "**/CHG*",
                    "**/PROCAR*",
                    "**/EIGENVAL*",
                    "**/DOSCAR*",
                    "**/LOCPOT*",
                    "**/XDATCAR*",
                ],
                extraction_prompts=[
                    "Identify specific calculation parameters (ENECUT, ISMEAR, etc)."
                ],
            ),
            "nauki_fizyczne": ExtractionProtocol(
                id="field_nauki_fizyczne",
                name="Nauki Fizyczne",
                level=ProtocolLevel.FIELD,
                exclude_patterns=[
                    "**/WAVECAR*",
                    "**/CHG*",
                    "**/PROCAR*",
                    "**/EIGENVAL*",
                    "**/DOSCAR*",
                    "**/LOCPOT*",
                    "**/XDATCAR*",
                ],
                extraction_prompts=[
                    "Sprawdź wersje oprogramowania VASP, Phonopy i ALAMODE."
                ],
            ),
        }

    def _init_system_protocol(self) -> ExtractionProtocol:
        """Returns the hardcoded base system protocol."""
        return ExtractionProtocol(
            id="system_base",
            name="System Default",
            level=ProtocolLevel.SYSTEM,
            is_read_only=True,
            exclude_patterns=[
                "**/.*",
                "**/__pycache__",
                "**/node_modules",
                "**/venv",
                "**/*.tmp",
                "**/*.bak",
                "**/Thumbs.db",
                "**/.DS_Store",
            ],
            metadata_prompts=[
                "Identify the primary research paper (LaTeX, PDF, or Docx).",
                "Extract authors, affiliations, and ORCIDs where available.",
                "Summarize the project based on README or main publication abstract.",
                "Identify scientific software and versions used.",
            ],
            curator_prompts=[
                "Analyze the main publication file (LaTeX/Docx) to identify all datasets, figures, and processing steps mentioned.",
                "Ensure the package includes all raw data, processing scripts, and configuration files required to reproduce the core findings.",
                "Verify script-data linkages (e.g., Python scripts reading specific CSVs) and suggest including both.",
                "Suggest inclusion of README and LICENSE files if they exist.",
                "Group similar data files and suggest representative samples if the dataset is too large.",
            ],
        )

    def get_global_protocol(self) -> ExtractionProtocol:
        path = self.protocols_dir / "global.yaml"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data is None:
                        return ExtractionProtocol(
                            id="global_user",
                            name="Global User Rules",
                            level=ProtocolLevel.GLOBAL,
                        )
                    return ExtractionProtocol.model_validate(data)
            except Exception as e:
                logger.error(f"Failed to load global protocol: {e}", exc_info=True)
        return ExtractionProtocol(
            id="global_user", name="Global User Rules", level=ProtocolLevel.GLOBAL
        )

    def save_global_protocol(self, protocol: ExtractionProtocol):
        protocol.level = ProtocolLevel.GLOBAL
        path = self.protocols_dir / "global.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                protocol.model_dump(mode="json"), f, allow_unicode=True, sort_keys=False
            )

    def list_fields(self) -> List[str]:
        """Lists available fields by merging built-ins and disk files."""
        built_ins = list(self._get_predefined_fields().keys())
        on_disk = [p.stem for p in self.fields_dir.glob("*.yaml")]
        return list(set(built_ins + on_disk))

    def get_field_protocol(self, field_name: str) -> ExtractionProtocol:
        """Retrieves a field protocol, checking user overrides first."""
        norm_name = field_name.lower().replace(" ", "_")

        # 1. Check disk (user override)
        path = self.fields_dir / f"{norm_name}.yaml"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                try:
                    return ExtractionProtocol.model_validate(yaml.safe_load(f))
                except Exception:
                    pass

        # 2. Check built-ins
        built_ins = self._get_predefined_fields()
        if norm_name in built_ins:
            return built_ins[norm_name]

        return ExtractionProtocol(
            id=f"field_{norm_name}", name=field_name, level=ProtocolLevel.FIELD
        )

    def save_field_protocol(self, protocol: ExtractionProtocol):
        protocol.level = ProtocolLevel.FIELD
        path = self.fields_dir / f"{protocol.name.lower().replace(' ', '_')}.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                protocol.model_dump(mode="json"), f, allow_unicode=True, sort_keys=False
            )

    def get_project_protocol(self, project_id: str) -> ExtractionProtocol:
        # Project protocols are stored in the workspace project folder
        project_dir = self.workspace.projects_dir / project_id
        path = project_dir / "protocol.yaml"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f)
                    return ExtractionProtocol.model_validate(data)
                except Exception as e:
                    logger.error(
                        f"Failed to load project protocol {project_id}: {e}",
                        exc_info=True,
                    )
        return ExtractionProtocol(
            id=f"project_{project_id}",
            name="Project Rules",
            level=ProtocolLevel.PROJECT,
        )

    def save_project_protocol(self, project_id: str, protocol: ExtractionProtocol):
        protocol.level = ProtocolLevel.PROJECT
        project_dir = self.workspace.projects_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        path = project_dir / "protocol.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                protocol.model_dump(mode="json"), f, allow_unicode=True, sort_keys=False
            )

    def resolve_effective_protocol(
        self, project_id: Optional[str] = None, field_name: Optional[str] = None
    ) -> Dict:
        """Merges all layers into a final instruction set."""
        layers = [self.system_protocol, self.get_global_protocol()]

        if field_name:
            layers.append(self.get_field_protocol(field_name))

        if project_id:
            layers.append(self.get_project_protocol(project_id))

        effective = {
            "include": [],
            "exclude": [],
            "prompts": [],
            "metadata_prompts": [],
            "curator_prompts": [],
        }

        for p in layers:
            effective["include"].extend(p.include_patterns)
            effective["exclude"].extend(p.exclude_patterns)
            effective["prompts"].extend(p.extraction_prompts)
            effective["metadata_prompts"].extend(p.metadata_prompts)
            effective["curator_prompts"].extend(p.curator_prompts)

        # Deduplicate while preserving order
        effective["include"] = list(dict.fromkeys(effective["include"]))
        effective["exclude"] = list(dict.fromkeys(effective["exclude"]))
        effective["prompts"] = list(dict.fromkeys(effective["prompts"]))
        effective["metadata_prompts"] = list(
            dict.fromkeys(effective["metadata_prompts"])
        )
        effective["curator_prompts"] = list(dict.fromkeys(effective["curator_prompts"]))

        import logging

        import logging

        logger = logging.getLogger("opendata.protocols")
        msg = f"Effective Protocol for {project_id} (Field: {field_name}):\n - Exclude: {effective['exclude']}\n - Include: {effective['include']}"
        logger.debug(msg)

        return effective
