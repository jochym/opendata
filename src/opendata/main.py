import threading
import sys
import webbrowser
import time
import os
import argparse
from opendata.ui.app import start_ui

def main():
    """Main entry point with stable Thread-based server startup."""
    parser = argparse.ArgumentParser(description="OpenData Tool")
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Start the server without the desktop control window",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind the server to (default: 8080)",
    )
    args = parser.parse_args()

    port = args.port
    host = args.host

    if args.no_gui:
        print(f"[INFO] Starting server in no-GUI mode on http://{host}:{port}")
        start_ui(host=host, port=port)
        return

    # 1. Start the server in a background THREAD
    server_thread = threading.Thread(
        target=start_ui, kwargs={"host": host, "port": port}, daemon=True
    )
    server_thread.start()

    print(f"[INFO] Server starting on http://{host}:{port}")

    # Give the server time to bind
    time.sleep(2)

    try:
        import webview

        status_html = f"""
            <body style="font-family: sans-serif; text-align: center; padding: 15px; background-color: #f9f9f9;">
                <h2 style="margin-bottom: 10px;">OpenData Control</h2>
                <div style="display: flex; justify-content: space-around; margin-bottom: 15px;">
                    <div><div style="width: 15px; height: 15px; background-color: #4CAF50; border-radius: 50%; margin: 0 auto;"></div><small>Server</small></div>
                    <div><div style="width: 15px; height: 15px; background-color: #4CAF50; border-radius: 50%; margin: 0 auto;"></div><small>AI</small></div>
                    <div><div style="width: 15px; height: 15px; background-color: #4CAF50; border-radius: 50%; margin: 0 auto;"></div><small>Space</small></div>
                </div>
                <div style="margin-bottom: 15px;">
                    <button onclick="pywebview.api.open_browser()" style="padding: 10px 20px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
                        Open Dashboard
                    </button>
                </div>
                <footer style="font-size: 0.75em; color: #666; line-height: 1.4;">
                    Dashboard: <code style="background:#eee; padding:2px 4px;">http://{host}:{port}</code><br>
                    Closing this window shuts down the tool.
                </footer>
            </body>
        """

        class API:
            def open_browser(self):
                url = f"http://localhost:{port}" if host == "0.0.0.0" else f"http://{host}:{port}"
                webbrowser.open(url)

        window = webview.create_window(
            "OpenData Tool",
            html=status_html,
            js_api=API(),
            width=350,
            height=250,
            resizable=False,
            on_top=True,
        )
        webview.start()

    except Exception as e:
        print(f"\n[ERROR] GUI launch failed ({e}). Fallback to terminal mode.")
        while True:
            time.sleep(1)

if __name__ == "__main__":
    main()
