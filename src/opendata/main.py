import webview
from opendata.ui.app import start_ui
import multiprocessing
import sys
import webbrowser


def main():
    """Main entry point with a Desktop Control Window anchor and status lights."""

    # 1. Start the NiceGUI server in a background process
    server_process = multiprocessing.Process(target=start_ui)
    server_process.daemon = True
    server_process.start()

    # 2. Status Light Logic (Simplified Placeholder)
    status_html = """
        <body style="font-family: sans-serif; text-align: center; padding: 15px; background-color: #f9f9f9;">
            <h2 style="margin-bottom: 20px;">OpenData Control</h2>
            
            <div style="display: flex; justify-content: space-around; margin-bottom: 20px;">
                <div>
                    <div style="width: 15px; height: 15px; background-color: #4CAF50; border-radius: 50%; margin: 0 auto;"></div>
                    <small>Server</small>
                </div>
                <div>
                    <div style="width: 15px; height: 15px; background-color: #4CAF50; border-radius: 50%; margin: 0 auto;"></div>
                    <small>AI Service</small>
                </div>
                <div>
                    <div style="width: 15px; height: 15px; background-color: #FFC107; border-radius: 50%; margin: 0 auto;"></div>
                    <small>Workspace</small>
                </div>
            </div>

            <button onclick="pywebview.api.open_browser()" style="padding: 10px 20px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
                Open Dashboard
            </button>

            <footer style="position: absolute; bottom: 10px; left: 0; width: 100%; font-size: 0.7em; color: gray;">
                Closing this window shuts down the tool.
            </footer>

            <script>
                // We'll add real-time status updates here later
            </script>
        </body>
    """

    class API:
        def open_browser(self):
            webbrowser.open("http://localhost:8080")

    # 3. Launch Desktop Anchor
    try:
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
    finally:
        server_process.terminate()
        sys.exit()


if __name__ == "__main__":
    main()
