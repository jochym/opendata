import logging
import threading
from typing import Any, Dict, List, Optional, Literal, Set

logger = logging.getLogger("opendata.ui.state")


class UIState:
    main_tabs: Any = None
    analysis_tab: Any = None
    package_tab: Any = None
    preview_tab: Any = None
    inventory_cache: list[dict[str, Any]] = []
    last_inventory_project: str = ""
    is_loading_inventory: bool = False
    # Performance & Stability state
    inventory_lock: bool = False
    last_refresh_time: float = 0.0
    pending_refresh: bool = False
    _is_refreshing_global: bool = False
    is_project_loading: bool = False
    total_files_count: int = 0  # Count of included files
    total_files_size: int = 0  # Total size of included files
    inventory_total_count: int = 0  # Total count of all files in inventory
    grid_rows: list[dict[str, Any]] = []
    show_only_included: bool = False
    show_suggestions_banner: bool = True

    # File Explorer State
    explorer_path: str = ""  # Current path being viewed (relative to project root)
    folder_children_map: dict[
        str, list[dict[str, Any]]
    ] = {}  # Cache for folder contents
    folder_stats: dict[
        str, dict[str, int]
    ] = {}  # Stats for tri-state checkboxes (total, included, size)

    ai_stop_event: Optional[threading.Event] = None


class ScanState:
    is_scanning = False
    is_processing_ai = False
    agent_mode: Literal["metadata", "curator"] = "metadata"
    progress = ""
    short_path = ""
    full_path = ""
    progress_label: Any = None
    short_path_label: Any = None
    current_path = ""
    stop_event: Any = None
    qr_dialog: Any = None
