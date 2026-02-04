from nicegui import ui
import webbrowser
from pathlib import Path
from typing import Any  # Added for type annotations
from opendata.utils import get_local_ip
from opendata.workspace import WorkspaceManager
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.ai.service import AIService
from opendata.i18n.translator import setup_i18n, _


def start_ui(host: str = "127.0.0.1", port: int = 8080):
    # 1. Initialize Backend
    wm = WorkspaceManager()
    settings = wm.get_settings()
    setup_i18n(settings.language)

    agent = ProjectAnalysisAgent(wm)
    ai = AIService(Path(settings.workspace_path))

    # Try Silent Auth
    ai.authenticate(silent=True)

    # --- REFRESHABLE COMPONENTS ---

    @ui.refreshable
    def chat_messages_ui():
        with ui.column().classes("w-full gap-4"):
            for role, msg in agent.chat_history:
                with ui.chat_message(
                    name=_("Agent") if role == "agent" else _("You"),
                    sent=role == "user",
                    avatar=None,
                ).classes("bg-slate-100" if role == "agent" else ""):
                    ui.markdown(msg)

            if ScanState.is_scanning:
                with ui.chat_message(
                    name=_("Agent"),
                    sent=False,
                    avatar=None,
                ).classes("bg-slate-100 animate-pulse"):
                    ui.markdown(_("Scanning project..."))
                    ui.button(_("Cancel Scan"), on_click=handle_cancel_scan).props(
                        "flat color=red icon=cancel"
                    ).classes("text-xs mt-2")

            # Smart scrolling
            ui.run_javascript("window.scrollTo(0, document.body.scrollHeight)")

    class ScanState:
        is_scanning = False
        progress = ""
        progress_label: Any = None  # Will hold a ui.label reference
        current_path = ""  # New state for path
        stop_event: Any = None  # Added for cancellation - will hold a threading.Event

    @ui.refreshable
    def metadata_preview_ui():
        if ScanState.is_scanning:
            with ui.column().classes("w-full items-center justify-center p-8"):
                ui.spinner(size="lg")
                # Create a temporary label first
                temp_label = ui.label(ScanState.progress).classes(
                    "text-xs text-slate-500 animate-pulse text-center w-full truncate"
                )
                # Assign it to ScanState.progress_label after creation
                ScanState.progress_label = temp_label  # type: ignore[attr-defined]
            return

        # Explicitly refresh header/selector when metadata changes
        project_selector_ui.refresh()

        fields = agent.current_metadata.model_dump(exclude_unset=True)

        # Use a column layout for metadata fields with labels above values
        with ui.column().classes("w-full gap-4"):
            for key, value in fields.items():
                if key == "authors":
                    # Special case for authors with richer display
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-xs font-bold text-slate-600 ml-2"
                    )
                    with ui.row().classes(
                        "w-full gap-1 flex-wrap items-center"
                    ):  # Allow wrapping for many authors, centered alignment for name-icon
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
                                identifier = item.get("identifier", "")  # ORCID

                                # Create a container for the author name with icons
                                with ui.label("").classes("") as author_container:
                                    # Display the name with small badge-like styling
                                    ui.label(name_clean).classes(
                                        "text-sm font-medium inline mr-1"
                                    )

                                    # Add small indicator icons inline with the name as superscripts
                                    # Put them in a span with reduced vertical spacing
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

                                    # Detailed tooltip on hover over the whole element
                                    with ui.tooltip().classes(
                                        "bg-slate-800 text-white p-2 text-xs whitespace-normal max-w-xs"
                                    ):
                                        ui.label(f"Name: {name_clean}")
                                        if affiliation:
                                            ui.label(f"Affiliation: {affiliation}")
                                        if identifier:
                                            ui.label(f"ORCID: {identifier}")

                                # Style the container to look like a subtle badge
                                author_container.classes(
                                    "py-0.5 px-1.5 rounded bg-slate-100 border border-slate-200 cursor-pointer hover:bg-slate-200 text-sm inline-block mr-1 mb-1"
                                )
                            else:
                                ui.label(str(item)).classes(
                                    "text-sm bg-slate-50 p-1 rounded border border-slate-100 break-words"
                                )
                else:
                    # Standard key-value pairs with label above full-width value
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-xs font-bold text-slate-600 ml-2"
                    )

                    if isinstance(value, list):
                        if key == "keywords":
                            # Special case for keywords to display them like small badges/tags
                            with ui.row().classes(
                                "w-full gap-1 flex-wrap items-center"
                            ):  # Allow wrapping for many keywords, centered alignment
                                for kw in value:
                                    ui.label(str(kw)).classes(
                                        "text-sm bg-slate-100 py-0.5 px-2 rounded border border-slate-200 inline-block mr-1 mb-1"
                                    )
                        else:
                            with ui.column().classes("w-full"):
                                for v_item in value:
                                    ui.label(str(v_item)).classes(
                                        "text-sm bg-slate-50 p-2 rounded border border-slate-100 w-full break-words"
                                    )
                    else:
                        ui.label(str(value)).classes(
                            "text-sm bg-slate-50 p-2 rounded border border-slate-100 w-full break-words"
                        )

    @ui.refreshable
    def project_selector_ui():
        if not settings.ai_consent_granted:
            return

        projects = wm.list_projects()
        if not projects:
            return

        project_options = {p["path"]: f"{p['title']} ({p['path']})" for p in projects}

        ui.select(
            options=project_options,
            label=_("Recent Projects"),
            on_change=lambda e: handle_load_project(e.value),
        ).props("dark dense options-dark behavior=menu").classes("w-64 text-xs")

    @ui.page("/")
    def index():
        setup_i18n(settings.language)
        ui.query("body").style("background-color: #f8f9fa;")

        # --- HEADER ---
        with ui.header().classes(
            "bg-slate-800 text-white p-4 justify-between items-center shadow-lg"
        ):
            with ui.row().classes("items-center gap-4"):
                ui.icon("auto_awesome", size="md")  # Spark icon in header too
                ui.label(_("OpenData Agent")).classes(
                    "text-h5 font-bold tracking-tight"
                )

                # PROJECT SELECTOR (In Top Bar)
                project_selector_ui()

            with ui.row().classes("items-center gap-2"):
                # MODEL SELECTOR
                if ai.is_authenticated():
                    models = ai.list_available_models()
                    ui.select(
                        options=models,
                        value=ai.model_name,
                        on_change=lambda e: ai.switch_model(e.value),
                    ).props("dark dense options-dark").classes("w-48 text-xs")

                with ui.button(
                    icon="qr_code_2", on_click=lambda: qr_dialog.open()
                ).props("flat color=white"):
                    ui.tooltip(_("Continue on Mobile"))
                ui.separator().props("vertical color=white")
                ui.button("EN", on_click=lambda: set_lang("en")).props(
                    "flat color=white text-xs"
                ).classes("bg-slate-700" if settings.language == "en" else "")
                ui.button("PL", on_click=lambda: set_lang("pl")).props(
                    "flat color=white text-xs"
                ).classes("bg-slate-700" if settings.language == "pl" else "")
                if settings.ai_consent_granted:
                    with ui.button(icon="logout", on_click=handle_logout).props(
                        "flat color=white"
                    ):
                        ui.tooltip(_("Logout from AI"))

        # --- QR DIALOG ---
        with ui.dialog() as qr_dialog, ui.card().classes("p-6 items-center"):
            ui.label(_("Continue on Mobile")).classes("text-h6 q-mb-md")
            url = f"http://{get_local_ip()}:{port}"
            ui.interactive_image(
                f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url}"
            )
            ui.label(url).classes("text-caption text-slate-500 q-mt-md")
            ui.button(_("Close"), on_click=qr_dialog.close).props("flat")

        # --- MAIN CONTENT ---
        container = ui.column().classes("w-full items-center q-pa-md max-w-7xl mx-auto")
        with container:
            if not settings.ai_consent_granted:
                render_setup_wizard()
            else:
                render_analysis_dashboard()

    # Shared reference for path input
    # path_input_ref = {"element": None}

    # def handle_project_selection(path: str):
    #     if path_input_ref["element"]:
    #         path_input_ref["element"].set_value(path)
    #     handle_scan(path)

    def render_setup_wizard():
        with ui.card().classes(
            "w-full max-w-xl p-8 shadow-xl border-t-4 border-primary"
        ):
            ui.label(_("AI Configuration")).classes("text-h4 q-mb-md font-bold")
            ui.markdown(
                _(
                    "This tool uses **Google Gemini** to help extract metadata safely. No API keys needed—just sign in."
                )
            )
            with ui.expansion(_("Security & Privacy FAQ"), icon="security").classes(
                "bg-blue-50 q-mb-lg"
            ):
                # Use a single markdown block with individual translations to fix spacing
                faq_items = [
                    _("Read-Only: We never modify your research files."),
                    _("Local: Analysis happens on your machine."),
                    _(
                        "Consent: We only send text snippets to AI with your permission."
                    ),
                ]
                ui.markdown("\n".join([f"- {item}" for item in faq_items]))
            ui.button(
                _("Sign in with Google"), icon="login", on_click=handle_auth
            ).classes("w-full py-4 bg-primary text-white font-bold rounded-lg")

    def render_analysis_dashboard():
        with ui.row().classes("w-full gap-6 no-wrap items-start"):
            # LEFT: Agent Chat
            with ui.column().classes("flex-grow"):
                with ui.card().classes("w-full h-[700px] p-0 shadow-md flex flex-col"):
                    with ui.row().classes(
                        "bg-slate-100 text-slate-800 p-3 w-full justify-between items-center"
                    ):
                        ui.label(_("Agent Interaction")).classes("font-bold")
                        with ui.row().classes("gap-2"):
                            ui.button(
                                icon="delete_sweep",
                                on_click=lambda: handle_clear_chat(),
                            ).props("flat dense color=red").classes("text-xs")
                            ui.tooltip(_("Clear Chat History"))

                    with ui.scroll_area().classes("flex-grow q-pa-md"):
                        chat_messages_ui()

                    with ui.row().classes(
                        "bg-white p-3 border-t w-full items-center no-wrap gap-2"
                    ):
                        user_input = ui.input(
                            placeholder=_("Type your response...")
                        ).classes("flex-grow")
                        user_input.on(
                            "keydown.enter", lambda: handle_user_msg(user_input)
                        )
                        ui.button(
                            icon="send", on_click=lambda: handle_user_msg(user_input)
                        ).props("round elevated color=primary")

            # RIGHT: Metadata Preview
            with ui.column().classes("w-96 shrink-0"):
                with ui.card().classes(
                    "w-full p-4 shadow-md border-l-4 border-green-500"
                ):
                    with ui.row().classes(
                        "w-full justify-between items-center q-mb-md"
                    ):
                        ui.label(_("RODBUK Metadata")).classes(
                            "text-h6 font-bold text-green-800"
                        )
                        ui.button(
                            icon="refresh",
                            on_click=lambda: handle_clear_metadata(),
                        ).props("flat dense color=orange")
                        ui.tooltip(_("Reset Metadata"))

                    with ui.column().classes("gap-2 q-mb-md w-full"):
                        path_input = (
                            ui.input(
                                label=_("Project Path"), placeholder="/path/to/research"
                            )
                            .classes("w-full")
                            .bind_value(ScanState, "current_path")
                        )
                        ui.button(
                            _("Analyze Directory"),
                            icon="search",
                            on_click=lambda: handle_scan(path_input.value, force=True),
                        ).classes("w-full")

                    with ui.scroll_area().classes("h-[450px] w-full"):
                        metadata_preview_ui()

                    ui.button(
                        _("Build Package"), icon="archive", color="green"
                    ).classes("w-full q-mt-md font-bold")

    async def handle_auth():
        if ai.authenticate(silent=False):
            settings.ai_consent_granted = True
            wm.save_yaml(settings, "settings.yaml")
            ui.navigate.to("/")
        else:
            ui.notify(
                _(
                    "Authorization failed. Please ensure client_secrets.json is present."
                ),
                type="negative",
            )

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
        # Refresh UI to show the new path in input box
        # We don't need a full refresh if it's bound, but we need to ensure the agent loads it

        import asyncio

        # We call start_analysis but with force_rescan=False (default)
        # which loads existing state in the agent.
        await asyncio.to_thread(agent.start_analysis, Path(path))

        chat_messages_ui.refresh()
        metadata_preview_ui.refresh()  # type: ignore

    async def handle_cancel_scan():
        if ScanState.stop_event:
            ScanState.stop_event.set()
            ui.notify(_("Cancelling scan..."))

    async def handle_scan(path: str, force: bool = False):
        if not path:
            ui.notify(_("Please provide a path"), type="warning")
            return

        # Update global state if not already set (e.g. manual typing)
        ScanState.current_path = path

        # Resolve ~ to home directory
        resolved_path = Path(path).expanduser()

        import threading

        ScanState.stop_event = threading.Event()  # type: ignore
        ScanState.is_scanning = True
        ScanState.progress = _("Initializing...")
        metadata_preview_ui.refresh()

        def update_progress(msg):
            ScanState.progress = msg
            if hasattr(ScanState, "progress_label") and ScanState.progress_label:
                ScanState.progress_label.text = msg

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

        # 1. Clear input and update UI immediately
        input_element.value = ""
        # Add to history here so it shows up while thinking
        agent.chat_history.append(("user", text))
        chat_messages_ui.refresh()

        # 2. Run AI in background to avoid freezing
        ui.notify(_("Agent is thinking..."), duration=2)
        import asyncio

        # Use to_thread for the blocking AI call
        await asyncio.to_thread(
            agent.process_user_input, text, ai, skip_user_append=True
        )

        chat_messages_ui.refresh()
        metadata_preview_ui.refresh()
        # Scroll to bottom again after agent response
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
