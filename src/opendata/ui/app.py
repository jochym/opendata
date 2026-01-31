from nicegui import ui
import webbrowser
from opendata.utils import get_local_ip


def start_ui():
    state = {
        "step": 1,
        "language": "en",
        "remote_access": False,
        "local_ip": get_local_ip(),
    }

    content = {
        "en": {
            "title": "OpenData Tool",
            "mobile_btn": "Enable Mobile Access",
            "mobile_desc": "For security, remote access is disabled by default. Enable it to see the QR code.",
            "welcome": "Welcome to OpenData",
        },
        "pl": {
            "title": "Narzędzie OpenData",
            "mobile_btn": "Włącz dostęp mobilny",
            "mobile_desc": "Ze względów bezpieczeństwa dostęp zdalny jest domyślnie wyłączony. Włącz go, aby zobaczyć kod QR.",
            "welcome": "Witaj w OpenData",
        },
    }

    @ui.page("/")
    def index():
        ui.query("body").style("background-color: #f0f2f5;")

        with ui.header().classes("bg-primary text-white p-4 justify-between"):
            ui.label(content[state["language"]].get("title", "OpenData")).classes(
                "text-h5 font-bold"
            )
            with ui.row().classes("items-center"):
                # SECURE MOBILE ACCESS BUTTON
                with ui.button(
                    icon="smartphone", on_click=lambda: qr_dialog.open()
                ).props("flat color=white"):
                    ui.tooltip(content[state["language"]].get("mobile_btn", "Mobile"))

                ui.button("EN", on_click=lambda: set_lang("en")).props(
                    "flat color=white"
                )
                ui.button("PL", on_click=lambda: set_lang("pl")).props(
                    "flat color=white"
                )

        # SECURE QR CODE DIALOG
        with ui.dialog() as qr_dialog, ui.card().classes("items-center p-8"):
            ui.label(content[state["language"]].get("mobile_btn")).classes("text-h5")
            ui.label(content[state["language"]].get("mobile_desc")).classes(
                "text-grey-7 text-center q-mb-md"
            )

            if not state["remote_access"]:
                ui.button(
                    "Enable Remote Access",
                    color="red",
                    on_click=lambda: [
                        state.update({"remote_access": True}),
                        ui.notify(
                            "Remote access enabled. Restart server to apply bind change."
                        ),
                    ],
                ).classes("q-ma-md")
            else:
                url = f"http://{state['local_ip']}:8080"
                ui.interactive_image(
                    f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url}"
                )
                ui.label(url).classes("text-mono q-mt-md")

            ui.button("Close", on_click=qr_dialog.close).props("flat")

        def set_lang(l):
            state["language"] = l
            ui.navigate.to("/")

        # Wizard content
        with ui.column().classes("w-full items-center q-pa-xl"):
            with ui.card().classes("w-full max-w-lg p-8 shadow-2xl"):
                ui.markdown(
                    f"## {content[state['language']].get('welcome', 'Welcome')}"
                )

    # DEFAULT BINDING: localhost (Security first)
    ui.run(title="OpenData Tool", port=8080, show=False, reload=False, host="127.0.0.1")


if __name__ == "__main__":
    start_ui()
