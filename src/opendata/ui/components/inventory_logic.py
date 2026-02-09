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

    # Clear old cache to prevent cross-project pollution
    if UIState.last_inventory_project != ctx.agent.project_id:
        UIState.inventory_cache = []
        UIState.grid_rows = []
        UIState.total_files_count = 0
        UIState.total_files_size = 0
        ctx.refresh("package")
        ctx.refresh("preview")

    UIState.inventory_lock = True
    UIState.is_loading_inventory = True

    # Wait a bit to let the initial project load UI stabilize
    await asyncio.sleep(0.3)

    try:
        project_path = Path(ScanState.current_path)
        if not project_path.exists():
            logger.warning(f"Project path does not exist: {project_path}")
            UIState.is_loading_inventory = False
            UIState.inventory_lock = False
            return

        logger.info(f"Loading inventory for {ctx.agent.project_id}...")
        manifest = ctx.pkg_mgr.get_manifest(ctx.agent.project_id)

        field_name = None
        if ctx.agent.current_metadata.science_branches_mnisw:
            # Normalize for protocol lookup
            field_name = (
                ctx.agent.current_metadata.science_branches_mnisw[0]
                .lower()
                .replace(" ", "_")
            )

        effective = ctx.pm.resolve_effective_protocol(ctx.agent.project_id, field_name)
        protocol_excludes = effective.get("exclude", [])
        logger.info(
            f"Loading inventory for UI. Effective excludes: {protocol_excludes}"
        )

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
        print(f"[DEBUG] Inventory prepared. Rows: {len(rows)}, Count: {count}")

        UIState.total_files_count = count
        UIState.total_files_size = size
        # Update rows list in place or replace it cleanly
        UIState.grid_rows.clear()
        UIState.grid_rows.extend(rows)
        UIState.last_inventory_project = ctx.agent.project_id

        # Always refresh preview and package (if initialized)
        ctx.refresh("preview")
        ctx.refresh("package")
        print("[DEBUG] Refresh calls sent to preview and package")
        logger.info(f"Inventory load complete for {ctx.agent.project_id}")

    except Exception as e:
        logger.error(f"Failed to load inventory: {e}")
    finally:
        UIState.is_loading_inventory = False
        UIState.inventory_lock = False
