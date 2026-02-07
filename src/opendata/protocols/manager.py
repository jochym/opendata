from pathlib import Path
from typing import List, Dict, Optional
import yaml
from ..models import ExtractionProtocol, ProtocolLevel
from ..workspace import WorkspaceManager


class ProtocolManager:
    """Manages hierarchical extraction protocols (System, Global, Field, Project)."""

    def __init__(self, workspace: WorkspaceManager):
        self.workspace = workspace
        self.protocols_dir = self.workspace.protocols_dir
        self.fields_dir = self.protocols_dir / "fields"

        self.protocols_dir.mkdir(parents=True, exist_ok=True)
        self.fields_dir.mkdir(parents=True, exist_ok=True)

        self.system_protocol = self._init_system_protocol()

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
            extraction_prompts=[
                "Identify the primary research paper (LaTeX, PDF, or Docx).",
                "Extract authors, affiliations, and ORCIDs where available.",
                "Summarize the project based on README or main publication abstract.",
                "Identify scientific software and versions used.",
            ],
        )

    def get_global_protocol(self) -> ExtractionProtocol:
        path = self.protocols_dir / "global.yaml"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f)
                    return ExtractionProtocol.model_validate(data)
                except Exception as e:
                    print(f"[ERROR] Failed to load global protocol: {e}")
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
        return [p.stem for p in self.fields_dir.glob("*.yaml")]

    def get_field_protocol(self, field_name: str) -> ExtractionProtocol:
        path = self.fields_dir / f"{field_name}.yaml"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f)
                    return ExtractionProtocol.model_validate(data)
                except Exception as e:
                    print(f"[ERROR] Failed to load field protocol {field_name}: {e}")
        return ExtractionProtocol(
            id=f"field_{field_name}", name=field_name, level=ProtocolLevel.FIELD
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
                    print(f"[ERROR] Failed to load project protocol {project_id}: {e}")
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

        effective = {"include": [], "exclude": [], "prompts": []}

        for p in layers:
            effective["include"].extend(p.include_patterns)
            effective["exclude"].extend(p.exclude_patterns)
            effective["prompts"].extend(p.extraction_prompts)

        # Deduplicate while preserving order
        effective["include"] = list(dict.fromkeys(effective["include"]))
        effective["exclude"] = list(dict.fromkeys(effective["exclude"]))
        effective["prompts"] = list(dict.fromkeys(effective["prompts"]))

        return effective
