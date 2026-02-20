import asyncio
import logging
import re
import threading
from pathlib import Path
from typing import Any

from nicegui import ui

from opendata.i18n.translator import _
from opendata.ui.components.file_picker import LocalFilePicker
from opendata.ui.components.inventory_logic import load_inventory_background
from opendata.ui.components.metadata import metadata_preview_ui
from opendata.ui.context import AppContext
from opendata.ui.state import ScanState

logger = logging.getLogger("opendata.ui.chat")


@ui.refreshable
def chat_messages_ui(ctx: AppContext):
    with ui.column().classes("w-full gap-4 p-4"):
        if not ctx.agent.chat_history:
            with ui.column().classes(
                "w-full items-center justify-center p-8 opacity-50"
            ):
                ui.icon("chat_bubble_outline", size="lg")
                ui.label(_("No conversation history yet.")).classes("text-sm")
                ui.label(
                    _("Analyze the directory or ask a question to start.")
                ).classes("text-xs")

        for i, (role, text) in enumerate(ctx.agent.chat_history):
            if role == "user":
                with ui.row().classes("w-full justify-end"):
                    with ui.card().classes(
                        "bg-blue-500 text-white rounded-lg py-2 px-4 max-w-[80%] shadow-sm"
                    ):
                        ui.markdown(text).classes("text-sm")
            else:
                with ui.row().classes("w-full justify-start"):
                    with ui.card().classes(
                        "bg-white border border-slate-200 rounded-lg py-2 px-4 max-w-[90%] shadow-sm"
                    ):
                        ui.markdown(text).classes("text-sm text-slate-800")

                        # If this is the last message and there's an active analysis form, show it
                        if (
                            i == len(ctx.agent.chat_history) - 1
                            and ctx.agent.current_analysis
                        ):
                            render_analysis_form(ctx, ctx.agent.current_analysis)

        if ScanState.is_scanning or ScanState.is_processing_ai:
            with ui.row().classes("w-full justify-start"):
                with ui.card().classes(
                    "bg-gray-100 border border-gray-200 rounded-lg py-1 px-3 w-full shadow-none"
                ):
                    with ui.row().classes("items-center w-full justify-between gap-2"):
                        with ui.row().classes("items-center gap-2"):
                            is_stopping = (
                                (ScanState.stop_event and ScanState.stop_event.is_set())
                                if ScanState.is_scanning
                                else (
                                    ctx.session.ai_stop_event
                                    and ctx.session.ai_stop_event.is_set()
                                )
                            )

                            if is_stopping:
                                ui.icon("cancel", color="red", size="sm")
                                label_text = _("Canceled")
                            else:
                                ui.spinner(size="sm")
                                if ScanState.is_scanning:
                                    label_text = ScanState.progress or _(
                                        "Scanning project..."
                                    )
                                else:
                                    label_text = _("AI is thinking...")

                            ui.markdown(label_text).classes(
                                "text-sm text-gray-800 m-0 p-0 font-medium"
                            )
                            if ScanState.is_scanning and ScanState.short_path:
                                ui.label(ScanState.short_path).classes(
                                    "text-[10px] text-gray-500 truncate max-w-xs"
                                )

                        if not is_stopping:
                            if ScanState.is_scanning:
                                ui.button(
                                    "", on_click=lambda: handle_cancel_scan(ctx)
                                ).props(
                                    "icon=stop_circle flat color=red size=md"
                                ).classes("p-0")
                            elif ScanState.is_processing_ai:
                                ui.button(
                                    "", on_click=lambda: handle_cancel_ai(ctx)
                                ).props(
                                    "icon=stop_circle flat color=red size=md"
                                ).classes("p-0")
    try:
        ui.run_javascript("window.scrollTo(0, document.body.scrollHeight)")
    except RuntimeError:
        pass


def render_analysis_form(ctx: AppContext, analysis: Any):
    # Only show if there are actual questions or conflicts
    if not analysis.questions and not analysis.conflicting_data:
        return

    with ui.card().classes(
        "w-full mt-4 p-4 bg-white border border-slate-200 shadow-sm"
    ):
        ui.label(_("Refinement Form")).classes("text-sm font-bold text-slate-700 mb-2")

        form_data = {}

        # 1. Handle Conflicts
        if analysis.conflicting_data:
            ui.label(_("Resolve Conflicts")).classes(
                "text-xs font-bold text-orange-600 mt-2"
            )
            for conflict in analysis.conflicting_data:
                field = conflict.get("field", "unknown")
                sources = conflict.get("sources", [])
                options = {
                    str(
                        s.get("value", s) if isinstance(s, dict) else s
                    ): f"{str(s.get('value', s) if isinstance(s, dict) else s)} (Source: {s.get('source', 'unknown') if isinstance(s, dict) else 'unknown'})"
                    for s in sources
                }

                with ui.row().classes("w-full items-center gap-2"):
                    ui.label(field.replace("_", " ").title()).classes("text-xs w-24")
                    form_data[field] = (
                        ui.select(
                            options=options,
                            value=str(
                                sources[0].get("value", sources[0])
                                if isinstance(sources[0], dict)
                                else sources[0]
                            )
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
                with ui.column().classes("w-full gap-1 mt-2"):
                    ui.label(q.question).classes("text-xs text-slate-600")
                    if q.type == "choice" and q.options:
                        form_data[q.field] = (
                            ui.select(options=q.options, value=q.value)
                            .props("dense outlined")
                            .classes("w-full")
                        )
                    else:
                        form_data[q.field] = (
                            ui.input(value=q.value)
                            .props("dense outlined")
                            .classes("w-full")
                        )

        async def submit():
            answers = {k: v.value for k, v in form_data.items()}
            ctx.agent.submit_analysis_answers(answers, on_update=ctx.refresh_all)
            ui.notify(_("Metadata updated from form answers."))

        ui.button(_("Update Metadata"), on_click=submit).classes("w-full mt-4")


def render_analysis_dashboard(ctx: AppContext):
    def on_splitter_change(e):
        ctx.settings.splitter_value = e.value
        ctx.wm.save_yaml(ctx.settings, "settings.yaml")

    with ui.splitter(
        value=ctx.settings.splitter_value, on_change=on_splitter_change
    ).classes("w-full h-[calc(100vh-104px)] min-h-[600px] m-0 p-0") as splitter:
        with splitter.before:
            render_chat_panel(ctx)
        with splitter.after:
            render_metadata_panel(ctx)


def render_chat_panel(ctx: AppContext):
    with ui.column().classes("w-full h-full pr-2"):
        with ui.card().classes("w-full h-full p-0 shadow-md flex flex-col"):
            with ui.row().classes(
                "bg-slate-100 text-slate-800 p-2 w-full justify-between items-center shrink-0 border-b"
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.label(_("Agent Mode:")).classes("text-xs font-bold")
                    ui.toggle(
                        {"metadata": _("Metadata"), "curator": _("Curator")},
                    ).props("dense size=sm").bind_value(ScanState, "agent_mode")

                with ui.row().classes("gap-2"):
                    ui.button(
                        icon="delete_sweep",
                        on_click=lambda: handle_clear_chat(ctx),
                    ).props("flat dense color=red").classes("text-xs")
                    ui.tooltip(_("Clear Chat History"))
            with ui.scroll_area().classes("flex-grow w-full"):
                chat_messages_ui(ctx)
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
                        await handle_user_msg(ctx, user_input)

                user_input.on("keydown.enter", handle_ctrl_enter)
                ui.button(
                    icon="send",
                    on_click=lambda: handle_user_msg(ctx, user_input),
                ).props("round elevated color=primary")


async def handle_scan_only(ctx: AppContext, path: str):
    if not path:
        ui.notify(_("Please provide a path"), type="warning")
        return
    ScanState.current_path = path
    resolved_path = Path(path).expanduser()

    ScanState.stop_event = threading.Event()
    ScanState.is_scanning = True
    ScanState.progress = _("Scanning...")
    ctx.refresh("chat")

    def update_progress(msg, full_path="", short_path=""):
        ScanState.progress = msg
        ScanState.full_path = full_path
        ScanState.short_path = short_path
        ctx.refresh("chat")

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
            # Add scan statistics to chat history
            ctx.agent.chat_history.append(("agent", f"✅ **{result}**"))
            ui.notify(_("Inventory refreshed."), type="positive")
        # Persist the updated chat history so the scan result message survives reloads
        ctx.agent.save_state()

        # Refresh the UI inventory cache and stats
        await load_inventory_background(ctx)
    except asyncio.CancelledError:
        logger.info("Scan cancelled by user.")
        ctx.agent.chat_history.append(("agent", f"🛑 **{_('Scan cancelled.')}**"))
        ctx.agent.save_state()
    except Exception as e:
        ui.notify(f"Scan error: {e}", type="negative")
    finally:
        ScanState.is_scanning = False
        ScanState.stop_event = None
        ctx.refresh_all()


async def handle_heuristics(ctx: AppContext, path: str):
    if not path:
        ui.notify(_("Please provide a path"), type="warning")
        return
    resolved_path = Path(path).expanduser()

    ScanState.stop_event = threading.Event()
    ScanState.is_scanning = True
    ScanState.progress = _("Running heuristics...")
    ctx.refresh("chat")

    def update_progress(msg, full_path="", short_path=""):
        ScanState.progress = msg
        ScanState.full_path = full_path
        ScanState.short_path = short_path
        ctx.refresh("chat")

    try:
        await asyncio.to_thread(
            ctx.agent.run_heuristics_phase,
            resolved_path,
            ctx.ai,
            update_progress,
            stop_event=ScanState.stop_event,
        )
        ui.notify(_("Heuristics phase complete."), type="positive")
        # Refresh the UI inventory cache and stats as heuristics might change file identification
        from opendata.ui.components.inventory_logic import load_inventory_background

        await load_inventory_background(ctx)
    except asyncio.CancelledError:
        logger.info("Heuristics cancelled by user.")
    except Exception as e:
        ui.notify(f"Heuristics error: {e}", type="negative")
    finally:
        ScanState.is_scanning = False
        ScanState.stop_event = None
        ctx.refresh_all()


async def handle_ai_analysis(ctx: AppContext, path: str):
    if not path:
        ui.notify(_("Please provide a path"), type="warning")
        return

    ScanState.stop_event = threading.Event()
    ScanState.is_scanning = True
    ScanState.progress = _("AI analysis in progress...")
    ctx.refresh("metadata")

    try:
        await asyncio.to_thread(
            ctx.agent.run_ai_analysis_phase,
            ctx.ai,
            None,
            stop_event=ScanState.stop_event,
        )
        ui.notify(_("AI analysis phase complete."), type="positive")
        # Refresh the UI inventory cache and stats
        await load_inventory_background(ctx)
    except asyncio.CancelledError:
        logger.info("AI analysis cancelled by user.")
    except Exception as e:
        ui.notify(f"AI analysis error: {e}", type="negative")
    finally:
        ScanState.is_scanning = False
        ScanState.stop_event = None
        ctx.refresh_all()


def render_metadata_panel(ctx: AppContext):
    with ui.column().classes("w-full h-full pl-2"):
        with ui.card().classes(
            "w-full h-full p-3 shadow-md border-l-4 border-green-500 flex flex-col"
        ):
            with ui.row().classes("w-full justify-between items-center mb-1 shrink-0"):
                ui.label(_("RODBUK Metadata")).classes(
                    "text-h5 font-bold text-green-800"
                )
                ui.button(
                    icon="refresh", on_click=lambda: handle_clear_metadata(ctx)
                ).props("flat dense color=orange")
                ui.tooltip(_("Reset Metadata"))
            with ui.row().classes("w-full items-center gap-1 mb-2 shrink-0"):

                async def pick_dir():
                    picker = LocalFilePicker(
                        directory=ScanState.current_path or "~",
                        directory_only=True,
                    )
                    result = await picker
                    if result:
                        ScanState.current_path = result
                        path_input.value = result
                        # Auto-open project after selection
                        from opendata.ui.components.header import handle_load_project

                        await handle_load_project(ctx, result)

                path_input = (
                    ui.input(
                        label=_("Project Path"),
                        placeholder="/path/to/research",
                    )
                    .classes("flex-grow")
                    .props("dense")
                )
                # Manual binding to state only, without on_change triggers
                path_input.bind_value(ScanState, "current_path")

                ui.button(icon="folder", on_click=pick_dir).props("dense flat")

                from opendata.ui.components.header import handle_load_project

                ui.button(
                    _("Open"),
                    on_click=lambda: handle_load_project(ctx, path_input.value),
                ).props("dense outline").classes("shrink-0")

            with ui.row().classes("gap-1 mb-2 w-full shrink-0"):
                # Button 1: Scan
                ui.button(
                    _("Scan"),
                    icon="refresh",
                    on_click=lambda: handle_scan_only(ctx, path_input.value),
                ).classes("flex-grow").props("dense outline").bind_visibility_from(
                    ScanState, "is_scanning", backward=lambda x: not x
                )

                # Button 2: Select Files (replaces AI Heuristics)
                select_files_btn = (
                    ui.button(
                        _("Select Files"),
                        icon="folder_open",
                        on_click=lambda: open_file_selection_dialog(ctx),
                    )
                    .classes("flex-grow")
                    .props("dense outline")
                    .bind_visibility_from(
                        ScanState, "is_scanning", backward=lambda x: not x
                    )
                )
                # Enable only if scan is done
                select_files_btn.bind_enabled_from(
                    ctx.agent, "current_fingerprint", backward=lambda x: bool(x)
                )

                # Button 3: AI Analysis
                ai_btn = (
                    ui.button(
                        _("AI Analyze"),
                        icon="auto_awesome",
                        on_click=lambda: handle_ai_analysis(ctx, path_input.value),
                    )
                    .classes("flex-grow")
                    .props("dense elevated color=primary")
                    .bind_visibility_from(
                        ScanState, "is_scanning", backward=lambda x: not x
                    )
                )
                # Enable only if heuristics have been run
                ai_btn.bind_enabled_from(
                    ctx.agent, "heuristics_run", backward=lambda x: bool(x)
                )

                # Cancel Button
                ui.button(
                    _("Cancel"),
                    icon="stop",
                    on_click=lambda: handle_cancel_scan(ctx),
                    color="red",
                ).classes("w-full").props("dense").bind_visibility_from(
                    ScanState, "is_scanning"
                )
                ui.separator().classes("mt-1")

            with ui.scroll_area().classes("flex-grow w-full"):
                metadata_preview_ui(ctx)


async def handle_user_msg(ctx: AppContext, input_element):
    text = input_element.value
    if not text:
        return
    input_element.value = ""
    await handle_user_msg_from_code(ctx, text, mode=ScanState.agent_mode)


async def handle_user_msg_from_code(ctx: AppContext, text: str, mode: str = "metadata"):
    # 1. Immediate echo of user message
    ctx.agent.chat_history.append(("user", text))

    # 2. Add System Report if @files are detected
    at_matches = re.findall(r"@([^\s,]+)", text)
    if at_matches:
        file_list = ", ".join([f"`{m}`" for m in at_matches])
        ctx.agent.chat_history.append(
            (
                "agent",
                f"[System] context expanded with list of matching files: {file_list}",
            )
        )

    ScanState.is_processing_ai = True
    ctx.session.ai_stop_event = threading.Event()
    ctx.refresh("chat")

    try:
        await asyncio.to_thread(
            ctx.agent.process_user_input,
            text,
            ctx.ai,
            skip_user_append=True,
            on_update=ctx.refresh_all,
            mode=mode,
            stop_event=ctx.session.ai_stop_event,
        )
    except Exception as e:
        ui.notify(f"Error processing AI request: {e}", type="negative")
    finally:
        ScanState.is_processing_ai = False
        ctx.session.ai_stop_event = None
        ctx.refresh_all()

        try:
            ui.run_javascript("window.scrollTo(0, document.body.scrollHeight)")
        except RuntimeError:
            pass


async def handle_clear_chat(ctx: AppContext):
    ctx.agent.clear_chat_history()
    ctx.refresh("chat")
    ui.notify(_("Chat history cleared"))


async def handle_cancel_scan(ctx: AppContext):
    if ScanState.stop_event:
        ScanState.stop_event.set()
        ui.notify(_("Cancelling scan..."))
        # We don't set is_scanning = False here anymore to allow the UI
        # to show a "Stopping" state until the thread actually finishes.
        ctx.refresh_all()


async def handle_cancel_ai(ctx: AppContext):
    if ctx.session.ai_stop_event:
        ctx.session.ai_stop_event.set()
        ui.notify(_("Stopping AI..."))
        # We don't set is_processing_ai = False here anymore to allow the UI
        # to show a "Stopping" state until the thread actually finishes.
        ctx.refresh_all()


async def handle_clear_metadata(ctx: AppContext):
    from opendata.ui.components.metadata import handle_clear_metadata as hcm

    await hcm(ctx)


def open_file_selection_dialog(ctx: AppContext):
    """Opens a dialog for manual file selection with categories."""
    if not ctx.agent.current_fingerprint:
        ui.notify(_("Please scan the project first."), type="warning")
        return

    # Get all files from inventory (use session cache)
    inventory = (
        ctx.session.inventory_cache
        if hasattr(ctx, "session") and ctx.session.inventory_cache
        else []
    )

    # Category options
    CATEGORIES = {
        "main_article": _("Main Article/Paper"),
        "visualization_scripts": _("Visualization Scripts"),
        "data_files": _("Data Files"),
        "documentation": _("Documentation"),
        "other": _("Other"),
    }

    # Current selections (from existing analysis or empty)
    current_selections = {}
    if ctx.agent.current_analysis and ctx.agent.current_analysis.file_suggestions:
        for fs in ctx.agent.current_analysis.file_suggestions:
            # Infer category from reason
            reason_lower = fs.reason.lower()
            if (
                "main" in reason_lower
                or "article" in reason_lower
                or "paper" in reason_lower
            ):
                current_selections[fs.path] = "main_article"
            elif "visual" in reason_lower or "script" in reason_lower:
                current_selections[fs.path] = "visualization_scripts"
            elif "data" in reason_lower:
                current_selections[fs.path] = "data_files"
            elif "doc" in reason_lower:
                current_selections[fs.path] = "documentation"
            else:
                current_selections[fs.path] = "other"

    # Build dialog
    with ui.dialog() as dialog, ui.card().classes("w-[700px] h-[600px]"):
        ui.label(_("Select Significant Files")).classes("text-h6 mb-2")
        ui.markdown(
            _(
                "**Instructions:** Select files for deep analysis and assign categories. "
                "The AI will read these files to extract metadata."
            )
        ).classes("text-sm text-slate-600 mb-4")

        # File selection table
        selected_paths = {}

        # Initialize selected_paths with current selections (fix for pre-selected files)
        for path, category in current_selections.items():
            selected_paths[path] = category

        with ui.scroll_area().classes("h-96 w-full border rounded-md"):
            with ui.column().classes("gap-0"):
                # Header
                with ui.row().classes(
                    "w-full items-center gap-2 p-2 bg-slate-100 font-bold text-sm"
                ):
                    ui.label(_("File")).classes("flex-grow")
                    ui.label(_("Category")).classes("w-48")

                # Files
                for item in inventory:
                    path = item.get("path", "")
                    if not path or item.get("type") == "folder":
                        continue

                    with ui.row().classes(
                        "w-full items-center gap-2 p-1 hover:bg-slate-50"
                    ):
                        # Checkbox
                        is_selected = path in current_selections
                        initial_category = current_selections.get(path, "other")

                        # Category dropdown
                        cat_select = (
                            ui.select(
                                options=CATEGORIES,
                                value=initial_category,
                            )
                            .props("dense size=sm")
                            .classes("w-48")
                        )

                        # Checkbox with proper category handling
                        cb = ui.checkbox(
                            value=is_selected,
                            on_change=lambda e, p=path, cat_sel=cat_select: (
                                selected_paths.update({p: cat_sel.value})
                                if e.value
                                else selected_paths.pop(p, None)
                            ),
                        ).props("dense")

                        # File path
                        ui.label(path).classes("flex-grow text-sm font-mono truncate")

                        # Bind enabled state to checkbox
                        def update_cat_enabled(e, cat_sel=cat_select):
                            cat_sel.enabled = e.value

                        cb.on("update:model-value", update_cat_enabled)
                        cat_select.enabled = is_selected

                        # Update selected_paths when category changes
                        cat_select.on(
                            "update:model-value",
                            lambda e, p=path: selected_paths.update({p: e.value})
                            if p in selected_paths
                            else None,
                        )

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button(_("Cancel"), on_click=dialog.close).props("flat")

            async def apply_selection():
                # Convert to list of dicts
                selections = [
                    {"path": path, "category": cat}
                    for path, cat in selected_paths.items()
                ]

                # Call agent method
                msg = ctx.agent.set_significant_files_manual(selections)

                # Notify and close
                ui.notify(_("File selection saved."), type="positive")
                dialog.close()

                # Refresh UI
                ctx.refresh_all()

            ui.button(_("Apply"), on_click=apply_selection).props(
                "elevated color=primary"
            )

    dialog.open()
