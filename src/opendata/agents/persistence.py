import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from opendata.models import Metadata, AIAnalysis
from opendata.workspace import WorkspaceManager

logger = logging.getLogger("opendata.agents.persistence")


class ProjectStateManager:
    """Manager for project state persistence and loading."""

    def __init__(self, wm: WorkspaceManager):
        self.wm = wm

    def load_project(
        self, project_path: Path
    ) -> Tuple[
        str, Metadata | None, list[tuple[str, str]], Any | None, AIAnalysis | None
    ]:
        """Loads an existing project or initializes a new one."""
        project_id = self.wm.get_project_id(project_path)
        metadata, history, fingerprint, analysis = self.wm.load_project_state(
            project_id
        )
        return project_id, metadata, history, fingerprint, analysis

    def save_state(
        self,
        project_id: str,
        metadata: Metadata,
        chat_history: list[tuple[str, str]],
        fingerprint: Any | None,
        analysis: AIAnalysis | None,
    ):
        """Persists the current state to the workspace."""
        if project_id:
            self.wm.save_project_state(
                project_id,
                metadata,
                chat_history,
                fingerprint,
                analysis,
            )
