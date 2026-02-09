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

    if UIState.is_loading_inventory and not UIState.inventory_cache:
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
            ui.button(
                _("Go to Analysis"),
                on_click=lambda: UIState.main_tabs.set_value(UIState.analysis_tab),
            ).props("outline")
        return

    manifest = ctx.pkg_mgr.get_manifest(project_id)
    inventory = UIState.inventory_cache

    with ui.column().classes("w-full gap-4 h-full p-4"):
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column():
                ui.label(_("Package Content Editor")).classes("text-2xl font-bold")
                ui.label(
                    _(
                        "Select files to include in the final RODBUK package. Changes are saved automatically."
                    )
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

        column_defs = [
            {
                "headerName": _("Include"),
                "field": "included",
                "checkboxSelection": True,
                "showDisabledCheckboxes": True,
                "width": 100,
            },
            {
                "headerName": _("File Path"),
                "field": "path",
                "filter": "agTextColumnFilter",
                "flex": 1,
            },
            {
                "headerName": _("Size"),
                "field": "size",
                "sortable": True,
                "width": 120,
                "comparator": "valueGetter: node.data.size_val",
            },
            {
                "headerName": _("Inclusion Reason"),
                "field": "reason",
                "width": 180,
                "filter": "agTextColumnFilter",
            },
        ]

        # The Grid
        grid = ui.aggrid(
            {
                "columnDefs": column_defs,
                "rowData": UIState.grid_rows,
                "rowSelection": "multiple",
                "stopEditingWhenCellsLoseFocus": True,
                "pagination": True,
                "paginationPageSize": 50,
            }
        ).classes("w-full h-[600px] shadow-sm")

        # Initial selection
        grid.options["selected_keys"] = [
            i for i, f in enumerate(UIState.grid_rows) if f["included"]
        ]

        async def handle_selection_change():
            selected_rows = await grid.get_selected_rows()
            selected_paths = {row["path"] for row in selected_rows}

            new_force_include = []
            new_force_exclude = []

            for item in UIState.inventory_cache:
                rel_path = item["path"]
                is_proto_excluded = item["is_proto_excluded"]
                is_now_selected = rel_path in selected_paths

                if is_proto_excluded:
                    if is_now_selected:
                        new_force_include.append(rel_path)
                else:
                    if not is_now_selected:
                        new_force_exclude.append(rel_path)

            manifest.force_include = new_force_include
            manifest.force_exclude = new_force_exclude
            ctx.pkg_mgr.save_manifest(manifest)

            # Update cache
            for item in UIState.inventory_cache:
                rel_path = item["path"]
                if rel_path in manifest.force_include:
                    item["included"] = True
                    item["reason"] = "👤 User (Forced)"
                elif rel_path in manifest.force_exclude:
                    item["included"] = False
                    item["reason"] = "👤 User (Excluded)"
                else:
                    item["included"] = not item["is_proto_excluded"]
                    item["reason"] = (
                        "📜 Protocol" if item["is_proto_excluded"] else "✅ Default"
                    )

            ctx.refresh_all()

        grid.on("selectionChanged", handle_selection_change)


async def handle_refresh_inventory(ctx: AppContext):
    if not ScanState.current_path:
        ui.notify(_("Please select a project first."), type="warning")
        return

    resolved_path = Path(ScanState.current_path).expanduser()
    import threading

    ScanState.stop_event = threading.Event()
    ScanState.is_scanning = True
    ui.notify(_("Refreshing file list..."))

    def update_progress(msg, full_path="", short_path=""):
        ScanState.progress = msg

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
    ui.notify(_("File list updated."), type="positive")


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
