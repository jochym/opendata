import asyncio
import logging
from pathlib import Path
from nicegui import ui
from opendata.ui.state import ScanState, UIState
from opendata.ui.context import AppContext
from opendata.utils import format_size

logger = logging.getLogger("opendata.ui.inventory_logic")


async def load_inventory_background(ctx: AppContext):
    """Load inventory in background with lock to prevent concurrent runs."""
    if not ctx.agent.project_id:
        return

    if UIState.inventory_lock:
        logger.info("Inventory lock active, skipping background load")
        return

    UIState.inventory_lock = True
    UIState.is_loading_inventory = True

    # Wait a bit to let the initial project load UI stabilize
    await asyncio.sleep(0.5)

    try:

        def should_refresh():
            # Only refresh if the package tab is actually visible
            return UIState.main_tabs and UIState.main_tabs.value == UIState.package_tab

        project_path = Path(ScanState.current_path)
        if not project_path.exists():
            logger.warning(f"Project path does not exist: {project_path}")
            return

        logger.info(f"Loading inventory for {ctx.agent.project_id}...")
        manifest = ctx.pkg_mgr.get_manifest(ctx.agent.project_id)

        field_name = (
            ctx.agent.current_metadata.science_branches_mnisw[0]
            if ctx.agent.current_metadata.science_branches_mnisw
            else None
        )

        effective = ctx.pm.resolve_effective_protocol(ctx.agent.project_id, field_name)
        protocol_excludes = effective.get("exclude", [])

        inventory = await asyncio.to_thread(
            ctx.pkg_mgr.get_inventory_for_ui, project_path, manifest, protocol_excludes
        )

        UIState.inventory_cache = inventory

        # Calculate summary and grid rows for UI in background
        def prepare_ui_data():
            included = [f for f in inventory if f["included"]]
            count = len(included)
            size = sum(f["size"] for f in included)
            rows = [
                {
                    "included": item["included"],
                    "path": item["path"],
                    "size_val": item["size"],
                    "size": format_size(item["size"]),
                    "reason": item["reason"],
                }
                for item in inventory
            ]
            return count, size, rows

        count, size, rows = await asyncio.to_thread(prepare_ui_data)

        UIState.total_files_count = count
        UIState.total_files_size = size
        UIState.grid_rows = rows
        UIState.last_inventory_project = ctx.agent.project_id

        if should_refresh():
            logger.info("Refreshing package tab after inventory load")
            ctx.refresh("package")
            ctx.refresh("preview")
        else:
            logger.info("Inventory loaded to cache, package tab not visible")
            # Still refresh preview if it might be visible
            ctx.refresh("preview")

    except Exception as e:
        logger.error(f"Failed to load inventory: {e}")
    finally:
        UIState.is_loading_inventory = False
        UIState.inventory_lock = False
