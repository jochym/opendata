import asyncio
import logging
from pathlib import Path
from collections import defaultdict
from nicegui import ui
from opendata.ui.state import ScanState, UIState
from opendata.ui.context import AppContext
from opendata.utils import format_size

logger = logging.getLogger("opendata.ui.inventory_logic")


def build_folder_index(inventory: list):
    """
    Builds a flat index of folder contents and statistics for fast UI rendering.
    O(N * Depth) complexity, which is fast enough for Python backend.
    """
    children_map = defaultdict(list)
    stats = defaultdict(
        lambda: {"total": 0, "included": 0, "size": 0, "included_size": 0}
    )

    # Process files
    for item in inventory:
        path_str = item["path"]
        p = Path(path_str)
        parent = str(p.parent)
        if parent == ".":
            parent = ""

        # Add file to parent's children list
        children_map[parent].append(
            {
                "type": "file",
                "name": p.name,
                "path": path_str,
                "size": item["size"],
                "included": item["included"],
                "reason": item["reason"],
            }
        )

        # Update stats recursively up to root
        is_included = item["included"]
        size = item["size"]

        current_path = parent
        while True:
            s = stats[current_path]
            s["total"] += 1
            s["size"] += size
            if is_included:
                s["included"] += 1
                s["included_size"] += size

            if not current_path:  # We reached root
                break

            # Go up one level
            cpp = Path(current_path)
            current_path = str(cpp.parent)
            if current_path == ".":
                current_path = ""

    # Process folders (add them as children to their parents)
    # We get all folder paths from the stats keys (since every folder with files has an entry)
    all_folders = sorted(stats.keys())

    for folder_path in all_folders:
        if not folder_path:  # Skip root
            continue

        p = Path(folder_path)
        parent = str(p.parent)
        if parent == ".":
            parent = ""

        # Determine inclusion state for folder icon
        s = stats[folder_path]
        state = "unchecked"
        if s["included"] == 0:
            state = "unchecked"
        elif s["included"] == s["total"]:
            state = "checked"
        else:
            state = "indeterminate"

        # Add folder to its parent's children list
        # Check if already added to avoid duplicates (though stats keys are unique)
        exists = False
        for child in children_map[parent]:
            if child["type"] == "folder" and child["path"] == folder_path:
                exists = True
                break

        if not exists:
            children_map[parent].append(
                {
                    "type": "folder",
                    "name": p.name,
                    "path": folder_path,
                    "state": state,
                    "total_files": s["total"],
                    "included_files": s["included"],
                    "size": s["size"],
                }
            )

    # Sort children: Folders first, then Files
    for parent, children in children_map.items():
        children.sort(key=lambda x: (x["type"] == "file", x["name"].lower()))

    return children_map, stats


async def load_inventory_background(ctx: AppContext):
    """Load inventory in background with lock to prevent concurrent runs."""
    if not ctx.agent.project_id:
        return

    if ctx.session.inventory_lock:
        logger.info("Inventory lock active, skipping background load")
        return

    ctx.session.inventory_lock = True
    ctx.session.is_loading_inventory = True

    # Wait a bit to let the initial project load UI stabilize
    await asyncio.sleep(0.3)

    try:
        project_path = Path(ScanState.current_path)
        if not project_path.exists():
            logger.warning(f"Project path does not exist: {project_path}")
            ctx.session.is_loading_inventory = False
            ctx.session.inventory_lock = False
            return

        logger.info(f"Loading inventory for {ctx.agent.project_id}...")
        manifest = ctx.pkg_mgr.get_manifest(ctx.agent.project_id)

        # Get field protocol from agent (reads from project config, not metadata)
        field_name = ctx.agent._get_effective_field()

        effective = ctx.pm.resolve_effective_protocol(ctx.agent.project_id, field_name)
        protocol_excludes = effective.get("exclude", [])
        logger.info(
            f"Loading inventory for UI. Effective excludes: {protocol_excludes}"
        )

        inventory = await asyncio.to_thread(
            ctx.pkg_mgr.get_inventory_for_ui, project_path, manifest, protocol_excludes
        )

        ctx.session.inventory_cache = inventory

        # Prepare UI data (summary and explorer index) in background thread
        def prepare_ui_data():
            included = [f for f in inventory if f["included"]]
            count = len(included)
            total_count = len(inventory)
            size = sum(f["size"] for f in included)

            # Build Explorer Index
            children_map, stats = build_folder_index(inventory)

            return count, total_count, size, children_map, stats

        count, total_count, size, children_map, stats = await asyncio.to_thread(
            prepare_ui_data
        )

        ctx.session.total_files_count = count
        ctx.session.inventory_total_count = total_count
        ctx.session.total_files_size = size
        ctx.session.folder_children_map = children_map
        ctx.session.folder_stats = stats

        ctx.session.last_inventory_project = ctx.agent.project_id

        # Always refresh preview and package (if initialized)
        try:
            ctx.refresh("preview")
            ctx.refresh("package")
        except RuntimeError:
            pass
        logger.info(f"Inventory load complete for {ctx.agent.project_id}")

    except Exception as e:
        logger.error(f"Failed to load inventory: {e}")
        import traceback

        traceback.print_exc()
    finally:
        ctx.session.is_loading_inventory = False
        ctx.session.inventory_lock = False
