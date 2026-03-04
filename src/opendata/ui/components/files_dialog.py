"""File Management Dialog component for selecting and managing important files."""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from nicegui import ui
from opendata.i18n.translator import _
from opendata.ui.context import AppContext
from opendata.models import FileSuggestion

logger = logging.getLogger("opendata.ui.files_dialog")


def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    size_float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_float < 1024:
            return (
                f"{size_float:.1f} {unit}"
                if unit != "B"
                else f"{int(size_float)} {unit}"
            )
        size_float /= 1024
    return f"{size_float:.1f} TB"


@ui.refreshable
def render_selected_files_list(ctx: AppContext):
    """Render the list of selected files in the dialog."""
    suggestions = (
        ctx.agent.current_analysis.file_suggestions
        if ctx.agent.current_analysis
        else []
    )

    if not suggestions:
        ui.label(_("No files selected yet. Use the explorer below.")).classes(
            "text-sm text-slate-500 italic p-2"
        )
        return

    CATEGORIES = {
        "main_article": _("Article"),
        "visualization_scripts": _("Scripts"),
        "data_files": _("Data"),
        "documentation": _("Docs"),
        "other": _("Other"),
    }

    REASON_MAP = {
        "Main article/paper": "main_article",
        "Visualization scripts": "visualization_scripts",
        "Data files": "data_files",
        "Documentation": "documentation",
        "Supporting file": "other",
    }

    with ui.column().classes("w-full gap-1"):
        for fs in suggestions:
            with ui.row().classes(
                "w-full items-center gap-2 p-2 bg-slate-50 rounded border border-slate-200"
            ):
                # Role dropdown - use keys as values, labels as display
                current_cat = "other"
                for reason, cat in REASON_MAP.items():
                    if reason in fs.reason:
                        current_cat = cat
                        break

                # Capture path for select change
                def make_select_handler(p):
                    return lambda e: (
                        ctx.agent.update_file_role(p, e.value),
                        render_selected_files_list.refresh(),
                    )

                # Use category KEYS as values (not translated labels)
                ui.select(
                    options=CATEGORIES,
                    value=current_cat,
                    on_change=make_select_handler(fs.path),
                ).props("dense size=sm flat").classes("w-28 text-sm")

                ui.label(fs.path).classes(
                    "flex-grow text-sm font-mono truncate cursor-help"
                ).tooltip(fs.path)

                # Capture path for remove click
                def make_remove_handler(p):
                    return lambda _: (
                        ctx.agent.remove_significant_file(p),
                        render_selected_files_list.refresh(),
                        render_dialog_explorer.refresh(),
                    )

                ui.button(
                    icon="close",
                    on_click=make_remove_handler(fs.path),
                ).props("flat dense color=red size=sm")


@ui.refreshable
def render_dialog_explorer(ctx: AppContext):
    """Render the file explorer section of the dialog."""
    if not ctx.session.inventory_cache:
        with ui.column().classes("w-full items-center justify-center p-4"):
            ui.label(_("No inventory. Please scan the project first.")).classes(
                "text-sm text-slate-400 italic"
            )
        return

    current_path = ctx.session.explorer_path
    children = ctx.session.folder_children_map.get(current_path, [])

    # Breadcrumbs
    with ui.row().classes("w-full items-center gap-1 p-2 bg-slate-100 rounded mb-2"):
        ui.button(icon="home", on_click=lambda: navigate_to(ctx, "")).props(
            "flat dense round size=xs color=primary"
        )

        parts = Path(current_path).parts if current_path else []
        accumulated = ""
        for i, part in enumerate(parts):
            ui.label("/").classes("text-slate-400")
            if i > 0:
                accumulated = str(Path(accumulated) / part)
            else:
                accumulated = part

            if i == len(parts) - 1:
                ui.label(part).classes("font-bold")
            else:

                def make_nav(p):
                    return lambda: navigate_to(ctx, p)

                ui.button(part, on_click=make_nav(accumulated)).props(
                    "flat dense no-caps size=xs"
                ).classes("p-0 min-h-0")

    # File List
    with ui.scroll_area().classes("h-64 w-full bg-white border rounded"):
        with ui.column().classes("w-full gap-0"):
            if not children:
                ui.label(_("Folder is empty")).classes(
                    "text-sm text-slate-400 p-4 text-center"
                )

            # Limit number of items to avoid WebSocket "Message too long" errors
            display_items = children[: ctx.session.explorer_limit]

            if len(children) > ctx.session.explorer_limit:
                ui.label(
                    _("Showing first {n} items of {total}").format(
                        n=ctx.session.explorer_limit, total=len(children)
                    )
                ).classes(
                    "text-[10px] text-orange-600 bg-orange-50 w-full p-1 text-center font-bold border-b border-orange-100"
                )

            for item in display_items:
                is_selected = any(
                    fs.path == item["path"]
                    for fs in (
                        ctx.agent.current_analysis.file_suggestions
                        if ctx.agent.current_analysis
                        else []
                    )
                )

                # Item row
                row = ui.row().classes(
                    "w-full items-center gap-2 px-2 py-1 hover:bg-blue-50 border-b border-slate-50"
                )
                if item["type"] == "folder":

                    def make_folder_handler(p):
                        return lambda _: navigate_to(ctx, p)

                    row.on("click", make_folder_handler(item["path"]))
                    row.classes("cursor-pointer")

                with row:
                    # Icon
                    icon = "folder" if item["type"] == "folder" else "description"
                    color = "amber-400" if item["type"] == "folder" else "slate-400"
                    ui.icon(icon, color=color, size="sm")

                    # Name
                    if item["type"] == "folder":
                        ui.label(item["name"]).classes(
                            "text-sm flex-grow py-1 truncate"
                        )
                    else:
                        # Capture path for file click
                        def make_file_handler(p):
                            # First file defaults to 'main_article', subsequent to 'other'
                            is_first = not (
                                ctx.agent.current_fingerprint
                                and ctx.agent.current_fingerprint.significant_files
                            )
                            category = "main_article" if is_first else "other"
                            return lambda _: (
                                ctx.agent.add_significant_file(p, category),
                                render_selected_files_list.refresh(),
                                render_dialog_explorer.refresh(),
                            )

                        btn = (
                            ui.button(
                                item["name"],
                                on_click=make_file_handler(item["path"]),
                            )
                            .props("flat dense no-caps size=md")
                            .classes("text-sm text-left flex-grow p-0 min-h-0")
                        )
                        if is_selected:
                            btn.disable()
                            ui.icon("check", color="green", size="sm")

            if len(children) > ctx.session.explorer_limit:

                async def load_more():
                    ctx.session.explorer_limit += 100
                    render_dialog_explorer.refresh()

                ui.button(
                    _("Load More (+100)"),
                    on_click=load_more,
                ).props("flat dense color=primary").classes("w-full py-2")


def navigate_to(ctx: AppContext, path: str):
    """Updates the explorer path and refreshes the dialog."""
    logger.info(f"Navigating to: {path}")
    ctx.session.explorer_path = path
    ctx.session.explorer_limit = 100
    render_dialog_explorer.refresh()


def open_file_management_dialog(ctx: AppContext):
    """Opens the file management dialog."""
    # Ensure inventory is loaded before opening dialog
    if not ctx.session.inventory_cache and ctx.agent.project_id:
        from opendata.ui.components.inventory_logic import load_inventory_background
        import asyncio

        # Trigger background load if not already loaded
        asyncio.create_task(load_inventory_background(ctx))

    with (
        ui.dialog().props("persistent") as dialog,
        ui.card().classes("w-[600px] h-[700px] flex flex-col p-0 overflow-hidden"),
    ):
        # Header
        with ui.row().classes(
            "w-full items-center justify-between bg-slate-800 text-white p-3 shrink-0"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.icon("fact_check")
                ui.label(_("Manage Important Files")).classes("text-lg font-bold")
            ui.button(
                icon="close",
                on_click=lambda: (
                    dialog.close(),
                    ctx.refresh("file_selection_summary"),
                ),
            ).props("flat dense color=white")

        # Body - Split into selected files and explorer
        with ui.scroll_area().classes("flex-grow w-full p-3"):
            with ui.column().classes("w-full gap-3"):
                # Selected Files Section
                with ui.card().classes("w-full p-2 bg-white shadow-sm"):
                    ui.label(_("Selected Files")).classes(
                        "text-sm font-bold text-slate-700 mb-2"
                    )
                    # Force refresh to ensure we have latest data
                    render_selected_files_list(ctx)

                # Divider
                ui.separator()

                # Explorer Section
                with ui.card().classes("w-full p-2 bg-white shadow-sm"):
                    ui.label(_("Project Explorer")).classes(
                        "text-sm font-bold text-slate-700 mb-2"
                    )
                    ui.label(_("Click files to add them to the selection.")).classes(
                        "text-xs text-slate-500 mb-2"
                    )
                    render_dialog_explorer(ctx)

        # Footer
        with ui.row().classes(
            "w-full justify-end p-3 gap-2 shrink-0 border-t bg-slate-50"
        ):
            ui.button(
                _("Close"),
                on_click=lambda: (
                    dialog.close(),
                    ctx.refresh("file_selection_summary"),
                ),
            ).props("elevated color=primary")

    # Force refresh the list when dialog opens to ensure fresh data
    render_selected_files_list.refresh()
    dialog.open()


@ui.refreshable
def render_file_selection_summary(ctx: AppContext):
    """Render a compact summary of file selection with button to open editor."""
    suggestions = (
        ctx.agent.current_analysis.file_suggestions
        if ctx.agent.current_analysis
        else []
    )

    # Calculate stats
    selected_count = len(suggestions)
    selected_size = 0
    if ctx.agent.current_fingerprint:
        project_dir = Path(ctx.agent.current_fingerprint.root_path)
        for fs in suggestions:
            p = project_dir / fs.path
            if p.exists():
                selected_size += p.stat().st_size

    size_str = format_size(selected_size) if selected_size > 0 else "0 B"

    with ui.card().classes("w-full p-2 shadow-sm border border-slate-200"):
        with ui.row().classes("w-full items-center gap-2"):
            ui.icon("fact_check", color="primary", size="md")

            with ui.column().classes("flex-grow gap-0"):
                ui.label(
                    _("Important Files: {count} selected ({size})").format(
                        count=selected_count, size=size_str
                    )
                ).classes("text-sm font-medium")
                if selected_count > 0:
                    ui.label(
                        _("Click 'Edit' to change roles or add/remove files.")
                    ).classes("text-xs text-slate-500")
                else:
                    ui.label(
                        _("No files selected. Click 'Edit' to start selecting.")
                    ).classes("text-xs text-slate-500")

            ui.button(
                _("Edit Selection"),
                on_click=lambda: open_file_management_dialog(ctx),
            ).props("outline color=primary")
