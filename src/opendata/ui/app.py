import re
import yaml
import asyncio
from nicegui import ui
import webbrowser
from pathlib import Path
from typing import Any, List, Literal
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

    class UIState:
        main_tabs: Any = None
        analysis_tab: Any = None
        package_tab: Any = None
        preview_tab: Any = None
        inventory_cache: List[dict] = []
        last_inventory_project: str = ""
        is_loading_inventory: bool = False
        # Debouncing state
        last_refresh_time: float = 0.0
        pending_refresh: bool = False
        # Inventory loading lock
        inventory_lock: bool = False

    import time
    import logging

    # Setup diagnostic logging for connection issues
    logger = logging.getLogger("opendata.ui")

    async def refresh_all_debounced():
        """Debounced refresh - waits 150ms before executing, skips if already pending."""
        if UIState.pending_refresh:
            return

        # Check if we have an active client/connection before refreshing
        try:
            if not ui.context.client:
                return
        except Exception:
            return

        UIState.pending_refresh = True
        await asyncio.sleep(0.15)
        UIState.pending_refresh = False

        # Verify client again after sleep
        try:
            if not ui.context.client or not ui.context.client.has_socket_connection:
                return
        except Exception:
            return

        try:
            chat_messages_ui.refresh()
            metadata_preview_ui.refresh()
            header_content_ui.refresh()
            render_protocols_tab.refresh()
            render_preview_and_build.refresh()
        except Exception:
            pass

    def refresh_all():
        """Synchronous refresh with throttling - max once per 200ms."""
        # Check if we have an active client
        try:
            if not ui.context.client or not ui.context.client.has_socket_connection:
                return
        except Exception:
            return

        now = time.time()
        if now - UIState.last_refresh_time < 0.2:
            # Schedule async debounced refresh instead
            asyncio.create_task(refresh_all_debounced())
            return
        UIState.last_refresh_time = now
        try:
            chat_messages_ui.refresh()
            metadata_preview_ui.refresh()
            header_content_ui.refresh()
            render_protocols_tab.refresh()
            render_preview_and_build.refresh()
        except Exception:
            pass

    async def load_inventory_background():
        """Load inventory in background with lock to prevent concurrent runs."""
        logger.info(
            f">>> DEBUG: load_inventory_background START for {agent.project_id}"
        )
        if not agent.project_id or ScanState.is_scanning:
            logger.info("DEBUG: Load aborted - no project_id or scan in progress.")
            return

        # Prevent concurrent inventory loading
        if UIState.inventory_lock:
            logger.info(f"DEBUG: Inventory load skipped - already locked.")
            return

        UIState.inventory_lock = True
        UIState.is_loading_inventory = True

        try:
            # Step 1: UI feedback
            logger.info("DEBUG: Inventory load step 1: Pre-refreshing Package tab...")
            render_package_tab.refresh()

            # Step 2: Path check
            if not ScanState.current_path:
                logger.error(
                    "DEBUG: Inventory load ERROR - ScanState.current_path is None"
                )
                return

            project_path = Path(ScanState.current_path)
            logger.info(f"DEBUG: Inventory load step 2: Project path is {project_path}")

            # Step 3: DB Load
            logger.info(
                "DEBUG: Inventory load step 3: Fetching from DB (background thread)..."
            )
            manifest = pkg_mgr.get_manifest(agent.project_id)

            field_name = (
                agent.current_metadata.science_branches_mnisw[0]
                if agent.current_metadata.science_branches_mnisw
                else None
            )
            effective = pm.resolve_effective_protocol(agent.project_id, field_name)
            protocol_excludes = effective.get("exclude", [])

            inventory = await asyncio.to_thread(
                pkg_mgr.get_inventory_for_ui, project_path, manifest, protocol_excludes
            )

            # Step 4: Cache update
            UIState.inventory_cache = inventory
            UIState.last_inventory_project = agent.project_id
            logger.info(
                f"DEBUG: Inventory load step 4: SUCCESS. {len(inventory)} files found."
            )

            if len(inventory) > 0:
                safe_notify(
                    _("File inventory loaded ({count} files)").format(
                        count=len(inventory)
                    ),
                    type="positive",
                )

        except Exception as e:
            logger.error(f"DEBUG: Inventory load CRITICAL ERROR: {e}", exc_info=True)
            safe_notify(
                _("Error loading file list: {error}").format(error=str(e)),
                type="negative",
            )
        finally:
            UIState.is_loading_inventory = False
            UIState.inventory_lock = False
            logger.info(
                "DEBUG: load_inventory_background FINISHED. Refreshing Package tab..."
            )
            try:
                render_package_tab.refresh()
            except Exception as e:
                logger.warning(f"DEBUG: Failed final refresh: {e}")

    def safe_notify(
        message: str,
        type: Literal["positive", "negative", "warning", "info", "ongoing"] = "info",
    ):
        try:
            ui.notify(message, type=type)
        except Exception:
            print(f"[NOTIFY FALLBACK] {type.upper()}: {message}")

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
        # Performance: limit rendered messages to last 50 to avoid WebSocket overload
        MAX_VISIBLE_MESSAGES = 50
        history = agent.chat_history
        total = len(history)
        start_idx = max(0, total - MAX_VISIBLE_MESSAGES)
        visible_history = history[start_idx:]

        with ui.column().classes("w-full gap-1 overflow-x-hidden"):
            # Show truncation notice if history was clipped
            if total > MAX_VISIBLE_MESSAGES:
                with ui.row().classes("w-full justify-center"):
                    ui.label(
                        _("Showing last {count} of {total} messages").format(
                            count=MAX_VISIBLE_MESSAGES, total=total
                        )
                    ).classes("text-xs text-slate-400 italic")

            for i, (role, msg) in enumerate(visible_history):
                # Adjust index for original position (for detecting last message)
                original_idx = start_idx + i
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
                                original_idx == len(agent.chat_history) - 1
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
        # Only scroll if not in bulk loading mode
        if not ScanState.is_loading_project:
            ui.run_javascript("window.scrollTo(0, document.body.scrollHeight)")

    class ScanState:
        is_scanning = False
        is_processing_ai = False
        is_loading_project = False  # NEW: Track project loading
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

        # NOTE: Removed header_content_ui.refresh() call here to prevent cascade refreshes
        # that could cause WebSocket overload. Header is refreshed via refresh_all() instead.

        fields = agent.current_metadata.model_dump(exclude_unset=True)

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
                    with ui.row().classes(
                        "w-full gap-1 flex-wrap items-center relative group mt--1"
                    ) as list_container:
                        list_container.on(
                            "click", lambda _e, k=key: open_edit_dialog(k)
                        )

                        # Lock for lists
                        is_locked = key in agent.current_metadata.locked_fields
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

            async def handle_delete_current():
                # Multi-stage ID resolution
                current_id = None
                projects = wm.list_projects()

                if ScanState.current_path:
                    target = next(
                        (p for p in projects if p["path"] == ScanState.current_path),
                        None,
                    )
                    if target:
                        current_id = target["id"]

                if not current_id and selector.value:
                    target = next(
                        (p for p in projects if p["path"] == selector.value), None
                    )
                    if target:
                        current_id = target["id"]

                if not current_id:
                    ui.notify(_("Select a project first"), type="warning")
                    return

                with ui.dialog() as confirm_dialog, ui.card().classes("p-4"):
                    ui.label(_("Permanently delete project state?"))
                    with ui.row().classes("w-full justify-end gap-2 mt-4"):
                        ui.button(_("Cancel"), on_click=confirm_dialog.close).props(
                            "flat"
                        )

                        async def perform_delete():
                            confirm_dialog.close()
                            if wm.delete_project(current_id):
                                ui.notify(_("Project deleted"))
                                ScanState.current_path = ""
                                agent.reset_agent_state()
                                header_content_ui.refresh()
                                metadata_preview_ui.refresh()
                                chat_messages_ui.refresh()

                        ui.button(_("Delete"), on_click=perform_delete).props(
                            "color=red"
                        )
                confirm_dialog.open()

    async def handle_load_project(path: str):
        if not path:
            return

        # Loading Guard: prevent infinite loops or concurrent loads
        if ScanState.is_loading_project:
            logger.info(
                f"DEBUG: Skipping handle_load_project - already loading something."
            )
            return

        # Avoid reloading the exact same path if already loaded
        if ScanState.current_path == path and agent.project_id:
            logger.info(
                f"DEBUG: Skipping handle_load_project - project already active."
            )
            return

        start_time = time.time()
        logger.info(f">>> DEBUG: Starting handle_load_project for: {path}")
        ScanState.is_loading_project = True
        safe_notify(_("Opening project..."))

        try:
            path_obj = Path(path).expanduser().resolve()
            project_id = wm.get_project_id(path_obj)
            agent.project_id = project_id

            logger.info(f"DEBUG: Project ID resolved: {project_id}")
            UIState.last_inventory_project = ""
            UIState.inventory_cache = []

            # Load project data
            logger.info("DEBUG: Loading state from disk...")
            metadata, history, fingerprint = await asyncio.to_thread(
                wm.load_project_state, project_id
            )
            ScanState.current_path = str(path_obj)
            success = metadata is not None
            logger.info(
                f"DEBUG: Disk load complete. Metadata: {success}, History lines: {len(history)}"
            )

            # Assign to agent
            if metadata:
                agent.current_metadata = metadata
                agent.chat_history = history
                agent.current_fingerprint = fingerprint

            # Switch model
            if agent.current_metadata.ai_model:
                logger.info(
                    f"DEBUG: Switching AI model to: {agent.current_metadata.ai_model}"
                )
                ai.switch_model(agent.current_metadata.ai_model)

            # Sequence UI Refresh with timing
            logger.info("DEBUG: Starting sequential UI refresh...")

            refresh_steps = [
                ("Header", header_content_ui),
                ("Metadata Preview", metadata_preview_ui),
                ("Protocols Tab", render_protocols_tab),
                ("Preview & Build", render_preview_and_build),
                ("Chat Messages", chat_messages_ui),
            ]

            for name, component in refresh_steps:
                step_start = time.time()
                logger.info(f"DEBUG: Refreshing {name}...")
                try:
                    component.refresh()
                    logger.info(
                        f"DEBUG: {name} refresh took {time.time() - step_start:.4f}s"
                    )
                except Exception as re:
                    logger.error(f"DEBUG: ERROR refreshing {name}: {re}")
                await asyncio.sleep(0.1)  # Increased sleep between components

            logger.info(
                f">>> DEBUG: handle_load_project FINISHED in {time.time() - start_time:.4f}s"
            )
            safe_notify(
                _("Project opened from history.")
                if success
                else _("New project directory opened.")
            )

        except Exception as e:
            logger.error(
                f"DEBUG: CRITICAL ERROR in handle_load_project: {e}", exc_info=True
            )
            safe_notify(
                _("Failed to load project: {error}").format(error=str(e)),
                type="negative",
            )
        finally:
            ScanState.is_loading_project = False

    async def handle_scan(path: str, force: bool = False):
        if not path:
            ui.notify(_("Please provide a path"), type="warning")
            return

        # Ensure we always use absolute resolved paths
        resolved_path = Path(path).expanduser().resolve()
        ScanState.current_path = str(resolved_path)
        logger.info(f"DEBUG: Starting handle_scan for {resolved_path}")

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
        try:
            ui.run_javascript("window.scrollTo(0, document.body.scrollHeight)")
        except Exception:
            pass

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
