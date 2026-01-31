from nicegui import ui
import socket


# Minimal helper for the preview
def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# The Mockup Page
@ui.page("/")
def index():
    ui.query("body").style("background-color: #f0f2f5; font-family: sans-serif;")

    with ui.header().classes("bg-primary text-white p-4 justify-between"):
        ui.label("OpenData Tool Mockup").classes("text-h5 font-bold")
        with ui.row():
            ui.button("EN", on_click=lambda: ui.notify("English")).props(
                "flat color=white"
            )
            ui.button("PL", on_click=lambda: ui.notify("Polski")).props(
                "flat color=white"
            )

    with ui.column().classes("w-full items-center q-pa-xl"):
        with ui.card().classes("w-full max-w-lg p-8 shadow-2xl"):
            ui.markdown("## Welcome to OpenData")
            ui.label("This is a functional mockup for your remote preview.")
            ui.separator().classes("q-my-md")

            with ui.row().classes("items-center"):
                ui.icon("check_circle", color="green").classes("text-h4")
                ui.label("Server: Online").classes("text-lg")

            with ui.row().classes("items-center q-mt-sm"):
                ui.icon("account_circle", color="blue").classes("text-h4")
                ui.label("AI: Ready (Google Account)").classes("text-lg")

            ui.button(
                "Start Project Analysis",
                icon="play_arrow",
                on_click=lambda: ui.notify("Scan initiated (Mock)"),
            ).classes("w-full q-mt-lg")


# REQUIRED FOR REMOTE PREVIEW
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8080, host="0.0.0.0", show=False, reload=False)
