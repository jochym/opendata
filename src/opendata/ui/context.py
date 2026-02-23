from dataclasses import dataclass, field
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from opendata.workspace import WorkspaceManager
from opendata.packager import PackagingService
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.ai.service import AIService
from opendata.protocols.manager import ProtocolManager
from opendata.packaging.manager import PackageManager
from opendata.models import UserSettings


@dataclass
class SessionState:
    """Project-specific UI state that is cleared when loading a new project."""

    inventory_cache: list[dict[str, Any]] = field(default_factory=list)
    last_inventory_project: str = ""
    is_loading_inventory: bool = False
    inventory_lock: bool = False
    last_refresh_time: float = 0.0
    pending_refresh: bool = False
    _is_refreshing_global: bool = False
    is_project_loading: bool = False
    total_files_count: int = 0
    total_files_size: int = 0
    inventory_total_count: int = 0
    inventory_total_size: int = 0
    grid_rows: list[dict[str, Any]] = field(default_factory=list)
    show_only_included: bool = False
    show_suggestions_banner: bool = True
    explorer_path: str = ""
    extension_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    folder_children_map: dict[str, set[str]] = field(default_factory=dict)
    folder_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    ai_stop_event: Optional[threading.Event] = None

    def reset(self):
        """Resets session state to default values without replacing the object."""
        self.inventory_cache = []
        self.last_inventory_project = ""
        self.is_loading_inventory = False
        self.inventory_lock = False
        self.last_refresh_time = 0.0
        self.pending_refresh = False
        self._is_refreshing_global = False
        self.is_project_loading = False
        self.total_files_count = 0
        self.total_files_size = 0
        self.inventory_total_count = 0
        self.inventory_total_size = 0
        self.grid_rows = []
        self.show_only_included = False
        self.show_suggestions_banner = True
        self.explorer_path = ""
        self.extension_stats = {}
        self.folder_children_map = {}
        self.folder_stats = {}
        self.ai_stop_event = None


@dataclass
class AppContext:
    wm: WorkspaceManager
    agent: ProjectAnalysisAgent
    ai: AIService
    pm: ProtocolManager
    pkg_mgr: PackageManager
    packaging_service: PackagingService
    settings: UserSettings

    port: int = 8080

    # Encapsulated session state
    session: SessionState = field(default_factory=SessionState)

    # Session-specific UI components
    main_tabs: Any = None
    analysis_tab: Any = None
    package_tab: Any = None
    preview_tab: Any = None

    # Callback to refresh all UI components
    refresh_all: Callable[[], None] = field(default_factory=lambda: lambda: None)

    # Storage for specific refreshable components
    _refreshables: Dict[str, Any] = field(default_factory=dict)

    def register_refreshable(self, name: str, func: Any):
        self._refreshables[name] = func

    def refresh(self, name: str):
        if name in self._refreshables:
            self._refreshables[name].refresh()
