import asyncio
import logging
from pathlib import Path
from nicegui import ui
from opendata.i18n.translator import _
from opendata.ui.state import ScanState, UIState
from opendata.ui.context import AppContext
from opendata.utils import format_size
from opendata.ui.components.inventory_logic import load_inventory_background

logger = logging.getLogger("opendata.ui.package")


@ui.refreshable
def render_package_tab(ctx: AppContext):
    # Package Content Editor
    if not ctx.agent.project_id:
        with ui.card().classes("w-full p-8 shadow-md"):
            with ui.column().classes("w-full items-center p-8"):
                ui.icon("folder_open", size="lg", color="grey-400")
                ui.label(_("Please select and open a project first.")).classes(
                    "text-orange-600 font-bold"
                )
        return

    # Optimization: Don't render full grid if not on this tab (handled by tab_panels, but refresh() can still trigger it)
    if UIState.main_tabs and UIState.main_tabs.value != UIState.package_tab:
        ui.label(_("Loading package data...")).classes("p-8 animate-pulse")
        return

    if UIState.last_inventory_project != ctx.agent.project_id:
        if not UIState.is_loading_inventory:
            asyncio.create_task(load_inventory_background(ctx))

    # ONLY block with big spinner when reading from DB (initial load)
    if (
        UIState.is_loading_inventory
        and not UIState.inventory_cache
        and not UIState.grid_rows
    ):
        with ui.column().classes("w-full items-center justify-center p-20 gap-4"):
            ui.spinner(size="xl")
            ui.label(_("Reading project inventory from database...")).classes(
                "text-slate-500 animate-pulse"
            )
        return

    # Use a local variable to satisfy the type checker after the early return above
    project_id: str = ctx.agent.project_id

    if not UIState.inventory_cache:
        with ui.column().classes("w-full items-center justify-center p-20 gap-4"):
            ui.icon("inventory", size="xl", color="grey-400")
            ui.label(_("No file inventory found.")).classes("text-orange-600 font-bold")
            ui.markdown(
                _(
                    "Please click **Analyze Directory** in the Analysis tab to list project files."
                )
            ).classes("text-sm text-slate-500")
            with ui.row().classes("gap-2"):
                ui.button(
                    _("Go to Analysis"),
                    on_click=lambda: UIState.main_tabs.set_value(UIState.analysis_tab),
                ).props("outline")
                ui.button(
                    _("Scan Project Inventory"),
                    icon="search",
                    on_click=lambda: handle_refresh_inventory(ctx),
                ).props("elevated color=primary")
        return

    manifest = ctx.pkg_mgr.get_manifest(project_id)
    inventory = UIState.inventory_cache

    with ui.column().classes("w-full gap-4 h-[calc(100vh-130px)] p-4"):
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column():
                ui.label(_("Package Content Editor")).classes("text-2xl font-bold")
                ui.label(
                    _("Overview of files included in the final RODBUK package.")
                ).classes("text-sm text-slate-500")

            with ui.row().classes("gap-2"):
                ui.button(
                    _("Refresh File List"),
                    icon="refresh",
                    on_click=lambda: handle_refresh_inventory(ctx),
                ).props("outline color=primary").bind_visibility_from(
                    ScanState, "is_scanning", backward=lambda x: not x
                )
                ui.button(
                    _("Reset to Defaults"),
                    icon="settings_backup_restore",
                    on_click=lambda: handle_reset(ctx),
                ).props("outline color=grey-7")

        # Progress for background tasks
        if ScanState.is_scanning or UIState.is_loading_inventory:
            with ui.row().classes(
                "w-full items-center gap-2 p-2 bg-blue-50 border border-blue-100 rounded"
            ):
                ui.spinner(size="xs")
                ui.label().bind_text_from(ScanState, "progress").classes(
                    "text-xs text-blue-700"
                )
                if ScanState.is_scanning:
                    ui.label().bind_text_from(ScanState, "short_path").classes(
                        "text-[10px] text-blue-400 truncate flex-grow"
                    )

        ui.label(f"Rows in UIState: {len(UIState.grid_rows)}").classes(
            "text-[10px] text-slate-400"
        )
        # Statistics summary
        included_files = [f for f in inventory if f["included"]]
        total_size = sum(f["size"] for f in included_files)
        with ui.row().classes("w-full gap-8 p-3 bg-slate-50 rounded-lg border"):
            ui.label(
                _("Included: {count} files").format(count=len(included_files))
            ).classes("font-bold")
            ui.label(_("Total Size: {size}").format(size=format_size(total_size)))
            ui.label(
                _("Excluded: {count} files").format(
                    count=len(inventory) - len(included_files)
                )
            ).classes("text-slate-400")

        # Simplified High-Level View
        ui.label(_("Project Root Contents:")).classes(
            "text-sm font-bold text-slate-700 mt-2"
        )

        with ui.scroll_area().classes(
            "w-full flex-grow border rounded-lg bg-white p-2"
        ):
            root_path = Path(ScanState.current_path)

            # Resolve effective excludes for visual filtering
            field_name = None
            if ctx.agent.current_metadata.science_branches_mnisw:
                field_name = (
                    ctx.agent.current_metadata.science_branches_mnisw[0]
                    .lower()
                    .replace(" ", "_")
                )
            effective = ctx.pm.resolve_effective_protocol(
                ctx.agent.project_id, field_name
            )
            excludes = effective.get("exclude", [])

            try:
                # Sort: Directories first, then files
                items = sorted(
                    list(root_path.iterdir()),
                    key=lambda p: (not p.is_dir(), p.name.lower()),
                )

                from opendata.utils import is_path_excluded

                with ui.list().classes("w-full").props("dense"):
                    for item in items:
                        if item.name.startswith("."):
                            continue

                        # Apply visual exclusion check
                        rel_path_str = item.name  # Root items
                        if is_path_excluded(rel_path_str, item.name, excludes):
                            continue

                        is_dir = item.is_dir()

                        with ui.item().classes("q-py-xs"):
                            with ui.item_section().props("side"):
                                ui.icon(
                                    "folder" if is_dir else "description",
                                    color="primary" if is_dir else "grey-7",
                                )
                            with ui.item_section():
                                ui.item_label(item.name).classes("text-sm")
                                if not is_dir:
                                    size = format_size(item.stat().st_size)
                                    ui.item_label(size).props("caption").classes(
                                        "text-[10px]"
                                    )
            except Exception as e:
                ui.label(
                    _("Error reading directory: {error}").format(error=str(e))
                ).classes("text-red-500 text-xs")


async def handle_refresh_inventory(ctx: AppContext):
    if not ScanState.current_path:
        ui.notify(_("Please select a project first."), type="warning")
        return

    resolved_path = Path(ScanState.current_path).expanduser()
    import threading

    # DO NOT clear cache here - it causes UI to flip to "No inventory" state
    # Instead, we just mark as scanning and refresh to show progress bar
    ScanState.stop_event = threading.Event()
    ScanState.is_scanning = True
    ui.notify(_("Refreshing file list..."))
    ctx.refresh("package")

    def update_progress(msg, full_path="", short_path=""):
        ScanState.progress = msg
        ScanState.full_path = full_path
        ScanState.short_path = short_path
        # Removed periodic refresh to prevent list flickering during scan

    await asyncio.to_thread(
        ctx.agent.refresh_inventory,
        resolved_path,
        update_progress,
        stop_event=ScanState.stop_event,
    )

    ScanState.is_scanning = False
    ScanState.stop_event = None

    # Force cache reload
    UIState.last_inventory_project = ""
    await load_inventory_background(ctx)

    # Safely notify
    try:
        ui.notify(_("File list updated."), type="positive")
    except Exception:
        pass


async def handle_reset(ctx: AppContext):
    if not ctx.agent.project_id:
        return
    pid: str = ctx.agent.project_id
    manifest = ctx.pkg_mgr.get_manifest(pid)
    manifest.force_include = []
    manifest.force_exclude = []
    ctx.pkg_mgr.save_manifest(manifest)
    ui.notify(_("Selection reset to protocol defaults."), type="info")
    asyncio.create_task(load_inventory_background(ctx))
