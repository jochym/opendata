import asyncio
import logging
import re
import threading
from pathlib import Path
from typing import Any, Optional

from nicegui import ui

from opendata.i18n.translator import _
from opendata.ui.components.file_picker import LocalFilePicker
from opendata.ui.components.files_dialog import render_file_selection_summary
from opendata.ui.components.inventory_logic import (
    load_inventory_background,
)
from opendata.ui.components.metadata import metadata_preview_ui
from opendata.ui.context import AppContext
from opendata.ui.state import ScanState

logger = logging.getLogger("opendata.ui.chat")


@ui.refreshable
def chat_messages_ui(ctx: AppContext):
    # Ensure code blocks and pre tags wrap correctly within the chat
    ui.add_css("""
        .chat-bubble pre {
            white-space: pre-wrap !important;
            word-break: break-all !important;
        }
        .chat-bubble code {
            white-space: pre-wrap !important;
            word-break: break-all !important;
        }
    """)
    with ui.column().classes("w-full gap-4 p-4"):
        # Show welcome message until explicitly dismissed by user
        if not ctx.session.welcome_dismissed:
            with ui.card().classes(
                "w-full relative p-6 bg-blue-50 rounded-lg border border-blue-100 shadow-sm"
            ):
                # Dismiss button (top-right corner)
                with ui.row().classes("absolute top-2 right-2"):
                    ui.button(
                        icon="close",
                        on_click=lambda: dismiss_welcome(ctx),
                    ).props("flat dense round color=blue-300 size=sm").classes(
                        "hover:bg-blue-100"
                    )

                with ui.column().classes("w-full items-center justify-center gap-3"):
                    ui.icon("auto_awesome", size="lg", color="blue-500")
                    ui.label(_("Welcome to OpenData Agent!")).classes(
                        "text-lg font-bold text-blue-800"
                    )
                    ui.markdown(
                        _(
                            "I will help you prepare metadata for your research project.\n\n"
                            "**To get started:**\n"
                            "1. **Select project directory** and click **Open**.\n"
                            "2. Click **Scan** to index your files.\n"
                            "3. **Select significant files** in the **Significant Files** section below to provide context for the AI.\n"
                            "4. You can adjust file exclusions in the **Protocols** tab at any time.\n"
                            "5. Click **AI Analyze** to generate draft metadata."
                        )
                    ).classes("text-sm text-blue-900 text-center")

        for i, (role, text) in enumerate(ctx.agent.chat_history):
            if role == "user":
                with ui.row().classes("w-full justify-end"):
                    with ui.card().classes(
                        "bg-blue-500 text-white rounded-lg py-2 px-4 max-w-[85%] shadow-sm overflow-hidden chat-bubble"
                    ):
                        ui.markdown(text).classes(
                            "text-sm break-words whitespace-pre-wrap"
                        )
            else:
                with ui.row().classes("w-full justify-start"):
                    with ui.card().classes(
                        "bg-white border border-slate-200 rounded-lg py-2 px-4 max-w-[95%] shadow-sm overflow-hidden chat-bubble"
                    ):
                        ui.markdown(text).classes(
                            "text-sm text-slate-800 break-words whitespace-pre-wrap"
                        )

                        # If this is the last message and there's an active analysis form, show it
                        if (
                            i == len(ctx.agent.chat_history) - 1
                            and ctx.agent.current_analysis
                        ):
                            render_analysis_form(ctx, ctx.agent.current_analysis)

    if ctx.chat_scroll_area:
        # Only scroll if chat history has grown
        if len(ctx.agent.chat_history) > ctx.session.last_chat_len:
            try:
                ctx.chat_scroll_area.scroll_to(percent=1.0)
            except RuntimeError:
                pass
        # Always update last_chat_len to current state
        ctx.session.last_chat_len = len(ctx.agent.chat_history)


def render_status_dialog(ctx: AppContext):
    """Renders a modal dialog for scanning and AI processing progress.
    Purely reactive implementation using bindings to avoid flickering and 'client deleted' errors.
    """
    with ui.dialog().props("persistent") as dialog:
        # Visibility bound to scanning OR processing AI
        dialog.bind_value_from(
            ScanState, "is_scanning", backward=lambda x: x or ScanState.is_processing_ai
        )
        dialog.bind_value_from(
            ScanState, "is_processing_ai", backward=lambda x: x or ScanState.is_scanning
        )

        with ui.card().classes("w-96 p-6 items-center gap-4"):
            # Status Indicator (Spinner or Cancel Icon)
            # We use two elements and bind their visibility to the STOP event state
            with ui.column().classes("items-center w-full"):
                ui.spinner(size="lg").bind_visibility_from(
                    ScanState,
                    "stop_event",
                    backward=lambda ev: ev is None or not ev.is_set(),
                ).bind_visibility_from(
                    ctx.session,
                    "ai_stop_event",
                    backward=lambda ev: ev is None or not ev.is_set(),
                )

                ui.icon("cancel", color="red", size="lg").bind_visibility_from(
                    ScanState,
                    "stop_event",
                    backward=lambda ev: ev is not None and ev.is_set(),
                ).bind_visibility_from(
                    ctx.session,
                    "ai_stop_event",
                    backward=lambda ev: ev is not None and ev.is_set(),
                )

                ui.label(_("Processing...")).classes(
                    "text-lg font-bold"
                ).bind_text_from(
                    ScanState,
                    "stop_event",
                    backward=lambda ev: _("Cancelling...")
                    if ev is not None and ev.is_set()
                    else _("Processing..."),
                )

            # Progress content
            ui.markdown("").classes(
                "text-sm text-center text-gray-700 w-full"
            ).bind_content_from(
                ScanState,
                "progress",
                backward=lambda x: x
                if ScanState.is_scanning
                else _("AI is thinking..."),
            )

            # Current file path (Scan only)
            ui.label("").classes(
                "text-[10px] text-gray-500 text-center break-all w-full"
            ).bind_text_from(ScanState, "short_path").bind_visibility_from(
                ScanState, "is_scanning"
            )

            # Action buttons
            with ui.row().classes("w-full justify-center mt-2"):
                stop_btn = ui.button(
                    _("Stop"),
                    on_click=lambda: handle_cancel_scan(ctx)
                    if ScanState.is_scanning
                    else handle_cancel_ai(ctx),
                    color="red",
                ).props("outline")

                # Hide stop button if already cancelling
                stop_btn.bind_visibility_from(
                    ScanState,
                    "stop_event",
                    backward=lambda ev: ev is None or not ev.is_set(),
                ).bind_visibility_from(
                    ctx.session,
                    "ai_stop_event",
                    backward=lambda ev: ev is None or not ev.is_set(),
                )


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
            with ui.scroll_area().classes("flex-grow w-full") as ctx.chat_scroll_area:
                chat_messages_ui(ctx)

            # Modal status dialog - created once per session/client
            render_status_dialog(ctx)

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

    ScanState.is_scanning = True
    ScanState.stop_event = threading.Event()
    ScanState.progress = _("Scanning...")
    # Reactive bindings handle the dialog opening

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

        # Add scan statistics to chat history
        if ScanState.stop_event and ScanState.stop_event.is_set():
            ctx.agent.chat_history.append(("agent", f"🛑 **{result}**"))
        else:
            # Simplified scan message
            ctx.agent.chat_history.append(("agent", f"✅ **{result}**"))
            try:
                ui.notify(_("Inventory refreshed."), type="positive")
            except Exception:
                pass

        # Refresh the UI inventory cache and stats
        await load_inventory_background(ctx)

        # Force a global UI refresh
        ctx.refresh_all()

        # Persist the updated chat history
        ctx.agent.save_state()

    except asyncio.CancelledError:
        logger.info("Scan cancelled by user.")
        ctx.agent.chat_history.append(("agent", f"🛑 **{_('Scan cancelled.')}**"))
        ctx.agent.save_state()
    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        try:
            ui.notify(f"Scan error: {e}", type="negative")
        except Exception:
            pass
    finally:
        ScanState.is_scanning = False
        ScanState.stop_event = None
        # Reactive bindings handle the dialog closing
        ctx.refresh("chat")
        try:
            ctx.refresh_all()
        except Exception:
            pass


async def handle_ai_analysis(ctx: AppContext, path: str):
    if not ctx.agent.project_id:
        ui.notify(_("Please open a project first."), type="warning")
        return

    ScanState.is_processing_ai = True
    ctx.session.ai_stop_event = threading.Event()
    # Reactive bindings handle the dialog opening

    try:
        await asyncio.to_thread(
            ctx.agent.run_ai_analysis_phase,
            ctx.ai,
            None,  # progress_callback
            ctx.session.ai_stop_event,
        )
        ui.notify(_("AI analysis phase complete."), type="positive")
        await load_inventory_background(ctx)
    except asyncio.CancelledError:
        logger.info("AI analysis cancelled by user.")
    except Exception as e:
        logger.error(f"AI analysis failed: {e}", exc_info=True)
        ui.notify(f"AI analysis error: {e}", type="negative")
    finally:
        ScanState.is_processing_ai = False
        ctx.session.ai_stop_event = None
        # Reactive bindings handle the dialog closing
        ctx.refresh("chat")
        ctx.refresh_all()


def render_metadata_panel(ctx: AppContext):
    with ui.column().classes("w-full h-full pl-2 m-0 overflow-hidden"):
        with (
            ui.card()
            .classes(
                "w-full h-full p-2 shadow-md border-l-4 border-green-500 m-0 flex flex-col items-stretch"
            )
            .style(
                "display: flex !important; justify-content: flex-start !important; gap: 0 !important"
            )
        ):
            with ui.row().classes("w-full justify-between items-center mb-1 shrink-0"):
                ui.label(_("RODBUK Metadata")).classes(
                    "text-h5 font-bold text-green-800"
                )
                ui.button(
                    icon="refresh", on_click=lambda: handle_clear_metadata(ctx)
                ).props("flat dense color=orange")
                ui.tooltip(_("Reset Metadata"))
            with ui.row().classes("w-full items-center gap-1 mb-1 shrink-0"):

                async def pick_dir():
                    picker = LocalFilePicker(
                        directory=ScanState.current_path or "~",
                        directory_only=True,
                    )
                    result = await picker
                    if result:
                        ScanState.current_path = result
                        path_input.value = result
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
                path_input.bind_value(ScanState, "current_path")

                ui.button(icon="folder", on_click=pick_dir).props("dense flat")

                from opendata.ui.components.header import handle_load_project

                ui.button(
                    _("Open"),
                    on_click=lambda: handle_load_project(ctx, path_input.value),
                ).props("dense outline").classes("shrink-0")

            with ui.row().classes("gap-1 mb-1 w-full shrink-0"):
                ui.button(
                    _("Scan"),
                    icon="refresh",
                    on_click=lambda: handle_scan_only(ctx, path_input.value),
                ).classes("flex-grow").props("dense outline")

                ai_btn = (
                    ui.button(
                        _("AI Analyze"),
                        icon="auto_awesome",
                        on_click=lambda: handle_ai_analysis(ctx, path_input.value),
                    )
                    .classes("flex-grow")
                    .props("dense elevated color=primary")
                )
                ai_btn.bind_enabled_from(
                    ctx.agent, "heuristics_run", backward=lambda x: bool(x)
                )

            # File Selection Summary (opens dialog for editing)
            with ui.column().classes("w-full shrink-0"):
                ctx.register_refreshable(
                    "file_selection_summary", render_file_selection_summary
                )
                render_file_selection_summary(ctx)

            ui.separator().classes("my-1")

            with ui.scroll_area().classes("flex-grow w-full"):
                metadata_preview_ui(ctx)


async def handle_user_msg(ctx: AppContext, input_element):
    text = input_element.value
    if not text:
        return
    input_element.value = ""
    await handle_user_msg_from_code(ctx, text, mode=ScanState.agent_mode)


async def handle_user_msg_from_code(ctx: AppContext, text: str, mode: str = "metadata"):
    ctx.agent.chat_history.append(("user", text))

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
    # Reactive bindings handle the dialog opening

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
        # If the /bug command generated a pending bug report, open the dialog
        bug_report = getattr(ctx.agent, "_pending_bug_report", None)
        if isinstance(bug_report, dict):
            ctx.agent._pending_bug_report = None
            from opendata.ui.components.bug_report_dialog import show_bug_report_dialog

            show_bug_report_dialog(ctx, bug_report)
    except asyncio.CancelledError:
        logger.info("AI interaction cancelled by user.")
        ctx.agent.chat_history.append(
            ("agent", f"🛑 **{_('AI interaction cancelled.')}**")
        )
        ctx.agent.save_state()
    except Exception as e:
        logger.error(f"AI processing failed: {e}", exc_info=True)
        ui.notify(f"Error processing AI request: {e}", type="negative")
    finally:
        ScanState.is_processing_ai = False
        ctx.session.ai_stop_event = None
        # Reactive bindings handle the dialog closing
        ctx.refresh("chat")
        ctx.refresh_all()


async def handle_clear_chat(ctx: AppContext):
    ctx.agent.clear_chat_history()
    ctx.refresh("chat")
    ui.notify(_("Chat history cleared"))


async def dismiss_welcome(ctx: AppContext):
    """Dismiss the welcome message until next project load."""
    ctx.session.welcome_dismissed = True
    ctx.refresh("chat")


async def handle_cancel_scan(ctx: AppContext):
    if ScanState.stop_event:
        ScanState.stop_event.set()
        ui.notify(_("Cancelling scan..."))
        ctx.refresh_all()


async def handle_cancel_ai(ctx: AppContext):
    if ctx.session.ai_stop_event:
        ctx.session.ai_stop_event.set()
        ui.notify(_("Stopping AI..."))
        ctx.refresh_all()


async def handle_clear_metadata(ctx: AppContext):
    from opendata.ui.components.metadata import handle_clear_metadata as hcm

    await hcm(ctx)
