from nicegui import ui
import webbrowser
from pathlib import Path
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

            # Smart scrolling: if last message is agent, scroll to top of it if possible
            # But simple scrollTo bottom is usually best for "user answer on bottom"
            ui.run_javascript("window.scrollTo(0, document.body.scrollHeight)")

    class ScanState:
        is_scanning = False
        progress = ""
        progress_label: ui.label = None

    @ui.refreshable
    def metadata_preview_ui():
        if ScanState.is_scanning:
            with ui.column().classes("w-full items-center justify-center p-8"):
                ui.spinner(size="lg")
                ScanState.progress_label = (
                    ui.label(ScanState.progress)
                    .classes(
                        "text-xs text-slate-500 animate-pulse text-center w-full truncate"
                    )
                    .style("direction: rtl; text-align: left;")
                )
            return

        fields = agent.current_metadata.model_dump(exclude_unset=True)
        for key, value in fields.items():
            with ui.column().classes("w-full q-mb-sm"):
                ui.label(key.replace("_", " ").title()).classes(
                    "text-xs font-bold text-slate-600"
                )
                if isinstance(value, list):
                    for item in value:
                        # CLEAN AUTHOR DISPLAY WITH ORCID ICON
                        if isinstance(item, dict):
                            name = item.get(
                                "name", item.get("person_to_contact", str(item))
                            )
                            # Aggressively remove LaTeX leftovers
                            name = (
                                name.replace("{", "")
                                .replace("}", "")
                                .replace("\\", "")
                                .replace("orcidlink", "")
                            )
                            orcid = item.get("identifier")

                            with ui.row().classes("items-center gap-1"):
                                ui.label(name).classes(
                                    "text-sm bg-slate-50 p-2 rounded border border-slate-100"
                                )
                                if orcid:
                                    # Typeset ORCID nicely with a small logo and tooltip
                                    with ui.element("div").classes("cursor-pointer"):
                                        # Use standard ORCID green icon
                                        ui.icon("verified", size="16px", color="green")
                                        ui.tooltip(f"ORCID iD: {orcid}").classes(
                                            "bg-slate-800 text-white p-2 text-xs"
                                        )
                        else:
                            ui.label(str(item)).classes(
                                "text-sm bg-slate-50 p-2 rounded border border-slate-100 w-full"
                            )
                else:
                    ui.label(str(value)).classes(
                        "text-sm bg-slate-50 p-2 rounded border border-slate-100 w-full"
                    )

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
                if settings.ai_consent_granted:
                    projects = wm.list_projects()
                    if projects:
                        project_options = {
                            p["path"]: f"{p['title']} ({p['path']})" for p in projects
                        }
                        ui.select(
                            options=project_options,
                            label=_("Recent Projects"),
                            on_change=lambda e: handle_scan(e.value),
                        ).props("dark dense options-dark behavior=menu").classes(
                            "w-64 text-xs"
                        )

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
                        path_input = ui.input(
                            label=_("Project Path"), placeholder="/path/to/research"
                        ).classes("w-full")
                        ui.button(
                            _("Analyze Directory"),
                            icon="search",
                            on_click=lambda: handle_scan(path_input.value),
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

    async def handle_scan(path: str):
        if not path:
            ui.notify(_("Please provide a path"), type="warning")
            return

        # Resolve ~ to home directory
        resolved_path = Path(path).expanduser()

        ScanState.is_scanning = True
        ScanState.progress = _("Initializing...")
        metadata_preview_ui.refresh()

        def update_progress(msg):
            ScanState.progress = msg
            if hasattr(ScanState, "progress_label") and ScanState.progress_label:
                ScanState.progress_label.text = msg

        import asyncio

        await asyncio.to_thread(agent.start_analysis, resolved_path, update_progress)

        ScanState.is_scanning = False
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
