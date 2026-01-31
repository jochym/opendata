from pathlib import Path
import yaml
from typing import Any, Dict, Type, TypeVar
from pydantic import BaseModel
from opendata.models import UserSettings

T = TypeVar("T", bound=BaseModel)


class WorkspaceManager:
    """Manages the hidden workspace and YAML persistence for the tool."""

    def __init__(self, base_path: Path | None = None):
        # Default to ~/.opendata_tool if no path provided
        self.base_path = base_path or Path.home() / ".opendata_tool"
        self.protocols_dir = self.base_path / "protocols"
        self.workspaces_dir = self.base_path / "workspaces"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Creates the necessary workspace structure."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.protocols_dir.mkdir(parents=True, exist_ok=True)
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)

    def save_yaml(self, data: BaseModel, filename: str):
        """Saves a Pydantic model as a human-readable YAML file."""
        target_path = self.base_path / filename
        # Ensure suffix is .yaml
        if not target_path.suffix == ".yaml":
            target_path = target_path.with_suffix(".yaml")

        with open(target_path, "w", encoding="utf-8") as f:
            # We convert to dict first to handle Pydantic's complexity
            yaml.dump(data.model_dump(), f, allow_unicode=True, sort_keys=False)

    def load_yaml(self, model_class: Type[T], filename: str) -> T | None:
        """Loads a YAML file into a Pydantic model."""
        target_path = self.base_path / filename
        if not target_path.exists():
            return None

        with open(target_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return model_class.model_validate(data)

    def get_settings(self) -> UserSettings:
        """Retrieves user settings or returns defaults."""
        settings = self.load_yaml(UserSettings, "settings.yaml")
        if not settings:
            settings = UserSettings(
                workspace_path=str(self.workspaces_dir),
                field_protocols_path=str(self.protocols_dir),
            )
            self.save_yaml(settings, "settings.yaml")
        return settings
