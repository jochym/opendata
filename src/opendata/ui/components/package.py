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

    # Trigger background load if project changed, but in a safe way
    if ctx.session.last_inventory_project != ctx.agent.project_id:
        if not ctx.session.is_loading_inventory:
            ui.timer(0.1, lambda: load_inventory_background(ctx), once=True)

    if ctx.session.is_loading_inventory and not ctx.session.inventory_cache:
        with ui.column().classes("w-full items-center justify-center p-20 gap-4"):
            ui.spinner(size="xl")
            ui.label(_("Reading project inventory from database...")).classes(
                "text-slate-500 animate-pulse"
            )
        return

    project_id: str = ctx.agent.project_id

    if (
        ctx.agent.current_analysis
        and ctx.agent.current_analysis.file_suggestions
        and ctx.session.show_suggestions_banner
    ):
        render_suggestions_banner(ctx)

    if not ctx.session.inventory_cache:
        with ui.column().classes("w-full items-center justify-center p-20 gap-4"):
            ui.icon("inventory", size="xl", color="grey-400")
            ui.label(_("No file inventory found.")).classes("text-orange-600 font-bold")
            ui.markdown(
                _("Please click **Scan** in the Analysis tab to list project files.")
            ).classes("text-sm text-slate-500")
            with ui.row().classes("gap-2"):
                ui.button(
                    _("Go to Analysis"),
                    on_click=lambda: ctx.main_tabs.set_value(ctx.analysis_tab),
                ).props("outline")
                ui.button(
                    _("Scan Project Inventory"),
                    icon="search",
                    on_click=lambda: handle_refresh_inventory(ctx),
                ).props("elevated color=primary")
        return

    inventory = ctx.session.inventory_cache

    with ui.column().classes("w-full gap-4 h-[calc(100vh-130px)] p-4"):
        # Header Section
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column():
                ui.label(_("Package Content Editor")).classes("text-2xl font-bold")
                ui.label(
                    _("Overview of files included in the final RODBUK package.")
                ).classes("text-sm text-slate-500")

            with ui.row().classes("gap-2"):
                ui.button(
                    _("AI Suggest Selection"),
                    icon="auto_awesome",
                    on_click=lambda: handle_ai_suggestion_request(ctx),
                ).props("outline color=primary shadow-sm").bind_visibility_from(
                    ScanState, "is_scanning", backward=lambda x: not x
                )
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

        # Progress & Stats Bar
        if ScanState.is_scanning or ctx.session.is_loading_inventory:
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

        included_files = [f for f in ctx.session.inventory_cache if f["included"]]
        total_size = sum(f["size"] for f in included_files)

        with ui.row().classes(
            "w-full gap-8 p-3 bg-slate-50 rounded-lg border items-center"
        ):
            ui.label(
                _("Included: {count} files").format(count=len(included_files))
            ).classes("font-bold")
            ui.label(_("Total Size: {size}").format(size=format_size(total_size)))

            ui.space()

            ui.switch(
                _("Show only included files"),
                value=ctx.session.show_only_included,
                on_change=lambda e: (
                    setattr(ctx.session, "show_only_included", e.value),
                    ctx.refresh("package"),
                ),
            ).props("dense size=sm")

        # FILE EXPLORER AREA
        with ui.card().classes("w-full flex-grow p-0 overflow-hidden border"):
            # Breadcrumbs
            render_breadcrumbs(ctx)

            # File List
            with ui.scroll_area().classes("w-full flex-grow bg-white"):
                render_file_list(ctx)


def render_breadcrumbs(ctx: AppContext):
    """Renders the navigation path."""
    current_path = ctx.session.explorer_path
    parts = Path(current_path).parts if current_path else []

    with ui.row().classes(
        "w-full items-center gap-1 p-2 bg-slate-100 border-b text-sm"
    ):
        # Root Home Icon
        ui.button(icon="home", on_click=lambda: navigate_to(ctx, "")).props(
            "flat dense round size=sm color=primary"
        )

        if not parts:
            ui.label("/").classes("text-slate-400 font-bold")

        accumulated_path = ""
        for i, part in enumerate(parts):
            ui.label("/").classes("text-slate-400")

            if i > 0:
                accumulated_path = str(Path(accumulated_path) / part)
            else:
                accumulated_path = part

            is_last = i == len(parts) - 1

            if is_last:
                ui.label(part).classes("font-bold text-slate-800")
            else:
                # Clickable path part
                # Capture variable `p` for closure
                def make_handler(p):
                    return lambda: navigate_to(ctx, p)

                ui.link(part).classes("text-primary cursor-pointer hover:underline").on(
                    "click", make_handler(accumulated_path)
                )


def navigate_to(ctx: AppContext, path: str):
    """Updates the explorer path and refreshes the view."""
    ctx.session.explorer_path = path
    ctx.refresh("package")


def render_file_list(ctx: AppContext):
    """Renders the list of files and folders in the current explorer path."""
    current_path = ctx.session.explorer_path
    # Get children from cache (built in inventory_logic)
    children = ctx.session.folder_children_map.get(current_path, [])

    if not children:
        with ui.column().classes(
            "w-full items-center justify-center p-10 text-slate-400"
        ):
            ui.icon("folder_off", size="lg")
            ui.label(_("Folder is empty"))
        return

    # Render List
    with ui.column().classes("w-full gap-0"):
        for item in children:
            # Filter if "Show only included" is active
            if ctx.session.show_only_included:
                if item["type"] == "file" and not item["included"]:
                    continue
                # For folders, we'd need recursive check, simplified for now:
                if item["type"] == "folder" and item["included_files"] == 0:
                    continue

            with ui.row().classes(
                "w-full items-center gap-0 px-2 py-1 hover:bg-blue-50 border-b border-slate-100 cursor-pointer group"
            ):
                # 1. Selection Control (Checkbox or Tri-state icon)
                # Fixed width container to align everything precisely
                with ui.row().classes("w-10 items-center justify-center shrink-0"):
                    if item["type"] == "file":
                        # File Checkbox
                        ui.checkbox(
                            value=item["included"],
                            on_change=lambda e, p=item["path"]: toggle_file(
                                ctx, p, e.value
                            ),
                        ).props("dense size=sm").classes("m-0 p-0")
                    else:
                        # Folder Checkbox (Tri-state simulated via icon)
                        state = item.get("state", "unchecked")
                        icon = "check_box_outline_blank"
                        color = "grey"
                        if state == "checked":
                            icon = "check_box"
                            color = "primary"
                        elif state == "indeterminate":
                            icon = "indeterminate_check_box"
                            color = "primary"

                        # Manual adjustment to match ui.checkbox visual position
                        ui.icon(icon, color=color, size="20px").classes(
                            "cursor-pointer block"
                        ).on(
                            "click",
                            lambda e, p=item["path"], s=state: toggle_folder(ctx, p, s),
                        )

                # 2. Type Icon
                icon_name = "folder" if item["type"] == "folder" else "description"
                icon_color = "amber-400" if item["type"] == "folder" else "slate-400"
                ui.icon(icon_name, color=icon_color, size="24px").classes(
                    "mx-2 shrink-0"
                )

                # 3. Clickable Name and details
                if item["type"] == "folder":
                    ui.label(item["name"]).classes(
                        "flex-grow font-medium text-slate-700 text-sm py-1.5"
                    ).on("click", lambda e, p=item["path"]: navigate_to(ctx, p))
                else:
                    with ui.column().classes("flex-grow gap-0 py-1"):
                        ui.label(item["name"]).classes(
                            "text-slate-700 text-sm font-medium"
                        )
                        # Show reason if excluded/forced
                        if item["reason"]:
                            ui.label(item["reason"]).classes(
                                "text-[10px] text-slate-400 leading-none"
                            )

                # 4. Size
                size_str = format_size(item["size"])
                ui.label(size_str).classes(
                    "text-xs text-slate-500 min-w-[75px] text-right pr-2 shrink-0"
                )


async def toggle_file(ctx: AppContext, path: str, new_value: bool):
    """Toggles a single file inclusion."""
    pid = ctx.agent.project_id
    manifest = ctx.pkg_mgr.get_manifest(pid)

    if new_value:
        if path in manifest.force_exclude:
            manifest.force_exclude.remove(path)
        elif path not in manifest.force_include:
            manifest.force_include.append(path)
    else:
        if path in manifest.force_include:
            manifest.force_include.remove(path)
        elif path not in manifest.force_exclude:
            manifest.force_exclude.append(path)

    ctx.pkg_mgr.save_manifest(manifest)
    await load_inventory_background(ctx)


async def toggle_folder(ctx: AppContext, folder_path: str, current_state: str):
    """
    Toggles all files in a folder recursively.
    """
    should_include = current_state == "unchecked"
    pid = ctx.agent.project_id
    manifest = ctx.pkg_mgr.get_manifest(pid)
    inventory = ctx.session.inventory_cache

    folder_prefix = folder_path + "/"
    target_files = []

    for item in inventory:
        p = item["path"]
        if p == folder_path or p.startswith(folder_prefix):
            target_files.append(p)

    if not target_files:
        return

    changed = False
    for path in target_files:
        if should_include:
            if path in manifest.force_exclude:
                manifest.force_exclude.remove(path)
                changed = True
            if path not in manifest.force_include:
                manifest.force_include.append(path)
                changed = True
        else:
            if path in manifest.force_include:
                manifest.force_include.remove(path)
                changed = True
            if path not in manifest.force_exclude:
                manifest.force_exclude.append(path)
                changed = True

    if changed:
        ctx.pkg_mgr.save_manifest(manifest)
        try:
            ui.notify(
                _("{action} {count} files in {folder}").format(
                    action=_("Included") if should_include else _("Excluded"),
                    count=len(target_files),
                    folder=Path(folder_path).name,
                )
            )
        except Exception:
            pass
        await load_inventory_background(ctx)


def render_suggestions_banner(ctx: AppContext):
    suggestions = (
        ctx.agent.current_analysis.file_suggestions
        if ctx.agent.current_analysis
        else []
    )
    if not suggestions:
        return

    with ui.row().classes(
        "w-full bg-blue-50 border border-blue-200 p-3 rounded-lg items-center justify-between mb-4 shadow-sm"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.icon("auto_awesome", color="primary")
            ui.label(
                _("AI has found {count} relevant files for your package.").format(
                    count=len(suggestions)
                )
            ).classes("font-bold text-blue-800")

        with ui.row().classes("gap-2"):
            ui.button(
                _("Review Suggestions"), on_click=lambda: open_suggestions_dialog(ctx)
            ).props("elevated color=primary")
            ui.button(_("Dismiss"), on_click=lambda: clear_suggestions(ctx)).props(
                "flat color=grey"
            ).tooltip(_("Hide this banner until new recommendations arrive"))
            ui.button(_("Forget"), on_click=lambda: forget_suggestions(ctx)).props(
                "flat color=negative"
            ).tooltip(_("Permanently remove these recommendations"))


async def open_suggestions_dialog(ctx: AppContext):
    suggestions = (
        ctx.agent.current_analysis.file_suggestions
        if ctx.agent.current_analysis
        else []
    )

    with ui.dialog() as dialog, ui.card().classes("w-[600px]"):
        ui.label(_("Review AI File Suggestions")).classes("text-h6 mb-4")
        ui.markdown(
            _(
                "The AI curator suggests including these files based on project analysis:"
            )
        )

        selected_paths = {s.path for s in suggestions}

        with ui.scroll_area().classes("h-80 w-full border rounded-md p-2 mb-4"):
            for s in suggestions:
                with ui.row().classes(
                    "w-full items-start no-wrap gap-2 py-2 border-b last:border-0"
                ):
                    cb = ui.checkbox(
                        value=True,
                        on_change=lambda e, p=s.path: (
                            selected_paths.add(p)
                            if e.value
                            else selected_paths.discard(p)
                        ),
                    )
                    with ui.column().classes("flex-grow"):
                        ui.label(s.path).classes("text-sm font-mono font-bold")
                        ui.label(s.reason).classes("text-xs text-slate-500 italic")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button(_("Cancel"), on_click=dialog.close).props("flat")

            async def apply():
                pid = ctx.agent.project_id
                if pid:
                    manifest = ctx.pkg_mgr.get_manifest(pid)
                    for p in selected_paths:
                        if p not in manifest.force_include:
                            manifest.force_include.append(p)
                    ctx.pkg_mgr.save_manifest(manifest)
                    try:
                        ui.notify(
                            _("Included {count} suggested files.").format(
                                count=len(selected_paths)
                            ),
                            type="positive",
                        )
                    except Exception:
                        pass
                forget_suggestions(ctx)
                dialog.close()
                await load_inventory_background(ctx)

            ui.button(_("Include Selected"), on_click=apply).props(
                "elevated color=primary"
            )

    dialog.open()


def clear_suggestions(ctx: AppContext):
    ctx.session.show_suggestions_banner = False
    ctx.refresh("package")


def forget_suggestions(ctx: AppContext):
    if ctx.agent.current_analysis:
        ctx.agent.current_analysis.file_suggestions = []
        ctx.agent.save_state()
    ctx.session.show_suggestions_banner = True
    ctx.refresh("package")


async def handle_ai_suggestion_request(ctx: AppContext):
    if not ctx.agent.project_id:
        ui.notify(_("Please open a project first."), type="warning")
        return

    # 1. Switch to Analysis Tab
    ctx.main_tabs.set_value(ctx.analysis_tab)

    # 2. Update Mode and Notify
    ctx.session.show_suggestions_banner = True
    ScanState.agent_mode = "curator"

    # 3. Refresh UI to show the mode change in the toggle
    ctx.refresh_all()

    prompt = _(
        "Analyze the project structure and primary publication to suggest all files required for results reproduction. Focus on data-script linkages."
    )

    from opendata.ui.components.chat import handle_user_msg_from_code

    await handle_user_msg_from_code(ctx, prompt, mode="curator")
    try:
        ui.notify(_("AI Curator mode activated. Analyzing file linkages..."))
    except RuntimeError:
        pass


async def handle_refresh_inventory(ctx: AppContext):
    if not ScanState.current_path:
        ui.notify(_("Please select a project first."), type="warning")
        return

    resolved_path = Path(ScanState.current_path).expanduser()
    import threading

    ScanState.stop_event = threading.Event()
    ScanState.is_scanning = True
    ui.notify(_("Refreshing file list..."))
    ctx.refresh("package")

    def update_progress(msg, full_path="", short_path=""):
        ScanState.progress = msg
        ScanState.full_path = full_path
        ScanState.short_path = short_path

    try:
        result = await asyncio.to_thread(
            ctx.agent.refresh_inventory,
            resolved_path,
            update_progress,
            stop_event=ScanState.stop_event,
            force=True,
        )
        if ScanState.stop_event and ScanState.stop_event.is_set():
            ctx.agent.chat_history.append(("agent", f"🛑 **{result}**"))
        else:
            ui.notify(_("File list updated."), type="positive")
    except asyncio.CancelledError:
        logger.info("Scan cancelled by user.")
    except Exception as e:
        ui.notify(f"Scan error: {e}", type="negative")
    finally:
        ScanState.is_scanning = False
        ScanState.stop_event = None
        ctx.session.last_inventory_project = ""
        await load_inventory_background(ctx)


async def handle_reset(ctx: AppContext):
    if not ctx.agent.project_id:
        return
    pid: str = ctx.agent.project_id
    manifest = ctx.pkg_mgr.get_manifest(pid)
    manifest.force_include = []
    manifest.force_exclude = []
    ctx.pkg_mgr.save_manifest(manifest)
    ui.notify(_("Selection reset to protocol defaults."), type="info")
    await load_inventory_background(ctx)
