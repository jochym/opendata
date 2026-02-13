from pathlib import Path
import yaml
import hashlib
import logging
from typing import Any, Dict, List, Type, TypeVar
from pydantic import BaseModel
from opendata.models import UserSettings, Metadata, ProjectFingerprint, AIAnalysis
import json

logger = logging.getLogger("opendata.workspace")

T = TypeVar("T", bound=BaseModel)


class WorkspaceManager:
    """Manages the hidden workspace and YAML persistence for the tool."""

    def __init__(self, base_path: Path | None = None):
        self._projects_cache: List[Dict[str, str]] | None = None
        # Default to ~/.opendata_tool if no path provided
        self.base_path = base_path or Path.home() / ".opendata_tool"
        self.protocols_dir = self.base_path / "protocols"
        self.workspaces_dir = self.base_path / "workspaces"
        self.projects_dir = self.base_path / "projects"
        self.bug_reports_dir = self.base_path / "bug_reports"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Creates the necessary workspace structure."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.protocols_dir.mkdir(parents=True, exist_ok=True)
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.bug_reports_dir.mkdir(parents=True, exist_ok=True)

    def get_project_id(self, project_path: Path) -> str:
        """Generates a unique ID for a project based on its absolute path."""
        # Ensure path exists or is at least resolvable before hashing
        try:
            # Use as_posix and strip trailing slash for consistent ID generation
            abs_path = str(project_path.resolve().as_posix()).rstrip("/")
        except Exception:
            # Fallback for paths that don't exist yet but are specified
            abs_path = str(project_path.absolute().as_posix()).rstrip("/")

        return hashlib.md5(abs_path.encode("utf-8")).hexdigest()

    def get_project_dir(self, project_id: str) -> Path:
        """Returns the storage directory for a specific project."""
        return self.projects_dir / project_id

    def get_project_db_path(self, project_id: str) -> Path:
        """Returns the path to the project's SQLite database."""
        return self.get_project_dir(project_id) / "inventory.db"

    def save_project_state(
        self,
        project_id: str,
        metadata: Metadata,
        chat_history: List[tuple[str, str]],
        fingerprint: ProjectFingerprint | None,
        analysis: AIAnalysis | None = None,
    ):
        """Persists the complete state of a project."""
        self._projects_cache = None  # Invalidate cache
        pdir = self.get_project_dir(project_id)
        pdir.mkdir(parents=True, exist_ok=True)

        # Save Metadata (YAML)
        self.save_yaml(metadata, str(pdir / "metadata.yaml"))

        # Save Chat History (JSON)
        with open(pdir / "chat_history.json", "w", encoding="utf-8") as f:
            json.dump(chat_history, f, ensure_ascii=False, indent=2)

        # Save Fingerprint (JSON)
        if fingerprint:
            with open(pdir / "fingerprint.json", "w", encoding="utf-8") as f:
                f.write(fingerprint.model_dump_json(indent=2))

        # Save Analysis (JSON)
        if analysis:
            with open(pdir / "analysis.json", "w", encoding="utf-8") as f:
                f.write(analysis.model_dump_json(indent=2))
        else:
            # Clear analysis file if None provided
            analysis_path = pdir / "analysis.json"
            if analysis_path.exists():
                analysis_path.unlink()

    def load_project_state(
        self, project_id: str
    ) -> tuple[
        Metadata | None,
        List[tuple[str, str]],
        ProjectFingerprint | None,
        AIAnalysis | None,
    ]:
        """Loads the persisted state of a project."""
        pdir = self.get_project_dir(project_id)
        if not pdir.exists():
            return None, [], None, None

        metadata = self.load_yaml(Metadata, str(pdir / "metadata.yaml"))

        history = []
        history_path = pdir / "chat_history.json"
        if history_path.exists():
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    history = [tuple(item) for item in json.load(f)]
            except Exception:
                pass

        fingerprint = None
        fp_path = pdir / "fingerprint.json"
        if fp_path.exists():
            try:
                with open(fp_path, "r", encoding="utf-8") as f:
                    fingerprint = ProjectFingerprint.model_validate_json(f.read())
            except Exception:
                pass

        analysis = None
        analysis_path = pdir / "analysis.json"
        if analysis_path.exists():
            try:
                with open(analysis_path, "r", encoding="utf-8") as f:
                    analysis = AIAnalysis.model_validate_json(f.read())
            except Exception:
                pass

        return metadata, history, fingerprint, analysis

    async def list_projects_async(self) -> List[Dict[str, str]]:
        """Asynchronously lists all projects."""
        import asyncio

        return await asyncio.to_thread(self.list_projects)

    def list_projects(self) -> List[Dict[str, str]]:
        """Lists all projects that have a persisted state (cached)."""
        if self._projects_cache is not None:
            return self._projects_cache  # type: ignore

        projects = []
        if not self.projects_dir.exists():
            return []
        for pdir in self.projects_dir.iterdir():
            if not pdir.is_dir():
                continue

            try:
                metadata = self.load_yaml(Metadata, str(pdir / "metadata.yaml"))
                title = metadata.title if metadata else "Untitled Project"

                fp_path = pdir / "fingerprint.json"
                root_path = "Unknown"
                if fp_path.exists():
                    with open(fp_path, "r", encoding="utf-8") as f:
                        fp = json.load(f)
                        root_path = fp.get("root_path", "Unknown")

                projects.append(
                    {
                        "id": pdir.name,
                        "title": title or "Untitled Project",
                        "path": root_path,
                    }
                )
            except Exception as e:
                projects.append(
                    {
                        "id": pdir.name,
                        "title": f"Corrupt Project ({pdir.name[:8]})",
                        "path": "Unknown",
                    }
                )

        self._projects_cache = projects
        return projects

    def delete_project(self, project_id: str):
        """Permanently deletes a project's persisted state."""
        import shutil
        import os
        import gc

        pdir = self.projects_dir / project_id
        if pdir.exists() and pdir.is_dir():
            try:
                gc.collect()
                shutil.rmtree(pdir, ignore_errors=True)
                if pdir.exists():
                    for root, dirs, files in os.walk(str(pdir), topdown=False):
                        for name in files:
                            try:
                                os.remove(os.path.join(root, name))
                            except:
                                pass
                        for name in dirs:
                            try:
                                os.rmdir(os.path.join(root, name))
                            except:
                                pass
                    try:
                        os.rmdir(str(pdir))
                    except:
                        pass

                success = not pdir.exists()
                if success:
                    self._projects_cache = None
                return success
            except Exception as e:
                logger.error(
                    f"Failed to delete project directory {pdir}: {e}", exc_info=True
                )
                return False
        return False

    def save_yaml(self, data: BaseModel, filename: str):
        """Saves a Pydantic model as a human-readable YAML file."""
        target_path = Path(filename)
        if not target_path.is_absolute():
            target_path = self.base_path / filename

        if not target_path.suffix == ".yaml":
            target_path = target_path.with_suffix(".yaml")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            yaml.dump(data.model_dump(), f, allow_unicode=True, sort_keys=False)

    def load_yaml(self, model_class: Type[T], filename: str) -> T | None:
        """Loads a YAML file into a Pydantic model."""
        target_path = Path(filename)
        if not target_path.is_absolute():
            target_path = self.base_path / filename

        if not target_path.exists():
            return None

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data is None:
                    return None
                return model_class.model_validate(data)
        except Exception as e:
            return None

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
