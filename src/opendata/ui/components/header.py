from pathlib import Path
import asyncio
import logging
from nicegui import ui
from opendata.i18n.translator import _
from opendata.ui.state import ScanState
from opendata.ui.context import AppContext
from opendata.utils import get_app_version

logger = logging.getLogger("opendata.ui.header")


@ui.refreshable
def header_content_ui(ctx: AppContext):
    with ui.row().classes("items-center gap-1"):
        # Custom Logo
        with ui.element("div").classes("cursor-help"):
            ui.tooltip(f"OpenData Agent v{get_app_version()}")
            ui.html(
                f"""
                <div style="display: flex; align-items: center; gap: 12px; color: white; line-height: 1; margin-right: 12px;">
                    <div style="position: relative; width: 32px; height: 32px; flex-shrink: 0; display: flex; align-items: center; justify-content: center;">
                        <div style="position: absolute; inset: 0; border: 2.5px solid white; border-radius: 50%;"></div>
                        <div style="position: absolute; left: 38%; top: 20%; width: 45%; height: 60%; border: 2.5px solid white; border-left: none; border-radius: 0 16px 16px 0; display: flex; align-items: center; justify-content: center;">
                            <span class="material-icons" style="font-size: 12px; color: white;">auto_awesome</span>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; font-family: sans-serif; height: 32px;">
                        <div style="font-size: 38px; font-weight: 300; color: white; height: 100%; display: flex; align-items: center;">/</div>
                        <div style="display: flex; flex-direction: column; font-size: 12px; letter-spacing: 0.8px; text-transform: uppercase; justify-content: center;">
                            <span style="font-weight: 300;">{_("Open")}</span>
                            <span style="font-weight: 900;">{_("Data")}</span>
                        </div>
                    </div>
                </div>
            """,
                sanitize=False,
            )
        ui.label(_("Agent")).classes(
            "text-h5 font-bold tracking-tight hidden sm:block ml-4"
        )

        if not ctx.settings.ai_consent_granted:
            return

        projects = ctx.wm.list_projects()
        current_id = ctx.agent.project_id

        with ui.row().classes("items-center no-wrap gap-1"):
            project_options = {p["id"]: f"{p['title']} ({p['path']})" for p in projects}

            if not project_options:
                return

            if current_id not in project_options:
                current_id = None

            async def on_selector_change(e):
                # Guard against infinite loops: only load if ID actually changed AND not in refresh
                if ctx.session._is_refreshing_global:
                    return
                if e.value and e.value != ctx.agent.project_id:
                    if e.value in project_options:
                        path = next(
                            (p["path"] for p in projects if p["id"] == e.value), None
                        )
                        if path and path != "Unknown":
                            await handle_load_project(ctx, path)
                        else:
                            ctx.agent.project_id = e.value
                            ui.notify(
                                _("Broken project selected. You can delete it."),
                                type="warning",
                            )

            selector = (
                ui.select(
                    options=project_options,
                    value=current_id,
                    label=_("Recent Projects"),
                    on_change=on_selector_change,
                )
                .props("dark dense options-dark behavior=menu")
                .classes("w-48 text-xs")
            )
            selector.bind_visibility_from(
                ctx.session, "is_project_loading", backward=lambda x: not x
            )
            ui.spinner(size="sm", color="white").bind_visibility_from(
                ctx.session, "is_project_loading"
            )

            # Manage all projects button (always visible)
            with (
                ui.button(
                    icon="folder_open", on_click=lambda: handle_manage_projects(ctx)
                )
                .props("flat dense")
                .classes("text-xs") as manage_btn
            ):
                ui.tooltip(_("Manage all projects"))
                # Button visible when not loading (i.e., always after initial load)
                manage_btn.bind_visibility_from(
                    ctx.session, "is_project_loading", backward=lambda x: not x
                )


async def handle_load_project(ctx: AppContext, path: str):
    if not path:
        return

    try:
        path_obj = Path(path).expanduser().resolve()
    except Exception as e:
        ui.notify(_("Invalid path: {error}").format(error=str(e)), type="negative")
        return

    ctx.session.is_project_loading = True
    try:
        ui.notify(_("Opening project..."))
        project_id = ctx.wm.get_project_id(path_obj)
        ctx.agent.project_id = project_id

        # Reset session state for new project
        # Reset session state and start loading
        ctx.session.reset()
        # Loading state already managed in handle_load_project via reset() or explicitly
        ctx.session.is_project_loading = True

        success = await asyncio.to_thread(ctx.agent.load_project, path_obj)
        ScanState.current_path = str(path_obj)

        if ctx.agent.current_metadata.ai_model:
            ctx.ai.switch_model(ctx.agent.current_metadata.ai_model)

        project_state_dir = ctx.wm.projects_dir / project_id
        project_state_dir.mkdir(parents=True, exist_ok=True)

        ctx.refresh_all()

        from opendata.ui.components.inventory_logic import load_inventory_background

        asyncio.create_task(load_inventory_background(ctx))
        ctx.refresh("protocols")

        if success:
            ui.notify(_("Project opened from history."))
        else:
            ui.notify(_("New project directory opened."))
    finally:
        ctx.session.is_project_loading = False


async def handle_manage_projects(ctx: AppContext):
    """Shows a dialog with all projects and options to delete them."""
    projects = ctx.wm.list_projects()

    if not projects:
        ui.notify(_("No projects in workspace."), type="info")
        return

    with ui.dialog() as manage_dialog, ui.card().classes("p-6 w-[600px]"):
        ui.label(_("Manage Projects")).classes("text-xl font-bold")
        ui.separator()

        with ui.column().classes("gap-3 mt-4 max-h-96 overflow-y-auto"):
            for p in projects:
                path_display = p.get("path") or "Unknown"
                # Guard against invalid path values (empty, NUL, etc.)
                if not path_display or path_display == "Unknown":
                    path_exists = False
                else:
                    try:
                        path_exists = Path(path_display).exists()
                    except (ValueError, OSError):
                        # Invalid path (e.g., contains NUL, too long, etc.)
                        path_exists = False

                # Visual indicator for corrupt/orphaned projects
                if path_display == "Unknown" or not path_exists:
                    status_icon = "❌"
                    status_color = "red"
                    status_text = _("Corrupt/Orphaned")
                    tooltip_msg = _(
                        "Project data is incomplete or the original location no longer exists. Safe to remove."
                    )
                else:
                    status_icon = "✓"
                    status_color = "green"
                    status_text = _("OK")
                    tooltip_msg = _("Project is valid and accessible.")

                with ui.row().classes(
                    "w-full items-center gap-2 p-2 rounded hover:bg-gray-100"
                ):
                    # Accessibility: Add screen-reader friendly text
                    with ui.element("div").classes("text-lg").tooltip(tooltip_msg):
                        ui.label(status_icon).classes("inline")
                        ui.label(status_text).classes(
                            "sr-only"
                        )  # Hidden from visual, visible to screen readers

                    with ui.column().classes("flex-1"):
                        ui.label(p.get("title", _("Untitled"))[:50]).classes("font-bold")
                        # Only show ellipsis if path is actually truncated
                        path_label = (
                            f"{path_display[:60]}..."
                            if len(path_display) > 60
                            else path_display
                        )
                        ui.label(path_label).classes("text-xs text-gray-500")

                    ui.chip(status_text).props(f"color={status_color} outline")

                    async def do_delete(
                        pid=p["id"], title=p.get("title", _("Untitled"))[:40]
                    ):
                        # Show confirmation dialog before destructive operation
                        with (
                            ui.dialog() as confirm_dialog,
                            ui.card().classes("p-4 w-96"),
                        ):
                            ui.label(_("Delete Project?")).classes("text-lg font-bold")
                            ui.label(
                                _(
                                    "Are you sure you want to delete '{title}'? This action cannot be undone."
                                ).format(title=title)
                            ).classes("mt-2 text-gray-600")

                            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                                ui.button(
                                    _("Cancel"), on_click=confirm_dialog.close
                                ).props("flat")

                                async def confirm():
                                    confirm_dialog.close()
                                    try:
                                        # Use asyncio.to_thread for blocking I/O to avoid freezing UI
                                        success = await asyncio.to_thread(
                                            ctx.wm.delete_project, pid
                                        )
                                        if success:
                                            ui.notify(
                                                _("Project removed."), type="positive"
                                            )
                                            # Clear state if deleted project is currently loaded
                                            if ctx.agent.project_id == pid:
                                                ctx.agent.reset_agent_state()
                                                ScanState.current_path = ""
                                            # Cache already cleared by delete_project()
                                            # Close manage dialog and refresh
                                            manage_dialog.close()
                                            await asyncio.sleep(0.1)
                                            ctx.refresh_all()
                                        else:
                                            ui.notify(
                                                _("Failed to delete."), type="negative"
                                            )
                                    except Exception as e:
                                        logger.error(f"Delete error: {e}")
                                        ui.notify(str(e), type="negative")

                                ui.button(_("Delete"), on_click=confirm, color="red")

                        confirm_dialog.open()

                    ui.button(icon="delete", on_click=do_delete).props(
                        "flat color=red dense"
                    ).tooltip(_("Delete this project permanently"))

        with ui.row().classes("w-full justify-end mt-4"):
            ui.button(_("Close"), on_click=manage_dialog.close).props("flat")

    manage_dialog.open()
