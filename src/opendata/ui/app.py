from nicegui import ui
import webbrowser
from pathlib import Path
from opendata.utils import get_local_ip
from opendata.workspace import WorkspaceManager
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.ai.service import AIService


def start_ui():
    # 1. Initialize Backend
    wm = WorkspaceManager()
    settings = wm.get_settings()
    agent = ProjectAnalysisAgent(Path(settings.workspace_path))
    ai = AIService(Path(settings.workspace_path))

    # 2. Reactive State
    state = {
        "step": "setup" if not settings.ai_consent_granted else "analyze",
        "language": settings.language,
        "messages": [],
        "scanning": False,
        "metadata_draft": agent.current_metadata,
    }

    @ui.page("/")
    def index():
        ui.query("body").style("background-color: #f8f9fa;")

        # --- HEADER ---
        with ui.header().classes(
            "bg-slate-800 text-white p-4 justify-between items-center shadow-lg"
        ):
            with ui.row().classes("items-center gap-4"):
                ui.icon("database", size="md")
                ui.label("OpenData Agent").classes("text-h5 font-bold tracking-tight")

            with ui.row().classes("items-center gap-2"):
                # Mobile QR Toggle
                with ui.button(
                    icon="qr_code_2", on_click=lambda: qr_dialog.open()
                ).props("flat color=white"):
                    ui.tooltip("Open on Tablet/Mobile")

                ui.separator().props("vertical color=white")
                ui.button("EN", on_click=lambda: set_lang("en")).props(
                    "flat color=white text-xs"
                )
                ui.button("PL", on_click=lambda: set_lang("pl")).props(
                    "flat color=white text-xs"
                )

        # --- QR DIALOG ---
        with ui.dialog() as qr_dialog, ui.card().classes("p-6 items-center"):
            ui.label("Continue on Mobile").classes("text-h6 q-mb-md")
            url = f"http://{get_local_ip()}:8080"
            ui.interactive_image(
                f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url}"
            )
            ui.label(url).classes("text-caption text-slate-500 q-mt-md")
            ui.button("Close", on_click=qr_dialog.close).props("flat")

        # --- MAIN CONTENT ---
        container = ui.column().classes("w-full items-center q-pa-xl max-w-7xl mx-auto")

        with container:
            if state["step"] == "setup":
                render_setup_wizard()
            else:
                render_analysis_dashboard()

    def render_setup_wizard():
        with ui.card().classes(
            "w-full max-w-xl p-8 shadow-xl border-t-4 border-primary"
        ):
            ui.label("AI Configuration").classes("text-h4 q-mb-md font-bold")
            ui.markdown(
                "This tool uses **Google Gemini** to help extract metadata safely. No API keys needed—just sign in."
            )

            with ui.expansion("Security & Privacy FAQ", icon="security").classes(
                "bg-blue-50 q-mb-lg"
            ):
                ui.markdown("""
                - **Read-Only:** We never modify your research files.
                - **Local:** Analysis happens on your machine.
                - **Consent:** We only send text snippets to AI with your permission.
                """)

            ui.button(
                "Sign in with Google", icon="login", on_click=handle_auth
            ).classes("w-full py-4 bg-primary text-white font-bold rounded-lg")

    def render_analysis_dashboard():
        with ui.row().classes("w-full gap-6 no-wrap items-start"):
            # LEFT: Agent Chat (Iterative Loop)
            with ui.column().classes("flex-grow"):
                with ui.card().classes("w-full h-[600px] p-0 shadow-md flex flex-col"):
                    with ui.header().classes(
                        "bg-slate-100 text-slate-800 p-3 flex justify-between"
                    ):
                        ui.label("Agent Interaction").classes("font-bold")
                        if state["scanning"]:
                            ui.spinner(size="sm")

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
                                placeholder="Type your response..."
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
                    ui.label("RODBUK Metadata").classes(
                        "text-h6 font-bold q-mb-md text-green-800"
                    )

                    ui.label("Project Path").classes("text-xs text-slate-400 uppercase")
                    ui.label(
                        agent.current_fingerprint.root_path
                        if agent.current_fingerprint
                        else "Not selected"
                    ).classes("text-sm truncate q-mb-md")

                    with ui.scroll_area().classes("h-[400px]"):
                        render_metadata_fields()

                    ui.button("Build Package", icon="archive", color="green").classes(
                        "w-full q-mt-md font-bold"
                    )

    def render_metadata_fields():
        # Reactive display of the Pydantic model
        if not agent.current_metadata:
            ui.label("No metadata yet").classes("italic text-slate-400")
            return

        # Simple list of extracted fields
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
            state["step"] = "analyze"
            ui.navigate.to("/")
        else:
            ui.notify(
                "Authorization failed. Please ensure client_secrets.json is present.",
                type="negative",
            )

    def handle_user_msg(text):
        if not text:
            return
        agent.chat_history.append(("user", text))
        # Here we would trigger the Agent to generate a new AI response
        ui.notify("Agent is thinking...")
        ui.navigate.to("/")

    def set_lang(l):
        state["language"] = l
        settings.language = l
        wm.save_yaml(settings, "settings.yaml")
        ui.navigate.to("/")

    ui.run(title="OpenData Agent", port=8080, show=False, reload=False)


if __name__ == "__main__":
    start_ui()
