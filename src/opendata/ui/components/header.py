from pathlib import Path
import asyncio
from nicegui import ui
from opendata.i18n.translator import _
from opendata.ui.state import ScanState, UIState
from opendata.ui.context import AppContext


@ui.refreshable
def header_content_ui(ctx: AppContext):
    with ui.row().classes("items-center gap-1"):
        # Custom Logo
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
                if UIState._is_refreshing_global:
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
                UIState, "is_project_loading", backward=lambda x: not x
            )
            ui.spinner(size="sm", color="white").bind_visibility_from(
                UIState, "is_project_loading"
            )

            with (
                ui.button(icon="delete", on_click=lambda: handle_delete_current(ctx))
                .props("flat color=red dense")
                .classes("text-xs") as del_btn
            ):
                ui.tooltip(_("Remove current project from history"))
                del_btn.bind_visibility_from(
                    ctx.agent, "project_id", backward=lambda x: bool(x)
                )


async def handle_load_project(ctx: AppContext, path: str):
    if not path:
        return

    try:
        path_obj = Path(path).expanduser().resolve()
    except Exception as e:
        ui.notify(_("Invalid path: {error}").format(error=str(e)), type="negative")
        return

    UIState.is_project_loading = True
    try:
        ui.notify(_("Opening project..."))
        project_id = ctx.wm.get_project_id(path_obj)
        ctx.agent.project_id = project_id

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
        UIState.is_project_loading = False


async def handle_delete_current(ctx: AppContext):
    project_id = ctx.agent.project_id
    if not project_id:
        if ScanState.current_path:
            projects = ctx.wm.list_projects()
            for p in projects:
                if p["path"] == ScanState.current_path:
                    project_id = p["id"]
                    break

    if not project_id:
        ui.notify(_("Please select a project to delete first."), type="warning")
        return

    with ui.dialog() as confirm_dialog, ui.card().classes("p-4"):
        ui.label(_("Are you sure you want to remove this project from the list?"))
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button(_("Cancel"), on_click=confirm_dialog.close).props("flat")

            async def perform_delete():
                confirm_dialog.close()
                success = ctx.wm.delete_project(project_id)
                if success:
                    ui.notify(_("Project removed from workspace."))
                    ScanState.current_path = ""
                    ctx.agent.reset_agent_state()
                    ctx.refresh_all()
                else:
                    ui.notify(_("Failed to delete project state."), type="negative")
                    ctx.refresh_all()

            ui.button(_("Delete"), on_click=perform_delete, color="red")
    confirm_dialog.open()
