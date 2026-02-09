import re
import yaml
import asyncio
from nicegui import ui
import webbrowser
from pathlib import Path
from typing import Any, List
from opendata.utils import get_local_ip, format_size
from opendata.workspace import WorkspaceManager
from opendata.packager import PackagingService
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.ai.service import AIService
from opendata.models import (
    Metadata,
    PersonOrOrg,
    Contact,
    RelatedResource,
    ExtractionProtocol,
)
from opendata.protocols.manager import ProtocolManager
from opendata.packaging.manager import PackageManager
from opendata.i18n.translator import setup_i18n, _


def start_ui(host: str = "127.0.0.1", port: int = 8080):
    # 1. Initialize Backend
    wm = WorkspaceManager()
    settings = wm.get_settings()
    setup_i18n(settings.language)

    agent = ProjectAnalysisAgent(wm)
    ai = AIService(Path(settings.workspace_path), settings)
    pm = ProtocolManager(wm)
    pkg_mgr = PackageManager(wm)
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

    import time
    import logging

    logger = logging.getLogger("opendata.ui")

    class UIState:
        main_tabs: Any = None
        analysis_tab: Any = None
        package_tab: Any = None
        preview_tab: Any = None
        inventory_cache: List[dict] = []
        last_inventory_project: str = ""
        is_loading_inventory: bool = False
        # Performance & Stability state
        inventory_lock: bool = False
        last_refresh_time: float = 0.0
        pending_refresh: bool = False

    async def load_inventory_background():
        """Load inventory in background with lock to prevent concurrent runs."""
        if not agent.project_id or ScanState.is_scanning:
            return

        if UIState.inventory_lock:
            return

        UIState.inventory_lock = True
        UIState.is_loading_inventory = True
        try:
            render_package_tab.refresh()
            project_path = Path(ScanState.current_path)
            manifest = pkg_mgr.get_manifest(agent.project_id)

            field_name = (
                agent.current_metadata.science_branches_mnisw[0]
                if agent.current_metadata.science_branches_mnisw
                else None
            )
            from opendata.protocols.manager import ProtocolManager

            pm_internal = ProtocolManager(wm)
            effective = pm_internal.resolve_effective_protocol(
                agent.project_id, field_name
            )
            protocol_excludes = effective.get("exclude", [])

            inventory = await asyncio.to_thread(
                pkg_mgr.get_inventory_for_ui, project_path, manifest, protocol_excludes
            )

            UIState.inventory_cache = inventory
            UIState.last_inventory_project = agent.project_id
        except Exception as e:
            logger.error(f"Failed to load inventory: {e}")
        finally:
            UIState.is_loading_inventory = False
            UIState.inventory_lock = False
            render_package_tab.refresh()

    async def refresh_all_debounced():
        if UIState.pending_refresh:
            return
        UIState.pending_refresh = True
        await asyncio.sleep(0.15)
        UIState.pending_refresh = False
        try:
            chat_messages_ui.refresh()
            metadata_preview_ui.refresh()
            header_content_ui.refresh()
            render_preview_and_build.refresh()
        except Exception:
            pass

    def refresh_all():
        now = time.time()
        if now - UIState.last_refresh_time < 0.2:
            asyncio.create_task(refresh_all_debounced())
            return
        UIState.last_refresh_time = now
        try:
            chat_messages_ui.refresh()
            metadata_preview_ui.refresh()
            header_content_ui.refresh()
            render_preview_and_build.refresh()
        except Exception:
            pass

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

    def render_analysis_form(analysis: Any):
        with ui.card().classes(
            "w-full mt-4 p-4 bg-white border border-slate-200 shadow-sm"
        ):
            ui.label(_("Refinement Form")).classes(
                "text-sm font-bold text-slate-700 mb-2"
            )

            form_data = {}

            # 1. Handle Conflicts
            if analysis.conflicting_data:
                ui.label(_("Resolve Conflicts")).classes(
                    "text-xs font-bold text-orange-600 mt-2"
                )
                for conflict in analysis.conflicting_data:
                    field = conflict.get("field", "unknown")
                    sources = conflict.get("sources", [])
                    # Ensure values are strings for select options keys
                    options = {
                        str(
                            s.get("value", "")
                        ): f"{str(s.get('value', ''))} (Source: {s.get('source', 'unknown')})"
                        for s in sources
                    }

                    with ui.row().classes("w-full items-center gap-2"):
                        ui.label(field.replace("_", " ").title()).classes(
                            "text-xs w-24"
                        )
                        form_data[field] = (
                            ui.select(
                                options=options,
                                value=str(sources[0].get("value", ""))
                                if sources
                                else None,
                            )
                            .props("dense outlined")
                            .classes("flex-grow")
                        )

            # 2. Handle Questions
            if analysis.questions:
                ui.label(_("Additional Information")).classes(
                    "text-xs font-bold text-blue-600 mt-2"
                )
                for q in analysis.questions:
                    with ui.column().classes("w-full gap-1 mt-1"):
                        ui.label(q.question).classes("text-xs text-slate-600")
                        if q.type == "choice":
                            form_data[q.field] = (
                                ui.select(options=q.options or [], label=q.label)
                                .props("dense outlined")
                                .classes("w-full")
                            )
                        else:
                            form_data[q.field] = (
                                ui.input(label=q.label)
                                .props("dense outlined")
                                .classes("w-full")
                            )

            async def submit_form():
                # Extract values from NiceGUI components
                final_answers = {}
                for field, component in form_data.items():
                    final_answers[field] = component.value

                agent.submit_analysis_answers(final_answers, on_update=refresh_all)
                ui.notify(_("Metadata updated from form."), type="positive")

            ui.button(_("Update Metadata"), on_click=submit_form).props(
                "elevated color=primary icon=check"
            ).classes("w-full mt-4")

    @ui.refreshable
    def chat_messages_ui():
        with ui.column().classes("w-full gap-1 overflow-x-hidden"):
            for i, (role, msg) in enumerate(agent.chat_history):
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

                            # If this is the last agent message and we have an active analysis, show the form
                            if (
                                i == len(agent.chat_history) - 1
                                and agent.current_analysis
                            ):
                                render_analysis_form(agent.current_analysis)

            if ScanState.is_scanning or ScanState.is_processing_ai:
                with ui.row().classes("w-full justify-start"):
                    with ui.card().classes(
                        "bg-gray-100 border border-gray-200 rounded-lg py-0.5 px-3 w-full shadow-none"
                    ):
                        with ui.row().classes("items-center gap-1"):
                            label_text = (
                                _("Scanning project...")
                                if ScanState.is_scanning
                                else _("AI is thinking...")
                            )
                            ui.markdown(label_text).classes(
                                "text-sm text-gray-800 m-0 p-0"
                            )
                            ui.spinner(size="xs")
                            if ScanState.is_scanning:
                                ui.button("", on_click=handle_cancel_scan).props(
                                    "icon=close flat color=gray size=xs"
                                ).classes("min-h-6 min-w-6 p-0.5")
        ui.run_javascript("window.scrollTo(0, document.body.scrollHeight)")

    class ScanState:
        is_scanning = False
        is_processing_ai = False
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
        try:
            header_content_ui.refresh()  # type: ignore
        except Exception:
            pass

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

                if key == "description":
                    # Convert list of strings to markdown paragraphs
                    md_text = "\n\n".join(text) if isinstance(text, list) else text
                    content = ui.markdown(md_text).classes(
                        "px-3 py-2 text-sm text-gray-800 break-words overflow-hidden transition-all duration-300 cursor-pointer"
                    )
                    # Fixed height to avoid cutting lines + line-clamp for ellipsis
                    content.style(
                        "max-height: 120px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 6; -webkit-box-orient: vertical;"
                    )
                elif key == "keywords":
                    # Join keywords with commas
                    kw_text = ", ".join(text) if isinstance(text, list) else text
                    content = ui.markdown(kw_text).classes(
                        "px-2 py-0 text-sm text-gray-800 break-words overflow-hidden transition-all duration-300 cursor-pointer"
                    )
                    content.style("max-height: 110px; line-height: 1.5;")
                else:
                    # Fallback for other fields, ensuring string conversion
                    display_text = str(text)
                    content = ui.markdown(display_text).classes(
                        "px-2 py-0 text-sm text-gray-800 break-words overflow-hidden transition-all duration-300 cursor-pointer"
                    )
                    content.style("max-height: 110px; line-height: 1.5;")

                if key:
                    content.on("click", lambda: open_edit_dialog(key))

                # Logic for single MORE button for description
                if (
                    (key == "description" and isinstance(text, list) and len(text) > 0)
                    or (isinstance(text, list) and len(text) > 1)
                    or len(str(text)) > 300
                ):

                    def toggle(e, target=content):
                        is_expanded = target.style["max-height"] == "none"
                        if key == "description":
                            target.style(
                                f"max-height: {'120px' if is_expanded else 'none'}; -webkit-line-clamp: {'6' if is_expanded else 'unset'}"
                            )
                        else:
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
                        # Special handling for description: use double newlines for paragraphs
                        if key == "description":
                            current_text = "\n\n".join(val) if val else ""
                            help_text = _(
                                "Enter one paragraph per block. Use double newlines to separate."
                            )
                        else:
                            current_text = "\n".join(val) if val else ""
                            help_text = _("Enter one item per line.")

                        edit_area = (
                            ui.textarea(value=current_text)
                            .classes("w-full")
                            .props("rows=10 auto-grow")
                        )
                        ui.markdown(help_text).classes("text-xs text-slate-500")
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
                                    parsed_list = yaml.safe_load(new_val)
                                    if not isinstance(parsed_list, list):
                                        raise ValueError("YAML must be a list")
                                    setattr(agent.current_metadata, key, parsed_list)
                                else:
                                    # Special parsing for description: split by double newlines or single newlines
                                    if key == "description":
                                        # Split by double newlines to get paragraphs
                                        new_list = [
                                            p.strip()
                                            for p in re.split(r"\n\s*\n", new_val)
                                            if p.strip()
                                        ]
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

        with ui.column().classes("w-full gap-2"):
            for key, value in fields.items():
                if key == "locked_fields":
                    continue
                if key == "authors" or key == "contacts":
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                    )
                    with ui.row().classes("w-full gap-1 flex-wrap items-center mt--1"):
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
                                        "click",
                                        lambda _e, k=key: open_edit_dialog(k),
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
                                                "business",
                                                size="0.75rem",
                                                color="blue",
                                            ).classes("inline-block align-middle")
                                        if email:
                                            ui.icon(
                                                "email",
                                                size="0.75rem",
                                                color="indigo",
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
                elif key == "description":
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                    )
                    with ui.column().classes("w-full gap-0 mt--1"):
                        create_expandable_text(value, key=key)
                elif key == "keywords":
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                    )
                    with ui.row().classes(
                        "w-full gap-1 flex-wrap items-center relative group mt--1"
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
                elif (
                    key == "science_branches_mnisw"
                    or key == "science_branches_oecd"
                    or key == "software"
                    or key == "languages"
                ):
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                    )
                    with ui.row().classes("w-full gap-1 flex-wrap items-center mt--1"):
                        for item in value:
                            ui.label(str(item)).classes(
                                "text-sm bg-slate-100 py-0.5 px-2 rounded border border-slate-200 inline-block mr-1 mb-1"
                            )
                elif key == "related_publications":
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                    )
                    with ui.column().classes("w-full gap-1 items-start mt--1"):
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
                elif key == "software":
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                    )
                    with ui.row().classes(
                        "w-full gap-1 flex-wrap items-center relative group"
                    ) as soft_container:
                        is_locked = key in agent.current_metadata.locked_fields
                        soft_container.on(
                            "click", lambda _e, k=key: open_edit_dialog(k)
                        )

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

                        for s in value:
                            ui.label(str(s)).classes(
                                "text-sm bg-purple-50 text-purple-800 py-0.5 px-2 rounded border border-purple-100 inline-block mr-1 mb-1"
                            )
                elif key == "funding":
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                    )
                    with ui.column().classes("w-full gap-1 items-start mt--1"):
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
                        "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                    )
                    if isinstance(value, list):
                        with ui.column().classes("w-full gap-1 mt--1"):
                            for v_item in value:
                                create_expandable_text(str(v_item), key=key)
                    else:
                        with ui.column().classes("w-full mt--1"):
                            create_expandable_text(str(value), key=key)

    @ui.refreshable
    def project_selector_ui():
        if not settings.ai_consent_granted:
            return
        projects = wm.list_projects()

        # Identify current project by path to set as default value
        current_val = ScanState.current_path if ScanState.current_path else None

        with ui.row().classes("items-center no-wrap gap-1"):
            project_options = {
                p["path"]: f"{p['title']} ({p['path']})" for p in projects
            }

            if not project_options:
                return

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
            # Bind selector value to ScanState.current_path to keep it in sync
            selector.bind_value(ScanState, "current_path")

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
        ui.add_head_html("""
            <style>
                .nicegui-content { padding: 4px !important; }
            </style>
        """)
        ui.query("body").style("background-color: #f8f9fa; margin: 0; padding: 0;")
        ui.query("html").style("margin: 0; padding: 0;")

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

                UIState.main_tabs = main_tabs
                UIState.analysis_tab = analysis_tab
                UIState.package_tab = package_tab
                UIState.preview_tab = preview_tab

        container = ui.column().classes("w-full p-0 max-w-none mx-0 h-full")
        with container:
            if not settings.ai_consent_granted:
                render_setup_wizard()
            else:
                with ui.tab_panels(main_tabs, value=analysis_tab).classes(
                    "w-full bg-transparent p-0 h-full"
                ):
                    with ui.tab_panel(analysis_tab).classes("p-0 h-full"):
                        render_analysis_dashboard()
                    with ui.tab_panel(protocols_tab):
                        render_protocols_tab()
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
                    with ui.row().classes("gap-2"):
                        ui.button(
                            _("Metadata Only"),
                            icon="description",
                            color="blue",
                            on_click=lambda: handle_build_package(mode="metadata"),
                        ).classes("px-4").props("outline")
                        ui.button(
                            _("Build Full Package"),
                            icon="archive",
                            color="green",
                            on_click=lambda: handle_build_package(mode="full"),
                        ).classes("px-6 font-bold")

                ui.markdown(
                    _(
                        "Review your metadata before generating the final package. The full package will respect your file selection."
                    )
                )
                ui.separator().classes("my-4")

                # Reuse metadata preview logic
                metadata_preview_ui()

            with ui.card().classes("w-full p-6 shadow-md"):
                ui.label(_("Final Selection Summary")).classes("text-h6 font-bold mb-2")
                if agent.project_id:
                    project_path = Path(ScanState.current_path)
                    manifest = pkg_mgr.get_manifest(agent.project_id)
                    # Resolve protocol to show current effective count
                    field_name = (
                        agent.current_metadata.science_branches_mnisw[0]
                        if agent.current_metadata.science_branches_mnisw
                        else None
                    )
                    effective = pm.resolve_effective_protocol(
                        agent.project_id, field_name
                    )
                    protocol_excludes = effective.get("exclude", [])
                    eff_list = pkg_mgr.get_effective_file_list(
                        project_path, manifest, protocol_excludes
                    )
                    total_size = sum(p.stat().st_size for p in eff_list if p.exists())

                    with ui.row().classes("gap-4 items-center"):
                        ui.icon("inventory", size="md", color="slate-600")
                        with ui.column().classes("gap-0"):
                            ui.label(
                                _("{count} files selected for inclusion").format(
                                    count=len(eff_list)
                                )
                            ).classes("font-bold")
                            ui.label(
                                _("Estimated Package Data Size: {size}").format(
                                    size=format_size(total_size)
                                )
                            ).classes("text-sm text-slate-500")

                    ui.button(
                        _("Edit Selection"),
                        icon="edit",
                        on_click=lambda: UIState.main_tabs.set_value(
                            UIState.package_tab
                        ),
                    ).classes("mt-4").props("flat color=primary")
                else:
                    ui.label(_("No project active.")).classes("text-slate-400 italic")

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

    @ui.refreshable
    def render_protocols_tab():
        with ui.column().classes("w-full gap-4"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(_("Extraction Protocols")).classes("text-h4 font-bold")
                with ui.row().classes("gap-2"):
                    ui.icon("info", color="primary").classes("cursor-help")
                    ui.tooltip(
                        _(
                            "Protocols guide the AI and scanner. Rules are applied from System to Project level."
                        )
                    )

            with ui.tabs().classes("w-full") as protocol_tabs:
                sys_tab = ui.tab(_("System"), icon="settings_suggest")
                glob_tab = ui.tab(_("Global"), icon="public")
                field_tab = ui.tab(_("Field/Domain"), icon="science")
                proj_tab = ui.tab(_("Project"), icon="folder_special")

            with ui.tab_panels(protocol_tabs, value=sys_tab).classes(
                "w-full bg-white border rounded shadow-sm"
            ):
                with ui.tab_panel(sys_tab):
                    render_protocol_editor(pm.system_protocol)
                with ui.tab_panel(glob_tab):
                    render_protocol_editor(
                        pm.get_global_protocol(), on_save=pm.save_global_protocol
                    )
                with ui.tab_panel(field_tab):
                    # For fields, we need a selector
                    current_fields = pm.list_fields()
                    field_container = ui.column().classes("w-full")

                    def refresh_field_editor():
                        field_container.clear()
                        if field_select.value:
                            with field_container:
                                render_protocol_editor(
                                    pm.get_field_protocol(field_select.value),
                                    on_save=pm.save_field_protocol,
                                )

                    with ui.column().classes("w-full gap-4 mb-4"):
                        with ui.row().classes("w-full items-center gap-4"):
                            field_select = ui.select(
                                options=current_fields,
                                label=_("Select Field Domain"),
                                value=current_fields[0] if current_fields else None,
                            ).classes("w-64")

                            new_field_input = (
                                ui.input(label=_("New Field Name"))
                                .classes("w-48")
                                .props("dense")
                            )

                            def create_new_field():
                                name = new_field_input.value.strip()
                                if not name:
                                    ui.notify(
                                        _("Field name cannot be empty."), type="warning"
                                    )
                                    return
                                new_p = pm.get_field_protocol(name)
                                pm.save_field_protocol(new_p)
                                ui.notify(
                                    _("Field '{name}' created.").format(name=name)
                                )
                                # Update selector
                                new_fields = pm.list_fields()
                                field_select.options = new_fields
                                field_select.value = name
                                new_field_input.value = ""
                                refresh_field_editor()

                            ui.button(
                                _("Create Field"), icon="add", on_click=create_new_field
                            ).props("outline")

                        field_container = ui.column().classes("w-full mt-4")

                        field_select.on("update:model-value", refresh_field_editor)
                        refresh_field_editor()

                with ui.tab_panel(proj_tab):
                    if agent.project_id:
                        render_protocol_editor(
                            pm.get_project_protocol(agent.project_id),
                            on_save=lambda p: pm.save_project_protocol(
                                agent.project_id, p
                            ),
                        )
                    else:
                        with ui.column().classes("w-full items-center p-8"):
                            ui.icon("folder_open", size="lg", color="grey-400")
                            ui.label(
                                _("Please select and open a project first.")
                            ).classes("text-orange-600 font-bold")
                            ui.markdown(
                                _(
                                    "Use the **Open** button in the Analysis tab to activate this project."
                                )
                            ).classes("text-sm text-slate-500")

    def render_protocol_editor(protocol: ExtractionProtocol, on_save=None):
        is_readonly = protocol.is_read_only

        with ui.column().classes("w-full gap-6 p-4"):
            if is_readonly:
                ui.label(_("This protocol is Read-Only.")).classes(
                    "text-xs text-orange-600 italic"
                )

            # Exclusion Patterns
            with ui.column().classes("w-full gap-2"):
                ui.label(_("Exclude Patterns (Glob)")).classes(
                    "text-sm font-bold text-slate-700"
                )
                exclude_area = (
                    ui.textarea(value="\n".join(protocol.exclude_patterns))
                    .classes("w-full font-mono text-sm")
                    .props(f"outlined {'readonly' if is_readonly else ''} rows=4")
                )
                ui.markdown(
                    _("One pattern per line. e.g. `**/temp/*` or `*.log`")
                ).classes("text-[10px] text-slate-500")

            # Include Patterns
            with ui.column().classes("w-full gap-2"):
                ui.label(_("Include Patterns (Glob)")).classes(
                    "text-sm font-bold text-slate-700"
                )
                include_area = (
                    ui.textarea(value="\n".join(protocol.include_patterns))
                    .classes("w-full font-mono text-sm")
                    .props(f"outlined {'readonly' if is_readonly else ''} rows=3")
                )
                ui.markdown(_("Force include specific files.")).classes(
                    "text-[10px] text-slate-500"
                )

            # AI Prompts
            with ui.column().classes("w-full gap-2"):
                ui.label(_("AI Instructions / Prompts")).classes(
                    "text-sm font-bold text-slate-700"
                )
                prompts_area = (
                    ui.textarea(value="\n".join(protocol.extraction_prompts))
                    .classes("w-full text-sm")
                    .props(f"outlined {'readonly' if is_readonly else ''} rows=6")
                )
                ui.markdown(_("Specific instructions for the AI agent.")).classes(
                    "text-[10px] text-slate-500"
                )

            if not is_readonly and on_save:

                def handle_save():
                    protocol.exclude_patterns = [
                        l.strip() for l in exclude_area.value.split("\n") if l.strip()
                    ]
                    protocol.include_patterns = [
                        l.strip() for l in include_area.value.split("\n") if l.strip()
                    ]
                    protocol.extraction_prompts = [
                        l.strip() for l in prompts_area.value.split("\n") if l.strip()
                    ]
                    on_save(protocol)
                    ui.notify(
                        _("Protocol '{name}' saved.").format(name=protocol.name),
                        type="positive",
                    )

                ui.button(_("Save Changes"), icon="save", on_click=handle_save).classes(
                    "w-full mt-4"
                ).props("color=primary")

    @ui.refreshable
    def render_package_tab():
        # Package Content Editor
        if not agent.project_id:
            with ui.card().classes("w-full p-8 shadow-md"):
                with ui.column().classes("w-full items-center p-8"):
                    ui.icon("folder_open", size="lg", color="grey-400")
                    ui.label(_("Please select and open a project first.")).classes(
                        "text-orange-600 font-bold"
                    )
            return

        # Explicit Requirement: Only use SQLite cache. Never scan disk implicitly during render.
        # Check if project changed and we haven't loaded cache yet
        if UIState.last_inventory_project != agent.project_id:
            # We don't trigger scanning here. We just show empty state or trigger loading if DB exists.
            # However, handle_load_project should have triggered load_inventory_background.
            if not UIState.is_loading_inventory:
                asyncio.create_task(load_inventory_background())

        if UIState.is_loading_inventory and not UIState.inventory_cache:
            with ui.column().classes("w-full items-center justify-center p-20 gap-4"):
                ui.spinner(size="xl")
                ui.label(_("Reading project inventory from database...")).classes(
                    "text-slate-500 animate-pulse"
                )
            return

        if not UIState.inventory_cache:
            with ui.column().classes("w-full items-center justify-center p-20 gap-4"):
                ui.icon("inventory", size="xl", color="grey-400")
                ui.label(_("No file inventory found.")).classes(
                    "text-orange-600 font-bold"
                )
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

        project_path = Path(ScanState.current_path)
        manifest = pkg_mgr.get_manifest(agent.project_id)
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
                        on_click=handle_refresh_inventory,
                    ).props("outline color=primary").bind_visibility_from(
                        ScanState, "is_scanning", backward=lambda x: not x
                    )
                    ui.button(
                        _("Reset to Defaults"),
                        icon="settings_backup_restore",
                        on_click=lambda: handle_reset(),
                    ).props("outline color=grey-7")
                    ui.button(
                        _("AI Assist (Coming Soon)"),
                        icon="auto_awesome",
                    ).props("flat color=primary disabled")

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

            # The Grid
            grid_data = []
            for item in inventory:
                grid_data.append(
                    {
                        "included": item["included"],
                        "path": item["path"],
                        "size_val": item["size"],
                        "size": format_size(item["size"]),
                        "reason": item["reason"],
                    }
                )

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

            grid = ui.aggrid(
                {
                    "columnDefs": column_defs,
                    "rowData": grid_data,
                    "rowSelection": "multiple",
                    "stopEditingWhenCellsLoseFocus": True,
                    "pagination": True,
                    "paginationPageSize": 50,
                }
            ).classes("w-full h-[600px] shadow-sm")

            # Initial selection
            grid.options["selected_keys"] = [
                i for i, f in enumerate(grid_data) if f["included"]
            ]

            async def handle_selection_change():
                selected_rows = await grid.get_selected_rows()
                selected_paths = {row["path"] for row in selected_rows}

                new_force_include = []
                new_force_exclude = []

                # Use UIState.inventory_cache directly
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
                pkg_mgr.save_manifest(manifest)

                # Update cache so UI reflects change immediately
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

                refresh_all()

            grid.on("selectionChanged", handle_selection_change)

            async def handle_reset():
                manifest.force_include = []
                manifest.force_exclude = []
                pkg_mgr.save_manifest(manifest)
                ui.notify(_("Selection reset to protocol defaults."), type="info")
                # Selective refresh in background
                asyncio.create_task(load_inventory_background())

    def render_package_placeholder():
        render_package_tab()

    def refresh_all():
        chat_messages_ui.refresh()
        metadata_preview_ui.refresh()
        header_content_ui.refresh()
        render_protocols_tab.refresh()
        render_package_tab.refresh()

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

        # Header is ~56px (py-2 = 8px top + 8px bottom + ~40px content) + tabs ~48px = ~104px total
        with ui.splitter(
            value=settings.splitter_value, on_change=on_splitter_change
        ).classes("w-full h-[calc(100vh-104px)] min-h-[600px] m-0 p-0") as splitter:
            with splitter.before:
                with ui.column().classes("w-full h-full pr-2"):
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
                with ui.column().classes("w-full h-full pl-2"):
                    with ui.card().classes(
                        "w-full h-full p-3 shadow-md border-l-4 border-green-500 flex flex-col"
                    ):
                        with ui.row().classes(
                            "w-full justify-between items-center mb-1 shrink-0"
                        ):
                            ui.label(_("RODBUK Metadata")).classes(
                                "text-h5 font-bold text-green-800"
                            )
                            ui.button(
                                icon="refresh", on_click=handle_clear_metadata
                            ).props("flat dense color=orange")
                            ui.tooltip(_("Reset Metadata"))
                        with ui.column().classes("gap-1 mb-2 w-full shrink-0"):

                            def on_path_change(e):
                                if e.value and "~" in e.value:
                                    canonical = str(
                                        Path(e.value).expanduser().resolve()
                                    )
                                    ScanState.current_path = canonical
                                    # Update UI value to show the expansion
                                    path_input.value = canonical

                            path_input = (
                                ui.input(
                                    label=_("Project Path"),
                                    placeholder="/path/to/research",
                                    on_change=on_path_change,
                                )
                                .classes("flex-grow")
                                .props("dense")
                                .bind_value(ScanState, "current_path")
                            )
                            ui.button(
                                _("Open"),
                                on_click=lambda: handle_load_project(path_input.value),
                            ).props("dense outline").classes("shrink-0")

                        with ui.column().classes("gap-1 mb-2 w-full shrink-0"):
                            ui.button(
                                _("Analyze Directory"),
                                icon="search",
                                on_click=lambda: handle_scan(
                                    path_input.value, force=True
                                ),
                            ).classes("w-full").props("dense").bind_visibility_from(
                                ScanState, "is_scanning", backward=lambda x: not x
                            )
                            ui.button(
                                _("Cancel Scan"),
                                icon="stop",
                                on_click=handle_cancel_scan,
                                color="red",
                            ).classes("w-full").props("dense").bind_visibility_from(
                                ScanState, "is_scanning"
                            )
                            ui.separator().classes("mt-1")
                        with ui.scroll_area().classes("flex-grow w-full"):
                            metadata_preview_ui()

    async def handle_build_package(mode: str = "metadata"):
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
            ui.notify(
                _("Building metadata package...")
                if mode == "metadata"
                else _("Building full data package...")
            )
            import asyncio

            # Canonicalize path before passing to thread
            canonical_path = Path(ScanState.current_path).expanduser().resolve()

            if mode == "metadata":
                pkg_path = await asyncio.to_thread(
                    packaging_service.generate_metadata_package,
                    canonical_path,
                    agent.current_metadata,
                )
            else:
                # Full Package with Selection
                manifest = pkg_mgr.get_manifest(agent.project_id)
                field_name = (
                    agent.current_metadata.science_branches_mnisw[0]
                    if agent.current_metadata.science_branches_mnisw
                    else None
                )
                effective = pm.resolve_effective_protocol(agent.project_id, field_name)
                protocol_excludes = effective.get("exclude", [])

                file_list = await asyncio.to_thread(
                    pkg_mgr.get_effective_file_list,
                    canonical_path,
                    manifest,
                    protocol_excludes,
                )

                pkg_path = await asyncio.to_thread(
                    packaging_service.generate_package,
                    canonical_path,
                    agent.current_metadata,
                    "rodbuk_full_package",
                    file_list,
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

    async def handle_cancel_scan():
        if ScanState.stop_event:
            ScanState.stop_event.set()
            ui.notify(_("Cancelling scan..."))

    async def handle_refresh_inventory():
        if not ScanState.current_path:
            ui.notify(_("Please select a project first."), type="warning")
            return

        resolved_path = Path(ScanState.current_path).expanduser()
        import threading
        import asyncio

        ScanState.stop_event = threading.Event()
        ScanState.is_scanning = True
        ui.notify(_("Refreshing file list..."))

        def update_progress(msg, full_path="", short_path=""):
            ScanState.progress = msg
            # We reuse the global progress bar if visible, but mostly this is background
            pass

        await asyncio.to_thread(
            agent.refresh_inventory,
            resolved_path,
            update_progress,
            stop_event=ScanState.stop_event,
        )

        ScanState.is_scanning = False
        ScanState.stop_event = None

        # Force cache reload
        UIState.last_inventory_project = ""
        await load_inventory_background()
        ui.notify(_("File list updated."), type="positive")

    async def handle_load_project(path: str):
        if not path:
            return
        ui.notify(_("Opening project..."))

        path_obj = Path(path).expanduser().resolve()
        # Explicitly create project ID and active it
        project_id = wm.get_project_id(path_obj)
        agent.project_id = project_id

        # Force refresh of all components that depend on project_id
        # including the Protocols tab
        success = await asyncio.to_thread(agent.load_project, path_obj)
        ScanState.current_path = str(path_obj)

        if agent.current_metadata.ai_model:
            ai.switch_model(agent.current_metadata.ai_model)
            ui.notify(
                _("Restored project model: {model}").format(
                    model=agent.current_metadata.ai_model
                )
            )

        # Ensure workspace directory exists for protocols
        project_state_dir = wm.projects_dir / project_id
        project_state_dir.mkdir(parents=True, exist_ok=True)

        refresh_all()

        # Start inventory scan in background immediately after project load
        asyncio.create_task(load_inventory_background())

        # Refresh the entire tab view to propagate project_id
        render_protocols_tab.refresh()

        if success:
            ui.notify(_("Project opened from history."))
        else:
            ui.notify(_("New project directory opened."))

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

        ScanState.is_processing_ai = True
        refresh_all()

        await asyncio.to_thread(
            agent.process_user_input,
            text,
            ai,
            skip_user_append=False,
            on_update=refresh_all,
        )
        ScanState.is_processing_ai = False
        refresh_all()
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
