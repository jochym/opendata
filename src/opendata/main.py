import threading
import sys
import webbrowser
import time
import argparse
from opendata.ui.app import start_ui


def create_icon_image():
    """Create a simple procedurally generated icon."""
    from PIL import Image, ImageDraw

    # Generate a 64x64 image with a blue background and "OD" text
    width = 64
    height = 64
    color1 = (30, 41, 59)  # slate-800
    color2 = (255, 255, 255)  # white

    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)

    # Draw a simple "OD" logo approximation
    dc.rectangle([10, 10, 54, 54], outline=color2, width=2)
    dc.text((18, 18), "OD", fill=color2)

    return image


def main():
    """Main entry point with pystray tray icon and background NiceGUI server."""
    parser = argparse.ArgumentParser(description="OpenData Tool")
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Start the server without the system tray icon (Terminal/Headless mode)",
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
    url = f"http://localhost:{port}" if host == "0.0.0.0" else f"http://{host}:{port}"

    if args.no_gui:
        print(f"[INFO] Starting server in Terminal/Headless mode on {url}")
        print("[INFO] Press Ctrl+C to stop.")
        # In no-gui mode, we run in the main thread
        start_ui(host=host, port=port)
        return

    # For GUI mode, we need pystray
    try:
        import pystray
    except Exception as e:
        print(f"[ERROR] Could not initialize GUI backend: {e}")
        print("[INFO] Falling back to Terminal mode.")
        start_ui(host=host, port=port)
        return

    # 1. Start the server in a background DAEMON thread
    server_thread = threading.Thread(
        target=start_ui, kwargs={"host": host, "port": port}, daemon=True
    )
    server_thread.start()

    print(f"[INFO] Server starting in background on {url}")

    # 2. Define Tray Icon actions
    def on_open_dashboard(icon, item):
        webbrowser.open(url)

    def on_exit(icon, item):
        print("[INFO] Shutting down...")
        icon.stop()

    # 3. Create and run the Tray Icon
    try:
        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard", on_open_dashboard, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", on_exit),
        )

        icon = pystray.Icon("opendata", create_icon_image(), "OpenData Tool", menu)

        # Setup function to auto-open browser on start
        def setup(icon):
            icon.visible = True
            # Give the server a moment to start before opening browser
            time.sleep(1.5)
            webbrowser.open(url)

        print("[INFO] Starting system tray icon...")
        icon.run(setup=setup)
    except Exception as e:
        print(f"\n[ERROR] System tray icon failed to start: {e}")
        print("[INFO] Falling back to Terminal mode (Server is still running).")
        print(f"[INFO] Access the dashboard at: {url}")
        print("[INFO] Press Ctrl+C to stop.")
        # Keep the main thread alive since the server is in a daemon thread
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[INFO] Shutting down...")
            sys.exit(0)


if __name__ == "__main__":
    main()
