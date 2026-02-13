import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from opendata.models import ProjectFingerprint, Metadata
from opendata.utils import scan_project_lazy, walk_project_files, format_size
from opendata.workspace import WorkspaceManager

logger = logging.getLogger("opendata.agents.scanner")


class ScannerService:
    """Service for project file scanning and inventory management."""

    def __init__(self, wm: WorkspaceManager):
        self.wm = wm

    def refresh_inventory(
        self,
        project_id: str,
        project_dir: Path,
        exclude_patterns: list[str],
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
        stop_event: Optional[Any] = None,
    ) -> Tuple[ProjectFingerprint, list[dict]]:
        """
        Performs a fast file scan and updates the SQLite inventory.
        """
        # 1. Quick fingerprint update
        res = scan_project_lazy(
            project_dir,
            progress_callback=progress_callback,
            stop_event=stop_event,
            exclude_patterns=exclude_patterns,
        )
        fingerprint, full_files = res

        if stop_event and stop_event.is_set():
            return fingerprint, []

        # 2. Update SQLite Inventory
        try:
            from opendata.storage.project_db import ProjectInventoryDB

            db = ProjectInventoryDB(self.wm.get_project_db_path(project_id))
            db.update_inventory(full_files)
        except Exception as e:
            logger.error(f"Failed to refresh inventory in SQLite: {e}", exc_info=True)

        return fingerprint, full_files

    def run_heuristics(
        self,
        project_dir: Path,
        fingerprint: ProjectFingerprint,
        exclude_patterns: list[str],
        registry: Any,
        progress_callback: Optional[Callable[[str, str, str], None]] = None,
        stop_event: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Runs heuristic extractors on the project files."""
        heuristics_data: Dict[str, Any] = {}
        total_files = fingerprint.file_count
        current_file_idx = 0
        total_size_str = format_size(fingerprint.total_size_bytes)

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
                        f"Analyzing {p.name}...",
                    )

                # Trigger extractors
                extractors = registry.get_extractors_for(p)
                for ext in extractors:
                    try:
                        partial = ext.extract(p)
                        # Merge logic could go here or in the agent
                        # For now, we just return the raw data collected
                        if ext.__class__.__name__ not in heuristics_data:
                            heuristics_data[ext.__class__.__name__] = []
                        heuristics_data[ext.__class__.__name__].append(partial)
                    except Exception as e:
                        logger.warning(
                            f"Extractor {ext.__class__.__name__} failed on {p}: {e}"
                        )

        return heuristics_data
