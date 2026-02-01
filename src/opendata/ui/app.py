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
    
    # Initialize i18n
    setup_i18n(settings.language)
    
    agent = ProjectAnalysisAgent(Path(settings.workspace_path))
    ai = AIService(Path(settings.workspace_path))

    @ui.page("/")
    def index():
        # Important: Sync translator with current user settings on page load
        setup_i18n(settings.language)
        
        ui.query("body").style("background-color: #f8f9fa;")

        # --- HEADER ---
        with ui.header().classes(
            "bg-slate-800 text-white p-4 justify-between items-center shadow-lg"
        ):
            with ui.row().classes("items-center gap-4"):
                ui.icon("database", size="md")
                ui.label(_("OpenData Agent")).classes("text-h5 font-bold tracking-tight")

            with ui.row().classes("items-center gap-2"):
                # Mobile QR Toggle
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
        container = ui.column().classes("w-full items-center q-pa-xl max-w-7xl mx-auto")

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
            ui.markdown(_("This tool uses **Google Gemini** to help extract metadata safely. No API keys needed—just sign in."))

            with ui.expansion(_("Security & Privacy FAQ"), icon="security").classes(
                "bg-blue-50 q-mb-lg"
            ):
                # Use a single markdown block with individual translations to fix spacing
                faq_items = [
                    _("Read-Only: We never modify your research files."),
                    _("Local: Analysis happens on your machine."),
                    _("Consent: We only send text snippets to AI with your permission.")
                ]
                ui.markdown("\n".join([f"- {item}" for item in faq_items]))

            ui.button(
                _("Sign in with Google"), icon="login", on_click=handle_auth
            ).classes("w-full py-4 bg-primary text-white font-bold rounded-lg")

    def render_analysis_dashboard():
        with ui.row().classes("w-full gap-6 no-wrap items-start"):
            # LEFT: Agent Chat (Iterative Loop)
            with ui.column().classes("flex-grow"):
                with ui.card().classes("w-full h-[600px] p-0 shadow-md flex flex-col"):
                    with ui.header().classes(
                        "bg-slate-100 text-slate-800 p-3 flex justify-between"
                    ):
                        ui.label(_("Agent Interaction")).classes("font-bold")
                    
                    # Chat Messages Area
                    message_container = ui.column().classes(
                        "flex-grow overflow-y-auto q-pa-md gap-4"
                    )
                    with message_container:
                        for role, msg in agent.chat_history:
                            with ui.chat_message(
                                name="Agent" if role == "agent" else "You",
                                sent=role == "user",
                                avatar="https://robohash.org/opendata"
                                if role == "agent"
                                else None,
                            ):
                                ui.markdown(msg)

                    # Input Row
                    with ui.footer().classes("bg-white p-3 border-t"):
                        with ui.row().classes("w-full items-center no-wrap gap-2"):
                            user_input = ui.input(
                                placeholder=_("Type your response...")
                            ).classes("flex-grow")
                            ui.button(
                                icon="send",
                                on_click=lambda: handle_user_msg(user_input.value),
                            ).props("round elevated color=primary")

            # RIGHT: Metadata Preview (The Live Result)
            with ui.column().classes("w-80 shrink-0"):
                with ui.card().classes(
                    "w-full p-4 shadow-md border-l-4 border-green-500"
                ):
                    ui.label(_("RODBUK Metadata")).classes(
                        "text-h6 font-bold q-mb-md text-green-800"
                    )

                    ui.label(_("Project Path")).classes("text-xs text-slate-400 uppercase")
                    
                    with ui.column().classes('gap-2 q-mb-md'):
                        path_input = ui.input(label=_('Project Path'), placeholder='/path/to/research')
                        ui.button(_('Analyze Directory'), icon='search', 
                                  on_click=lambda: handle_scan(path_input.value)).classes('w-full')

                    with ui.scroll_area().classes("h-[400px]"):
                        render_metadata_fields()

                    ui.button(_("Build Package"), icon="archive", color="green").classes(
                        "w-full q-mt-md font-bold"
                    )

    def render_metadata_fields():
        if not agent.current_metadata:
            ui.label(_("No metadata yet")).classes("italic text-slate-400")
            return

        fields = agent.current_metadata.model_dump(exclude_unset=True)
        for key, value in fields.items():
            with ui.column().classes("q-mb-sm"):
                ui.label(key.replace("_", " ").title()).classes(
                    "text-xs font-bold text-slate-600"
                )
                ui.label(str(value)).classes(
                    "text-sm bg-slate-50 p-1 rounded border border-slate-100"
                )

    async def handle_auth():
        if ai.authenticate():
            settings.ai_consent_granted = True
            wm.save_yaml(settings, "settings.yaml")
            ui.navigate.to("/")
        else:
            ui.notify(
                _("Authorization failed. Please ensure client_secrets.json is present."),
                type="negative",
            )

    async def handle_scan(path: str):
        if not path:
            ui.notify(_('Please provide a path'), type='warning')
            return
        ui.notify(_('Scanning {path}...').format(path=path))
        agent.start_analysis(Path(path))
        ui.navigate.to('/')

    async def handle_user_msg(text):
        if not text:
            return
        ui.notify(_("Agent is thinking..."))
        agent.process_user_input(text, ai)
        ui.navigate.to("/")

    def set_lang(l):
        settings.language = l
        wm.save_yaml(settings, "settings.yaml")
        setup_i18n(l)
        ui.navigate.to("/")

    ui.run(title="OpenData Agent", port=port, show=False, reload=False, host=host)


if __name__ == "__main__":
    start_ui()
