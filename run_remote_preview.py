from opendata.ui.app import start_ui
from nicegui import ui

if __name__ in {"__main__", "__mp_main__"}:
    print("Starting OpenData LIVE TEST on http://0.0.0.0:8080")
    # Force host to 0.0.0.0 for VPN access
    start_ui(host="0.0.0.0")
