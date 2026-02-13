import asyncio
import contextlib
import re
import threading
from pathlib import Path
from typing import Any

from nicegui import ui

from opendata.i18n.translator import _
from opendata.ui.components.file_picker import LocalFilePicker
from opendata.ui.components.metadata import handle_clear_metadata, metadata_preview_ui
from opendata.ui.context import AppContext
from opendata.ui.state import ScanState, UIState


@ui.refreshable
def chat_messages_ui(ctx: AppContext):
    with ui.column().classes("w-full gap-1 overflow-x-hidden"):
        # Limit history display to last 30 messages to avoid WebSocket overload
        display_history = ctx.agent.chat_history[-30:]

        for i, (role, msg) in enumerate(display_history):
            # Skip technical messages from display
            if msg.startswith("READ_FILE:"):
                continue

            # Format System/Context messages nicely
            if msg.startswith("[System] context expanded with content of:"):
                files = msg.replace(
                    "[System] context expanded with content of:", ""
                ).strip()
                msg = f"📂 **Context Loaded:** Read content of {files}"

            elif msg.startswith("[System] AI requested content of:"):
                files = msg.replace("[System] AI requested content of:", "").strip()
                msg = f"🔍 **Analysis:** I need to read {files} to understand the data structure."

            elif "[System] READ_FILE Tool Results:" in msg:
                # Show only a placeholder for read files
                msg = _("✅ **File Content Loaded.** Continuing analysis...")

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
                        # Filter out internal JSON blocks from the visible message
                        # UNLESS it is an error report which needs to show the raw data
                        if "❌" in msg or "**Error" in msg:
                            display_msg = msg
                        else:
                            display_msg = re.sub(
                                r"METADATA:.*", "", msg, flags=re.DOTALL
                            ).strip()

                        if not display_msg and "METADATA:" in msg:
                            display_msg = _("✅ Metadata processed (see Preview tab)")

                        ui.markdown(display_msg).classes(
                            "text-sm text-gray-800 m-0 p-0 break-words"
                        )

                        # If this is the last agent message and we have an active analysis, show the form
                        if (
                            i == len(ctx.agent.chat_history) - 1
                            and ctx.agent.current_analysis
                        ):
                            render_analysis_form(ctx, ctx.agent.current_analysis)

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
                        ui.markdown(label_text).classes("text-sm text-gray-800 m-0 p-0")
                        ui.spinner(size="xs")
                        if ScanState.is_scanning:
                            ui.button(
                                "", on_click=lambda: handle_cancel_scan(ctx)
                            ).props("icon=close flat color=gray size=xs").classes(
                                "min-h-6 min-w-6 p-0.5"
                            )
                        elif ScanState.is_processing_ai:
                            ui.button("", on_click=lambda: handle_cancel_ai(ctx)).props(
                                "icon=stop_circle flat color=red size=xs"
                            ).classes("min-h-6 min-w-6 p-0.5")
    with contextlib.suppress(RuntimeError):
        ui.run_javascript("window.scrollTo(0, document.body.scrollHeight)")


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
                        s.get("value", "")
                    ): f"{str(s.get('value', ''))} (Source: {s.get('source', 'unknown')})"
                    for s in sources
                }

                with ui.row().classes("w-full items-center gap-2"):
                    ui.label(field.replace("_", " ").title()).classes("text-xs w-24")
                    form_data[field] = (
                        ui.select(
                            options=options,
                            value=str(sources[0].get("value", "")) if sources else None,
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
            final_answers = {
                field: component.value for field, component in form_data.items()
            }
            ctx.agent.submit_analysis_answers(final_answers, on_update=ctx.refresh_all)
            ui.notify(_("Metadata updated from form."), type="positive")

        ui.button(_("Update Metadata"), on_click=submit_form).props(
            "elevated color=primary icon=check"
        ).classes("w-full mt-4")


def render_analysis_dashboard(ctx: AppContext):
    def on_splitter_change(e):
        ctx.settings.splitter_value = e.value
        ctx.wm.save_yaml(ctx.settings, "settings.yaml")

    with ui.splitter(
        value=ctx.settings.splitter_value, on_change=on_splitter_change
    ).classes("w-full h-[calc(100vh-104px)] min-h-[600px] m-0 p-0") as splitter:
        with splitter.before:
            with ui.column().classes("w-full h-full pr-2"):
                with ui.card().classes("w-full h-full p-0 shadow-md flex flex-col"):
                    with ui.row().classes(
                        "bg-slate-100 text-slate-800 p-2 w-full justify-between items-center shrink-0 border-b"
                    ):
                        with ui.row().classes("items-center gap-2"):
                            ui.label(_("Agent Mode:")).classes("text-xs font-bold")
                            ui.toggle(
                                {"metadata": _("Metadata"), "curator": _("Curator")},
                                value=ScanState.agent_mode,
                                on_change=lambda e: setattr(
                                    ScanState, "agent_mode", e.value
                                ),
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

        with splitter.after, ui.column().classes("w-full h-full pl-2"):
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

                with ui.column().classes("gap-1 mb-2 w-full shrink-0"):
                    ui.button(
                        _("Analyze Directory"),
                        icon="search",
                        on_click=lambda: handle_scan(
                            ctx, path_input.value, force=True
                        ),
                    ).classes("w-full").props("dense").bind_visibility_from(
                        ScanState, "is_scanning", backward=lambda x: not x
                    )
                    ui.button(
                        _("Cancel Scan"),
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
    at_matches = re.findall(r"@([^\\s,]+)", text)
    if at_matches:
        file_list = ", ".join([f"`{m}`" for m in at_matches])
        ctx.agent.chat_history.append(
            (
                "agent",
                f"[System] context expanded with list of matching files: {file_list}",
            )
        )

    ScanState.is_processing_ai = True
    UIState.ai_stop_event = threading.Event()
    ctx.refresh("chat")

    try:
        await asyncio.to_thread(
            ctx.agent.process_user_input,
            text,
            ctx.ai,
            skip_user_append=True,
            on_update=ctx.refresh_all,
            mode=mode,
            stop_event=UIState.ai_stop_event,
        )
    except Exception as e:
        ui.notify(f"Error processing AI request: {e}", type="negative")
    finally:
        ScanState.is_processing_ai = False
        UIState.ai_stop_event = None
        ctx.refresh_all()
        with contextlib.suppress(RuntimeError):
            ui.run_javascript("window.scrollTo(0, document.body.scrollHeight)")


async def handle_clear_chat(ctx: AppContext):
    ctx.agent.clear_chat_history()
    ctx.refresh("chat")
    ui.notify(_("Chat history cleared"))


async def handle_cancel_scan(ctx: AppContext):
    if ScanState.stop_event:
        ScanState.stop_event.set()
        ui.notify(_("Cancelling scan..."))


async def handle_cancel_ai(ctx: AppContext):
    if UIState.ai_stop_event:
        UIState.ai_stop_event.set()
        ui.notify(_("Stopping AI..."))


async def handle_scan(ctx: AppContext, path: str, force: bool = False):
    if not path:
        ui.notify(_("Please provide a path"), type="warning")
        return
    ScanState.current_path = path
    resolved_path = Path(path).expanduser()

    ScanState.stop_event = threading.Event()
    ScanState.is_scanning = True
    ScanState.progress = _("Initializing...")
    ctx.refresh("metadata")

    import time

    last_refresh = 0

    def update_progress(msg, full_path="", short_path=""):
        nonlocal last_refresh
        ScanState.progress = msg
        ScanState.full_path = full_path
        ScanState.short_path = short_path

        now = time.time()
        if now - last_refresh > 0.5:
            ctx.refresh("metadata")
            ctx.refresh("chat")
            last_refresh = now

    await asyncio.to_thread(
        ctx.agent.start_analysis,
        resolved_path,
        update_progress,
        force_rescan=force,
        stop_event=ScanState.stop_event,
    )
    ScanState.is_scanning = False
    ScanState.stop_event = None
    ctx.refresh_all()
