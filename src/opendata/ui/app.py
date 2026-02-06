import yaml
from nicegui import ui
import webbrowser
from pathlib import Path
from typing import Any
from opendata.utils import get_local_ip
from opendata.workspace import WorkspaceManager
from opendata.packager import PackagingService
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.ai.service import AIService
from opendata.i18n.translator import setup_i18n, _


def start_ui(host: str = "127.0.0.1", port: int = 8080):
    # 1. Initialize Backend
    wm = WorkspaceManager()
    settings = wm.get_settings()
    setup_i18n(settings.language)

    agent = ProjectAnalysisAgent(wm)
    ai = AIService(Path(settings.workspace_path), settings)
    packaging_service = PackagingService(Path(settings.workspace_path))

    # Initialize model from global settings
    if settings.ai_provider == "google" and settings.google_model:
        ai.switch_model(settings.google_model)
    elif settings.ai_provider == "openai" and settings.openai_model:
        ai.switch_model(settings.openai_model)

    # Try Silent Auth
    ai.authenticate(silent=True)

    async def confirm_logout():
        with ui.dialog() as dialog, ui.card().classes("p-4"):
            ui.label(_("Are you sure you want to logout from AI?")).classes(
                "text-lg mb-4"
            )
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button(_("Cancel"), on_click=dialog.close).props("flat")

                async def logout_action():
                    dialog.close()
                    await handle_logout()

                ui.button(_("Logout"), on_click=logout_action, color="red")
        dialog.open()

    # --- REFRESHABLE COMPONENTS ---

    @ui.refreshable
    def header_content_ui():
        with ui.row().classes("items-center gap-1"):
            # Custom Logo: Reverted O+D style with improved text and slash
            ui.html(
                f"""
                <div style="display: flex; align-items: center; gap: 12px; color: white; line-height: 1; margin-right: 12px;">
                    <div style="position: relative; width: 32px; height: 32px; flex-shrink: 0; display: flex; align-items: center; justify-content: center;">
                        <!-- Outer O -->
                        <div style="position: absolute; inset: 0; border: 2.5px solid white; border-radius: 50%;"></div>
                        <!-- Inner D -->
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
            project_selector_ui()

    @ui.refreshable
    def chat_messages_ui():
        with ui.column().classes("w-full gap-1 overflow-x-hidden"):
            for role, msg in agent.chat_history:
                if role == "user":
                    with ui.row().classes("w-full justify-start"):
                        with ui.card().classes(
                            "bg-blue-50 border border-blue-100 rounded-lg py-0.5 px-3 w-full ml-12 shadow-none"
                        ):
                            ui.markdown(msg).classes(
                                "text-sm text-gray-800 m-0 p-0 break-words"
                            )
                else:
                    with ui.row().classes("w-full justify-start"):
                        with ui.card().classes(
                            "bg-gray-100 border border-gray-200 rounded-lg py-0.5 px-3 w-full shadow-none"
                        ):
                            ui.markdown(msg).classes(
                                "text-sm text-gray-800 m-0 p-0 break-words"
                            )

            if ScanState.is_scanning:
                with ui.row().classes("w-full justify-start"):
                    with ui.card().classes(
                        "bg-gray-100 border border-gray-200 rounded-lg py-0.5 px-3 w-full shadow-none"
                    ):
                        with ui.row().classes("items-center gap-1"):
                            ui.markdown(_("Scanning project...")).classes(
                                "text-sm text-gray-800 m-0 p-0"
                            )
                            ui.button("", on_click=handle_cancel_scan).props(
                                "icon=close flat color=gray size=xs"
                            ).classes("min-h-6 min-w-6 p-0.5")
        ui.run_javascript("window.scrollTo(0, document.body.scrollHeight)")

    class ScanState:
        is_scanning = False
        progress = ""
        short_path = ""
        full_path = ""
        progress_label: Any = None
        short_path_label: Any = None
        current_path = ""
        stop_event: Any = None
        qr_dialog: Any = None  # Store reference globally within start_ui scope

    @ui.refreshable
    def metadata_preview_ui():
        if ScanState.is_scanning:
            with ui.column().classes("w-full items-center justify-center p-8 gap-1"):
                ui.spinner(size="lg")
                ui.label("").classes("text-xs font-bold text-slate-700").bind_text_from(
                    ScanState, "progress"
                )
                with ui.label("").classes(
                    "text-[10px] text-slate-500 animate-pulse text-center w-full truncate cursor-help"
                ) as lbl:
                    ui.tooltip("").bind_text_from(ScanState, "full_path")
                    lbl.bind_text_from(ScanState, "short_path")
                ScanState.progress_label = lbl  # type: ignore[attr-defined]
            return

        # Explicitly refresh header when metadata changes to sync project selector
        header_content_ui.refresh()  # type: ignore

        fields = agent.current_metadata.model_dump(exclude_unset=True)

        def create_expandable_text(text: str, key: str = None):
            with ui.column().classes(
                "w-full gap-0 bg-slate-50 border border-slate-100 rounded relative group"
            ):
                # Lock indicator
                if key:
                    is_locked = key in agent.current_metadata.locked_fields

                    async def toggle_lock(e, k=key):
                        if k in agent.current_metadata.locked_fields:
                            agent.current_metadata.locked_fields.remove(k)
                        else:
                            agent.current_metadata.locked_fields.append(k)
                        agent.save_state()
                        metadata_preview_ui.refresh()

                    with (
                        ui.button(
                            icon="lock" if is_locked else "lock_open",
                            on_click=toggle_lock,
                        )
                        .props("flat dense")
                        .classes(
                            f"absolute top-1 right-1 z-10 opacity-0 group-hover:opacity-100 transition-opacity {'text-orange-600 opacity-100' if is_locked else 'text-slate-400'}"
                        )
                    ):
                        ui.tooltip(
                            _("Lock field from AI updates")
                            if not is_locked
                            else _("Unlock field")
                        )

                # Increased height to 110px to ensure 5 lines are fully visible without chopping descenders.
                content = ui.markdown(text).classes(
                    "px-2 py-0 text-sm text-gray-800 break-words overflow-hidden transition-all duration-300 cursor-pointer"
                )
                if key:
                    content.on("click", lambda: open_edit_dialog(key))

                content.style("max-height: 110px; line-height: 1.5;")
                if len(text.splitlines()) > 5 or len(text) > 300:

                    def toggle(e, target=content):
                        is_expanded = target.style["max-height"] == "none"
                        target.style(
                            f"max-height: {'110px' if is_expanded else 'none'}"
                        )
                        e.sender.text = _("more...") if is_expanded else _("less...")

                    ui.button(_("more..."), on_click=toggle).props(
                        "flat dense color=primary"
                    ).classes("text-xs self-end px-2 pb-1")
                else:
                    content.style("max-height: none")

        async def open_edit_dialog(key: str):
            val = getattr(agent.current_metadata, key)

            with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
                ui.label(
                    _("Edit {field}").format(field=key.replace("_", " ").title())
                ).classes("text-h6")

                if isinstance(val, list):
                    # For lists like keywords or description
                    # Handle lists of objects (authors, etc.) or strings
                    if val and not isinstance(val[0], str):
                        # Use YAML for structured lists
                        current_text = yaml.dump(
                            [
                                i.model_dump() if hasattr(i, "model_dump") else i
                                for i in val
                            ],
                            allow_unicode=True,
                        )
                        edit_area = (
                            ui.textarea(value=current_text)
                            .classes("w-full font-mono text-xs")
                            .props("rows=15")
                        )
                        ui.markdown(_("Edit YAML structure for complex data.")).classes(
                            "text-xs text-slate-500"
                        )
                    else:
                        current_text = "\n".join(val) if val else ""
                        edit_area = (
                            ui.textarea(value=current_text)
                            .classes("w-full")
                            .props("rows=10 auto-grow")
                        )
                        ui.markdown(_("Enter one item per line.")).classes(
                            "text-xs text-slate-500"
                        )
                else:
                    # For simple strings
                    edit_area = (
                        ui.textarea(value=val or "")
                        .classes("w-full")
                        .props("rows=5 auto-grow")
                    )

                with ui.row().classes("w-full justify-end gap-2 mt-4"):
                    ui.button(_("Cancel"), on_click=dialog.close).props("flat")

                    async def save_value():
                        new_val = edit_area.value
                        try:
                            if isinstance(val, list):
                                if val and not isinstance(val[0], str):
                                    # Parse YAML back to list of dicts
                                    import yaml

                                    parsed_list = yaml.safe_load(new_val)
                                    if not isinstance(parsed_list, list):
                                        raise ValueError("YAML must be a list")
                                    setattr(agent.current_metadata, key, parsed_list)
                                else:
                                    new_list = [
                                        line.strip()
                                        for line in new_val.split("\n")
                                        if line.strip()
                                    ]
                                    setattr(agent.current_metadata, key, new_list)
                            else:
                                setattr(agent.current_metadata, key, new_val)

                            # Auto-lock on manual edit
                            if key not in agent.current_metadata.locked_fields:
                                agent.current_metadata.locked_fields.append(key)

                            agent.save_state()
                            dialog.close()
                            metadata_preview_ui.refresh()
                            ui.notify(
                                _("Field '{field}' updated and locked.").format(
                                    field=key
                                )
                            )
                        except Exception as e:
                            ui.notify(
                                _("Failed to save: {error}").format(error=str(e)),
                                type="negative",
                            )

                    ui.button(_("Save"), on_click=save_value, color="primary")

            dialog.open()

        with ui.column().classes("w-full gap-4"):
            for key, value in fields.items():
                if key == "locked_fields":
                    continue
                if key == "authors" or key == "contacts":
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-xs font-bold text-slate-600 ml-2"
                    )
                    with ui.row().classes("w-full gap-1 flex-wrap items-center"):
                        for item in value:
                            if isinstance(item, dict):
                                name = item.get(
                                    "name", item.get("person_to_contact", str(item))
                                )
                                name_clean = (
                                    name.replace("{", "")
                                    .replace("}", "")
                                    .replace("\\", "")
                                    .replace("orcidlink", "")
                                )
                                affiliation = item.get("affiliation", "")
                                identifier = item.get("identifier", "")
                                email = item.get("email", "")

                                # Use green for authors, indigo for contacts
                                bg_color = (
                                    "bg-slate-100 border-slate-200"
                                    if key == "authors"
                                    else "bg-indigo-50 border-indigo-100 hover:bg-indigo-100"
                                )

                                with ui.label("").classes(
                                    f"py-0.5 px-1.5 rounded {bg_color} border cursor-pointer text-sm inline-block mr-1 mb-1 relative group"
                                ) as container:
                                    # Lock indicator for Authors/Contacts (nested in list)
                                    is_locked = (
                                        key in agent.current_metadata.locked_fields
                                    )

                                    async def toggle_lock_list(e, k=key):
                                        if k in agent.current_metadata.locked_fields:
                                            agent.current_metadata.locked_fields.remove(
                                                k
                                            )
                                        else:
                                            agent.current_metadata.locked_fields.append(
                                                k
                                            )
                                        agent.save_state()
                                        metadata_preview_ui.refresh()

                                    with (
                                        ui.button(
                                            icon="lock" if is_locked else "lock_open",
                                            on_click=toggle_lock_list,
                                        )
                                        .props("flat dense")
                                        .classes(
                                            f"absolute -top-2 -right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity {'text-orange-600 opacity-100' if is_locked else 'text-slate-400'}"
                                        )
                                        .style(
                                            "font-size: 10px; background: white; border-radius: 50%; border: 1px solid #eee; width: 20px; height: 20px;"
                                        )
                                    ):
                                        ui.tooltip(
                                            _("Lock field from AI updates")
                                            if not is_locked
                                            else _("Unlock field")
                                        )

                                    container.on(
                                        "click", lambda _e, k=key: open_edit_dialog(k)
                                    )

                                    ui.label(name_clean).classes(
                                        "text-sm font-medium inline mr-1"
                                    )
                                    with ui.row().classes(
                                        "inline-flex items-center gap-0.5"
                                    ):
                                        if identifier:
                                            ui.icon(
                                                "verified",
                                                size="0.75rem",
                                                color="green",
                                            ).classes("inline-block align-middle")
                                        if affiliation:
                                            ui.icon(
                                                "business", size="0.75rem", color="blue"
                                            ).classes("inline-block align-middle")
                                        if email:
                                            ui.icon(
                                                "email", size="0.75rem", color="indigo"
                                            ).classes("inline-block align-middle")

                                    with ui.tooltip().classes(
                                        "bg-slate-800 text-white p-2 text-xs whitespace-normal max-w-xs"
                                    ):
                                        ui.label(f"Name: {name_clean}")
                                        if affiliation:
                                            ui.label(f"Affiliation: {affiliation}")
                                        if identifier:
                                            ui.label(f"ORCID: {identifier}")
                                        if email:
                                            ui.label(f"Email: {email}")
                            else:
                                ui.label(str(item)).classes(
                                    "text-sm bg-slate-50 p-1 rounded border border-slate-100 break-words"
                                )
                elif key == "keywords":
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-xs font-bold text-slate-600 ml-2"
                    )
                    with ui.row().classes(
                        "w-full gap-1 flex-wrap items-center relative group"
                    ) as kw_container:
                        # Lock for keywords
                        is_locked = key in agent.current_metadata.locked_fields
                        kw_container.on("click", lambda _e, k=key: open_edit_dialog(k))

                        with (
                            ui.button(
                                icon="lock" if is_locked else "lock_open",
                                on_click=lambda _e, k=key: toggle_lock_list(_e, k),
                            )
                            .props("flat dense")
                            .classes(
                                f"absolute -top-4 right-0 z-10 opacity-0 group-hover:opacity-100 transition-opacity {'text-orange-600 opacity-100' if is_locked else 'text-slate-400'}"
                            )
                            .style(
                                "font-size: 10px; background: white; border-radius: 50%; border: 1px solid #eee; width: 20px; height: 20px;"
                            )
                        ):
                            ui.tooltip(
                                _("Lock field from AI updates")
                                if not is_locked
                                else _("Unlock field")
                            )

                        for kw in value:
                            ui.label(str(kw)).classes(
                                "text-sm bg-slate-100 py-0.5 px-2 rounded border border-slate-200 inline-block mr-1 mb-1"
                            )
                elif key == "related_publications":
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-xs font-bold text-slate-600 ml-2"
                    )
                    with ui.column().classes("w-full gap-1 items-start"):
                        for pub in value:
                            if isinstance(pub, dict):
                                title = pub.get("title", "Untitled")
                                rel_type = pub.get("relation_type", "")
                                id_type = pub.get("id_type", "")
                                id_val = pub.get("id_number", "")

                                # Cleanup ID value: remove https://doi.org/ prefix
                                if id_val:
                                    id_val = id_val.replace("https://doi.org/", "")

                                with ui.label("").classes(
                                    "py-1 px-1.5 rounded bg-blue-50 border border-blue-100 cursor-pointer hover:bg-blue-100 text-sm inline-block w-full relative group"
                                ) as pub_container:
                                    # Lock for related publications
                                    is_locked = (
                                        key in agent.current_metadata.locked_fields
                                    )
                                    pub_container.on(
                                        "click", lambda _e, k=key: open_edit_dialog(k)
                                    )

                                    with (
                                        ui.button(
                                            icon="lock" if is_locked else "lock_open",
                                            on_click=lambda _e, k=key: toggle_lock_list(
                                                _e, k
                                            ),
                                        )
                                        .props("flat dense")
                                        .classes(
                                            f"absolute -top-2 -right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity {'text-orange-600 opacity-100' if is_locked else 'text-slate-400'}"
                                        )
                                        .style(
                                            "font-size: 10px; background: white; border-radius: 50%; border: 1px solid #eee; width: 20px; height: 20px;"
                                        )
                                    ):
                                        ui.tooltip(
                                            _("Lock field from AI updates")
                                            if not is_locked
                                            else _("Unlock field")
                                        )

                                    ui.label(title).classes(
                                        "text-sm font-medium break-words leading-tight"
                                    )

                                    with ui.tooltip().classes(
                                        "bg-slate-800 text-white p-2 text-xs whitespace-normal max-w-xs"
                                    ):
                                        ui.label(f"Title: {title}")
                                        if rel_type:
                                            ui.label(f"Relation: {rel_type}")
                                        if id_type or id_val:
                                            label_prefix = (
                                                f"{id_type}:" if id_type else "DOI:"
                                            )
                                            ui.label(f"{label_prefix} {id_val or ''}")
                elif key == "funding":
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-xs font-bold text-slate-600 ml-2"
                    )
                    with ui.column().classes("w-full gap-1 items-start"):
                        for f in value:
                            if isinstance(f, dict):
                                agency = f.get("funder_name", "")
                                award = f.get("award_title", "")
                                grant_id = f.get("grant_id", "")

                                display_title = award if award else agency

                                with ui.label("").classes(
                                    "py-1 px-1.5 rounded bg-amber-50 border border-amber-100 cursor-pointer hover:bg-amber-100 text-sm inline-block w-full relative group"
                                ) as fund_container:
                                    # Lock for funding
                                    is_locked = (
                                        key in agent.current_metadata.locked_fields
                                    )
                                    fund_container.on(
                                        "click", lambda _e, k=key: open_edit_dialog(k)
                                    )

                                    with (
                                        ui.button(
                                            icon="lock" if is_locked else "lock_open",
                                            on_click=lambda _e, k=key: toggle_lock_list(
                                                _e, k
                                            ),
                                        )
                                        .props("flat dense")
                                        .classes(
                                            f"absolute -top-2 -right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity {'text-orange-600 opacity-100' if is_locked else 'text-slate-400'}"
                                        )
                                        .style(
                                            "font-size: 10px; background: white; border-radius: 50%; border: 1px solid #eee; width: 20px; height: 20px;"
                                        )
                                    ):
                                        ui.tooltip(
                                            _("Lock field from AI updates")
                                            if not is_locked
                                            else _("Unlock field")
                                        )

                                    with ui.column().classes("gap-0"):
                                        ui.label(display_title).classes(
                                            "text-sm font-medium break-words leading-tight"
                                        )
                                        if grant_id:
                                            ui.label(grant_id).classes(
                                                "text-xs text-slate-500 italic"
                                            )

                                    with ui.tooltip().classes(
                                        "bg-slate-800 text-white p-2 text-xs whitespace-normal max-w-xs"
                                    ):
                                        if award:
                                            ui.label(f"Award: {award}")
                                        if agency:
                                            ui.label(f"Funder: {agency}")
                                        if grant_id:
                                            ui.label(f"Grant ID: {grant_id}")
                else:
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-xs font-bold text-slate-600 ml-2"
                    )
                    if isinstance(value, list):
                        with ui.column().classes("w-full gap-1"):
                            for v_item in value:
                                create_expandable_text(str(v_item), key=key)
                    else:
                        create_expandable_text(str(value), key=key)

    @ui.refreshable
    def project_selector_ui():
        if not settings.ai_consent_granted:
            return
        projects = wm.list_projects()
        if not projects:
            return

        # Identify current project by path to set as default value
        current_val = ScanState.current_path if ScanState.current_path else None

        with ui.row().classes("items-center no-wrap gap-1"):
            project_options = {
                p["path"]: f"{p['title']} ({p['path']})" for p in projects
            }

            # Sanitize current_val to avoid ValueError if project was deleted
            if current_val not in project_options:
                current_val = None

            selector = (
                ui.select(
                    options=project_options,
                    value=current_val,
                    label=_("Recent Projects"),
                    on_change=lambda e: handle_load_project(e.value),
                )
                .props("dark dense options-dark behavior=menu")
                .classes("w-48 text-xs")
            )

            async def handle_delete_current():
                if not ScanState.current_path:
                    return
                # Use the same logic as list_projects to find the project to delete
                projects = wm.list_projects()
                # Find project that matches current path exactly or by ID
                # If path is 'Unknown', try matching current_path or resolving current project ID
                target_project = next(
                    (p for p in projects if p["path"] == ScanState.current_path), None
                )

                if not target_project:
                    # Try resolving ID from ScanState.current_path
                    path_obj = Path(ScanState.current_path).resolve()
                    project_id = agent.wm.get_project_id(path_obj)
                else:
                    project_id = target_project["id"]

                print(f"[DEBUG] UI Current Path: {ScanState.current_path}")
                print(f"[DEBUG] Determined Project ID for deletion: {project_id}")

                # Use NiceGUI dialog instead of run_javascript(confirm) which times out in some environments
                with ui.dialog() as confirm_dialog, ui.card().classes("p-4"):
                    ui.label(
                        _("Are you sure you want to remove this project from the list?")
                    )
                    with ui.row().classes("w-full justify-end gap-2 mt-4"):
                        ui.button(_("Cancel"), on_click=confirm_dialog.close).props(
                            "flat"
                        )

                        async def perform_delete():
                            # Close dialog first
                            confirm_dialog.close()

                            # Perform deletion
                            success = wm.delete_project(project_id)
                            if success:
                                ui.notify(_("Project removed from workspace."))
                                # Force reset all state
                                ScanState.current_path = ""
                                agent.reset_agent_state()
                                # Refresh UI components
                                project_selector_ui.refresh()
                                metadata_preview_ui.refresh()
                                chat_messages_ui.refresh()
                                header_content_ui.refresh()
                            else:
                                # Fallback deletion attempt for "Unknown" paths if we have agent.project_id
                                if agent.project_id and wm.delete_project(
                                    agent.project_id
                                ):
                                    ui.notify(_("Project removed from workspace."))
                                    ScanState.current_path = ""
                                    agent.reset_agent_state()
                                    project_selector_ui.refresh()
                                    metadata_preview_ui.refresh()
                                    chat_messages_ui.refresh()
                                    header_content_ui.refresh()
                                else:
                                    ui.notify(
                                        _("Failed to delete project folder."),
                                        type="negative",
                                    )

                        ui.button(_("Delete"), on_click=perform_delete, color="red")

                confirm_dialog.open()

            with (
                ui.button(icon="delete", on_click=handle_delete_current)
                .props("flat color=red dense")
                .classes("text-xs") as del_btn
            ):
                ui.tooltip(_("Remove current project from history"))
                del_btn.bind_visibility_from(
                    ScanState, "current_path", backward=lambda x: bool(x)
                )

    @ui.page("/")
    def index():
        setup_i18n(settings.language)
        ui.query("body").style("background-color: #f8f9fa;")

        # Define dialogs early for access in header
        with ui.dialog() as qr_dialog, ui.card().classes("p-6 items-center"):
            ui.label(_("Continue on Mobile")).classes("text-h6 q-mb-md")
            url = f"http://{get_local_ip()}:{port}"
            ui.interactive_image(
                f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url}"
            )
            ui.label(url).classes("text-caption text-slate-500 q-mt-md")
            ui.button(_("Close"), on_click=qr_dialog.close).props("flat")

        ScanState.qr_dialog = qr_dialog

        with ui.header().classes(
            "bg-slate-800 text-white py-2 px-4 justify-between items-center shadow-lg"
        ):
            header_content_ui()
            with ui.tabs().classes("bg-slate-800") as main_tabs:
                analysis_tab = ui.tab(_("Analysis"), icon="analytics")
                protocols_tab = ui.tab(_("Protocols"), icon="rule")
                package_tab = ui.tab(_("Package"), icon="inventory_2")
                preview_tab = ui.tab(_("Preview"), icon="visibility")
                settings_tab = ui.tab(_("Settings"), icon="settings")

        container = ui.column().classes("w-full items-center q-pa-md max-w-7xl mx-auto")
        with container:
            if not settings.ai_consent_granted:
                render_setup_wizard()
            else:
                with ui.tab_panels(main_tabs, value=analysis_tab).classes(
                    "w-full bg-transparent"
                ):
                    with ui.tab_panel(analysis_tab):
                        render_analysis_dashboard()
                    with ui.tab_panel(protocols_tab):
                        render_protocols_placeholder()
                    with ui.tab_panel(package_tab):
                        render_package_placeholder()
                    with ui.tab_panel(preview_tab):
                        render_preview_and_build()
                    with ui.tab_panel(settings_tab):
                        render_settings_tab()

    def render_preview_and_build():
        with ui.column().classes("w-full gap-4"):
            with ui.card().classes("w-full p-6 shadow-md border-t-4 border-green-600"):
                with ui.row().classes("w-full justify-between items-center mb-4"):
                    ui.label(_("RODBUK Submission Preview")).classes(
                        "text-h5 font-bold text-green-800"
                    )
                    ui.button(
                        _("Build Package"),
                        icon="archive",
                        color="green",
                        on_click=handle_build_package,
                    ).classes("px-6 font-bold")

                ui.markdown(
                    _("This is how your project will appear in the RODBUK repository.")
                )
                ui.separator().classes("my-4")

                # Reuse metadata preview logic
                metadata_preview_ui()

            with ui.card().classes("w-full p-6 shadow-md"):
                ui.label(_("Selected Files")).classes("text-h6 font-bold mb-2")
                ui.markdown(
                    _("List of files to be included in the package will appear here.")
                )

    def render_settings_tab():
        qr_dialog = ScanState.qr_dialog
        with ui.card().classes("w-full p-8 shadow-md"):
            ui.label(_("Application Settings")).classes("text-h4 q-mb-md font-bold")

            with ui.column().classes("w-full gap-6"):
                # Model Selection
                with ui.column().classes("gap-1"):
                    ui.label(_("AI Model")).classes("text-sm font-bold text-slate-600")
                    if ai.is_authenticated():
                        models = ai.list_available_models()

                        async def handle_model_change(e):
                            ai.switch_model(e.value)
                            if settings.ai_provider == "google":
                                settings.google_model = e.value
                            else:
                                settings.openai_model = e.value
                            wm.save_yaml(settings, "settings.yaml")
                            if agent.project_id:
                                agent.current_metadata.ai_model = e.value
                                agent.save_state()

                        ui.select(
                            options=models,
                            value=ai.model_name,
                            on_change=handle_model_change,
                        ).props("outlined dense behavior=menu").classes(
                            "w-full max-w-md"
                        )

                # Language
                with ui.column().classes("gap-1"):
                    ui.label(_("Language")).classes("text-sm font-bold text-slate-600")
                    with ui.row().classes("gap-2"):
                        ui.button("English", on_click=lambda: set_lang("en")).props(
                            f"outline color={'primary' if settings.language == 'en' else 'grey'}"
                        ).classes("w-32")
                        ui.button("Polski", on_click=lambda: set_lang("pl")).props(
                            f"outline color={'primary' if settings.language == 'pl' else 'grey'}"
                        ).classes("w-32")

                # Mobile
                with ui.column().classes("gap-1"):
                    ui.label(_("Mobile Access")).classes(
                        "text-sm font-bold text-slate-600"
                    )
                    ui.button(
                        _("Show QR Code"),
                        icon="qr_code_2",
                        on_click=lambda: qr_dialog.open() if qr_dialog else None,
                    ).props("outline color=primary").classes("w-full max-w-md")

                ui.separator()

                # Auth
                if settings.ai_consent_granted:
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label(_("AI Session")).classes(
                            "text-sm font-bold text-slate-600"
                        )
                        ui.button(
                            _("Logout from AI"),
                            icon="logout",
                            on_click=confirm_logout,
                            color="red",
                        ).props("flat")

    def render_protocols_placeholder():
        with ui.card().classes("w-full p-8 shadow-md"):
            ui.label(_("Extraction Protocols")).classes("text-h4 q-mb-md font-bold")
            ui.markdown(
                _(
                    "This area will allow you to manage extraction protocols, including file exclusion patterns and hierarchical prompts."
                )
            )
            with ui.row().classes("gap-4 mt-8"):
                ui.icon("construction", size="lg", color="orange")
                ui.label(_("Under Construction")).classes("text-h6 text-orange-600")

    def render_package_placeholder():
        with ui.card().classes("w-full p-8 shadow-md"):
            ui.label(_("Package Content Editor")).classes("text-h4 q-mb-md font-bold")
            ui.markdown(
                _(
                    "This area will provide an interactive file tree to manually include or exclude files from the final package."
                )
            )
            with ui.row().classes("gap-4 mt-8"):
                ui.icon("construction", size="lg", color="orange")
                ui.label(_("Under Construction")).classes("text-h6 text-orange-600")

    def render_setup_wizard():
        with ui.card().classes(
            "w-full max-w-xl p-8 shadow-xl border-t-4 border-primary"
        ):
            ui.label(_("AI Configuration")).classes("text-h4 q-mb-md font-bold")
            with ui.tabs().classes("w-full") as tabs:
                google_tab = ui.tab("Google Gemini").classes("w-1/2")
                openai_tab = ui.tab("OpenAI / Ollama").classes("w-1/2")
            with ui.tab_panels(
                tabs,
                value="Google Gemini"
                if settings.ai_provider == "google"
                else "OpenAI / Ollama",
            ).classes("w-full"):
                with ui.tab_panel(google_tab):
                    ui.markdown(
                        _(
                            "Uses **Google Gemini** (Recommended). No API keys needed—just sign in."
                        )
                    )
                    with ui.expansion(
                        _("Security & Privacy FAQ"), icon="security"
                    ).classes("bg-blue-50 q-mb-lg"):
                        faq_items = [
                            _("Read-Only: We never modify your research files."),
                            _("Local: Analysis happens on your machine."),
                            _(
                                "Consent: We only send text snippets to AI with your permission."
                            ),
                        ]
                        ui.markdown("\n".join([f"- {item}" for item in faq_items]))
                    ui.button(
                        _("Sign in with Google"),
                        icon="login",
                        on_click=lambda: handle_auth_provider("google"),
                    ).classes("w-full py-4 bg-primary text-white font-bold rounded-lg")
                with ui.tab_panel(openai_tab):
                    ui.markdown(
                        _(
                            "Connect to **OpenAI**, **Ollama**, or compatible local APIs."
                        )
                    )
                    api_key_input = ui.input(
                        label=_("API Key"),
                        password=True,
                        placeholder="sk-...",
                        value=settings.openai_api_key or "",
                    ).classes("w-full")
                    base_url_input = ui.input(
                        label=_("Base URL"),
                        placeholder="https://api.openai.com/v1",
                        value=settings.openai_base_url,
                    ).classes("w-full")
                    model_input = ui.input(
                        label=_("Model Name"),
                        placeholder="gpt-3.5-turbo",
                        value=settings.openai_model,
                    ).classes("w-full")
                    ui.markdown(
                        _(
                            "**Common Local URLs:**\n- Ollama: `http://localhost:11434/v1`\n- LocalAI: `http://localhost:8080/v1`"
                        )
                    )

                    async def save_openai():
                        settings.openai_api_key = api_key_input.value
                        settings.openai_base_url = base_url_input.value
                        settings.openai_model = model_input.value
                        settings.ai_provider = "openai"
                        await handle_auth_provider("openai")

                    ui.button(
                        _("Save & Connect"), icon="link", on_click=save_openai
                    ).classes(
                        "w-full py-4 bg-secondary text-white font-bold rounded-lg q-mt-md"
                    )

    def render_analysis_dashboard():
        def on_splitter_change(e):
            settings.splitter_value = e.value
            wm.save_yaml(settings, "settings.yaml")

        with ui.splitter(
            value=settings.splitter_value, on_change=on_splitter_change
        ).classes("w-full h-[calc(100vh-110px)] min-h-[600px]") as splitter:
            with splitter.before:
                with ui.column().classes("w-full h-full pr-4"):
                    with ui.card().classes("w-full h-full p-0 shadow-md flex flex-col"):
                        with ui.row().classes(
                            "bg-slate-100 text-slate-800 p-3 w-full justify-between items-center shrink-0"
                        ):
                            ui.label(_("Agent Interaction")).classes("font-bold")
                            with ui.row().classes("gap-2"):
                                ui.button(
                                    icon="delete_sweep", on_click=handle_clear_chat
                                ).props("flat dense color=red").classes("text-xs")
                                ui.tooltip(_("Clear Chat History"))
                        with ui.scroll_area().classes("flex-grow w-full"):
                            chat_messages_ui()
                        with ui.row().classes(
                            "bg-white p-3 border-t w-full items-center no-wrap gap-2 shrink-0"
                        ):
                            user_input = (
                                ui.textarea(
                                    placeholder=_(
                                        "Type your response (Ctrl+Enter or button to send)..."
                                    )
                                )
                                .classes("flex-grow")
                                .props("rows=3")
                            )

                            async def handle_ctrl_enter(e):
                                if getattr(e.args, "ctrlKey", False):
                                    await handle_user_msg(user_input)

                            user_input.on("keydown.enter", handle_ctrl_enter)
                            ui.button(
                                icon="send",
                                on_click=lambda: handle_user_msg(user_input),
                            ).props("round elevated color=primary")

            with splitter.after:
                with ui.column().classes("w-full h-full pl-4"):
                    with ui.card().classes(
                        "w-full h-full p-4 shadow-md border-l-4 border-green-500 flex flex-col"
                    ):
                        with ui.row().classes(
                            "w-full justify-between items-center q-mb-md shrink-0"
                        ):
                            ui.label(_("RODBUK Metadata")).classes(
                                "text-h6 font-bold text-green-800"
                            )
                            ui.button(
                                icon="refresh", on_click=handle_clear_metadata
                            ).props("flat dense color=orange")
                            ui.tooltip(_("Reset Metadata"))
                        with ui.column().classes("gap-2 q-mb-md w-full shrink-0"):
                            path_input = (
                                ui.input(
                                    label=_("Project Path"),
                                    placeholder="/path/to/research",
                                )
                                .classes("w-full")
                                .bind_value(ScanState, "current_path")
                            )
                            ui.button(
                                _("Analyze Directory"),
                                icon="search",
                                on_click=lambda: handle_scan(
                                    path_input.value, force=True
                                ),
                            ).classes("w-full").bind_visibility_from(
                                ScanState, "is_scanning", backward=lambda x: not x
                            )
                            ui.button(
                                _("Cancel Scan"),
                                icon="stop",
                                on_click=handle_cancel_scan,
                                color="red",
                            ).classes("w-full").bind_visibility_from(
                                ScanState, "is_scanning"
                            )
                        with ui.scroll_area().classes("flex-grow w-full"):
                            metadata_preview_ui()

    async def handle_build_package():
        if not ScanState.current_path:
            ui.notify(_("Please select a project first."), type="warning")
            return

        # Validation
        errors = packaging_service.validate_for_rodbuk(agent.current_metadata)
        if errors:
            ui.notify(
                _("Metadata validation failed:") + "\n" + "\n".join(errors),
                type="negative",
                multi_line=True,
            )
            return

        try:
            ui.notify(_("Building metadata package..."))
            import asyncio

            pkg_path = await asyncio.to_thread(
                packaging_service.generate_metadata_package,
                Path(ScanState.current_path),
                agent.current_metadata,
            )
            ui.notify(
                _("Package created: {name}").format(name=pkg_path.name), type="positive"
            )
            # Trigger browser download
            ui.download(pkg_path)

            # Add a message to the chat history for visibility
            agent.chat_history.append(
                (
                    "assistant",
                    _("Package created successfully: {name}").format(
                        name=pkg_path.name
                    ),
                )
            )
            chat_messages_ui.refresh()
        except Exception as e:
            ui.notify(
                _("Failed to build package: {error}").format(error=str(e)),
                type="negative",
            )

    async def handle_auth_provider(provider: str):
        settings.ai_provider = provider
        wm.save_yaml(settings, "settings.yaml")
        ai.reload_provider(settings)
        if ai.authenticate(silent=False):
            settings.ai_consent_granted = True
            wm.save_yaml(settings, "settings.yaml")
            ui.navigate.to("/")
        else:
            msg = _("Authorization failed.")
            if provider == "google":
                msg += " " + _("Please ensure client_secrets.json is present.")
            else:
                msg += " " + _("Could not connect to API.")
            ui.notify(msg, type="negative")

    async def handle_logout():
        ai.logout()
        settings.ai_consent_granted = False
        wm.save_yaml(settings, "settings.yaml")
        ui.notify(_("Logged out from AI"))
        ui.navigate.to("/")

    async def handle_load_project(path: str):
        if not path:
            return
        ScanState.current_path = path
        import asyncio

        await asyncio.to_thread(agent.start_analysis, Path(path))
        if agent.current_metadata.ai_model:
            ai.switch_model(agent.current_metadata.ai_model)
            ui.notify(
                _("Restored project model: {model}").format(
                    model=agent.current_metadata.ai_model
                )
            )
            header_content_ui.refresh()
        chat_messages_ui.refresh()
        metadata_preview_ui.refresh()

    async def handle_cancel_scan():
        if ScanState.stop_event:
            ScanState.stop_event.set()
            ui.notify(_("Cancelling scan..."))

    async def handle_scan(path: str, force: bool = False):
        if not path:
            ui.notify(_("Please provide a path"), type="warning")
            return
        ScanState.current_path = path
        resolved_path = Path(path).expanduser()
        import threading

        ScanState.stop_event = threading.Event()
        ScanState.is_scanning = True
        ScanState.progress = _("Initializing...")
        metadata_preview_ui.refresh()

        def update_progress(msg, full_path="", short_path=""):
            ScanState.progress = msg
            ScanState.full_path = full_path
            ScanState.short_path = short_path

        import asyncio

        await asyncio.to_thread(
            agent.start_analysis,
            resolved_path,
            update_progress,
            force_rescan=force,
            stop_event=ScanState.stop_event,
        )
        ScanState.is_scanning = False
        ScanState.stop_event = None
        chat_messages_ui.refresh()
        metadata_preview_ui.refresh()

    async def handle_user_msg(input_element):
        text = input_element.value
        if not text:
            return
        input_element.value = ""
        # The agent.process_user_input now handles appending to chat_history
        # and we pass it a lambda to refresh the UI immediately when it does.

        import asyncio

        await asyncio.to_thread(
            agent.process_user_input,
            text,
            ai,
            skip_user_append=False,
            on_update=chat_messages_ui.refresh,
        )
        chat_messages_ui.refresh()
        metadata_preview_ui.refresh()
        ui.run_javascript("window.scrollTo(0, document.body.scrollHeight)")

    async def handle_clear_chat():
        agent.clear_chat_history()
        chat_messages_ui.refresh()
        ui.notify(_("Chat history cleared"))

    async def handle_clear_metadata():
        agent.clear_metadata()
        metadata_preview_ui.refresh()
        ui.notify(_("Metadata reset"))

    def set_lang(l):
        settings.language = l
        wm.save_yaml(settings, "settings.yaml")
        setup_i18n(l)
        ui.navigate.to("/")

    ui.run(title="OpenData Agent", port=port, show=False, reload=False, host=host)


if __name__ == "__main__":
    start_ui()
