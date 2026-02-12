import sys
import webbrowser
import argparse
from opendata.ui.app import start_ui
from opendata.utils import get_app_version


def main():
    """Main entry point. Runs the NiceGUI server and opens the browser."""
    parser = argparse.ArgumentParser(description="OpenData Tool")
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind the server to (default: 8080)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically",
    )
    args = parser.parse_args()

    port = args.port
    host = args.host
    url = f"http://localhost:{port}" if host == "0.0.0.0" else f"http://{host}:{port}"
    version = get_app_version()

    print(f"--- OpenData Tool v{version} ---")
    print(f"[INFO] Starting server on {url}")
    print("[INFO] Press Ctrl+C to stop.")

    if not args.no_browser:
        # Open browser in a slight delay to ensure server is ready
        import threading
        import time

        def open_browser():
            time.sleep(1.5)
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    start_ui(host=host, port=port)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
