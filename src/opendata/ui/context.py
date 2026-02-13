from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.ai.service import AIService
from opendata.models import UserSettings
from opendata.packager import PackagingService
from opendata.packaging.manager import PackageManager
from opendata.protocols.manager import ProtocolManager
from opendata.workspace import WorkspaceManager


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

    # Session-specific UI components
    main_tabs: Any = None
    analysis_tab: Any = None
    package_tab: Any = None
    preview_tab: Any = None

    # Callback to refresh all UI components
    refresh_all: Callable[[], None] = field(default_factory=lambda: lambda: None)

    # Storage for specific refreshable components
    _refreshables: dict[str, Any] = field(default_factory=dict)

    def register_refreshable(self, name: str, func: Any):
        self._refreshables[name] = func

    def refresh(self, name: str):
        if name in self._refreshables:
            self._refreshables[name].refresh()
