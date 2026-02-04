from nicegui import ui
import webbrowser
from pathlib import Path
from typing import Any
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
    ai = AIService(Path(settings.workspace_path), settings)

    # Initialize model from global settings
    if settings.ai_provider == "google" and settings.google_model:
        ai.switch_model(settings.google_model)
    elif settings.ai_provider == "openai" and settings.openai_model:
        ai.switch_model(settings.openai_model)

    # Try Silent Auth
    ai.authenticate(silent=True)

    # --- REFRESHABLE COMPONENTS ---

    @ui.refreshable
    def header_content_ui():
        qr_dialog = ScanState.qr_dialog
        with ui.row().classes("items-center gap-4"):
            ui.icon("auto_awesome", size="md")
            ui.label(_("OpenData Agent")).classes("text-h5 font-bold tracking-tight")
            project_selector_ui()

        with ui.row().classes("items-center gap-2"):
            # MODEL SELECTOR
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
                ).props("dark dense options-dark behavior=menu").classes("w-48 text-xs")

            with ui.button(
                icon="qr_code_2",
                on_click=lambda: qr_dialog.open() if qr_dialog else None,
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
        progress_label: Any = None
        current_path = ""
        stop_event: Any = None
        qr_dialog: Any = None  # Store reference globally within start_ui scope

    @ui.refreshable
    def metadata_preview_ui():
        if ScanState.is_scanning:
            with ui.column().classes("w-full items-center justify-center p-8"):
                ui.spinner(size="lg")
                temp_label = ui.label(ScanState.progress).classes(
                    "text-xs text-slate-500 animate-pulse text-center w-full truncate"
                )
                ScanState.progress_label = temp_label  # type: ignore[attr-defined]
            return

        project_selector_ui.refresh()  # type: ignore
        fields = agent.current_metadata.model_dump(exclude_unset=True)

        def create_expandable_text(text: str):
            with ui.column().classes(
                "w-full gap-0 bg-slate-50 border border-slate-100 rounded"
            ):
                # Increased height to 110px to ensure 5 lines are fully visible without chopping descenders.
                content = ui.markdown(text).classes(
                    "px-2 py-0 text-sm text-gray-800 break-words overflow-hidden transition-all duration-300"
                )
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

        with ui.column().classes("w-full gap-4"):
            for key, value in fields.items():
                if key == "authors":
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
                                with ui.label("").classes(
                                    "py-0.5 px-1.5 rounded bg-slate-100 border border-slate-200 cursor-pointer hover:bg-slate-200 text-sm inline-block mr-1 mb-1"
                                ) as author_container:
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
                                    with ui.tooltip().classes(
                                        "bg-slate-800 text-white p-2 text-xs whitespace-normal max-w-xs"
                                    ):
                                        ui.label(f"Name: {name_clean}")
                                        if affiliation:
                                            ui.label(f"Affiliation: {affiliation}")
                                        if identifier:
                                            ui.label(f"ORCID: {identifier}")
                            else:
                                ui.label(str(item)).classes(
                                    "text-sm bg-slate-50 p-1 rounded border border-slate-100 break-words"
                                )
                elif key == "keywords":
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-xs font-bold text-slate-600 ml-2"
                    )
                    with ui.row().classes("w-full gap-1 flex-wrap items-center"):
                        for kw in value:
                            ui.label(str(kw)).classes(
                                "text-sm bg-slate-100 py-0.5 px-2 rounded border border-slate-200 inline-block mr-1 mb-1"
                            )
                else:
                    ui.label(key.replace("_", " ").title()).classes(
                        "text-xs font-bold text-slate-600 ml-2"
                    )
                    if isinstance(value, list):
                        with ui.column().classes("w-full gap-1"):
                            for v_item in value:
                                create_expandable_text(str(v_item))
                    else:
                        create_expandable_text(str(value))

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
        with ui.row().classes(
            "w-full gap-6 no-wrap items-start h-[calc(100vh-100px)] min-h-[600px]"
        ):
            with ui.column().classes("flex-grow h-full"):
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
                            if e.modifier.ctrl:
                                await handle_user_msg(user_input)

                        user_input.on("keydown.enter", handle_ctrl_enter)
                        ui.button(
                            icon="send", on_click=lambda: handle_user_msg(user_input)
                        ).props("round elevated color=primary")

            with ui.column().classes("w-96 shrink-0 h-full"):
                with ui.card().classes(
                    "w-full h-full p-4 shadow-md border-l-4 border-green-500 flex flex-col"
                ):
                    with ui.row().classes(
                        "w-full justify-between items-center q-mb-md shrink-0"
                    ):
                        ui.label(_("RODBUK Metadata")).classes(
                            "text-h6 font-bold text-green-800"
                        )
                        ui.button(icon="refresh", on_click=handle_clear_metadata).props(
                            "flat dense color=orange"
                        )
                        ui.tooltip(_("Reset Metadata"))
                    with ui.column().classes("gap-2 q-mb-md w-full shrink-0"):
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
                    with ui.scroll_area().classes("flex-grow w-full"):
                        metadata_preview_ui()
                    ui.button(
                        _("Build Package"), icon="archive", color="green"
                    ).classes("w-full q-mt-md font-bold shrink-0")

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
        input_element.value = ""
        agent.chat_history.append(("user", text))
        chat_messages_ui.refresh()
        ui.notify(_("Agent is thinking..."), duration=2)
        import asyncio

        await asyncio.to_thread(
            agent.process_user_input, text, ai, skip_user_append=True
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
