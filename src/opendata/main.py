import argparse
import multiprocessing
import sys
import time
import webbrowser

from opendata.utils import get_app_version


def run_server_process(host: str, port: int):
    """
    Worker function that runs in a separate process.
    Loads heavy libraries only inside the child process.
    """
    try:
        from opendata.ui.app import start_ui

        start_ui(host=host, port=port)
    except Exception as e:
        print(f"[ERROR] Server process failed: {e}")
        sys.exit(1)


def main():
    """Main entry point. Handles arguments and launches either Headless or Anchor mode."""
    # Required for Windows and PyInstaller when using multiprocessing
    multiprocessing.freeze_support()
    try:
        # Use spawn to ensure a fresh environment for the child process
        # This is more robust for GUI and web frameworks
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

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
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without the Desktop Anchor window (terminal only)",
    )
    args = parser.parse_args()

    version = get_app_version()
    print(f"--- OpenData Tool v{version} ---")

    if args.headless:
        print(
            f"[INFO] Starting server in HEADLESS mode on http://{args.host}:{args.port}"
        )
        # Run directly in the main process
        from opendata.ui.app import start_ui

        if not args.no_browser:
            import threading

            def open_browser():
                time.sleep(1.5)
                webbrowser.open(f"http://{args.host}:{args.port}")

            threading.Thread(target=open_browser, daemon=True).start()

        start_ui(host=args.host, port=args.port)
        return

    # --- Anchor GUI Mode (Default) ---
    try:
        import tkinter as tk

        from opendata.anchor import AppAnchor
    except ImportError:
        print("[WARNING] Tkinter not found. Falling back to headless mode.")
        from opendata.ui.app import start_ui

        start_ui(host=args.host, port=args.port)
        return

    print(f"[INFO] Starting server process on http://{args.host}:{args.port}")

    # Create and start the server process
    server_process = multiprocessing.Process(
        target=run_server_process,
        args=(args.host, args.port),
        name="OpenDataServer",
    )
    server_process.start()

    # Launch the Anchor window
    root = tk.Tk()
    url = f"http://{args.host}:{args.port}"
    app = AppAnchor(root, server_process, url)

    # Automatically open browser from the parent process
    if not args.no_browser:
        root.after(1500, lambda: webbrowser.open(url))

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n[INFO] KeyboardInterrupt received, shutting down...")
        app.shutdown()


if __name__ == "__main__":
    main()
