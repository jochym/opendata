import threading
import sys
import webbrowser
import time
import argparse
from opendata.ui.app import start_ui


def create_icon_image():
    """Create a procedurally generated icon matching the app logo."""
    from PIL import Image, ImageDraw

    width = 64
    height = 64
    navy_blue = (15, 23, 42)  # slate-900 / navy
    white = (255, 255, 255)

    image = Image.new("RGB", (width, height), navy_blue)
    dc = ImageDraw.Draw(image)

    # Draw "O" (Outer circle)
    dc.ellipse([4, 4, 60, 60], outline=white, width=3)

    # Draw incomplete "D"
    # Vertical line of D
    dc.line([28, 16, 28, 48], fill=white, width=3)
    # Curve of D (arc)
    dc.arc([20, 16, 48, 48], start=-90, end=90, fill=white, width=3)

    # Draw stars (stars in logo are auto_awesome / sparkles)
    # Using small crosses as star approximations
    def draw_star(x, y, size):
        dc.line([x - size, y, x + size, y], fill=white, width=1)
        dc.line([x, y - size, x, y + size], fill=white, width=1)

    draw_star(38, 28, 4)
    draw_star(44, 36, 2)
    draw_star(34, 40, 3)

    return image


def main():
    """Main entry point with pystray tray icon and background NiceGUI server."""
    from opendata.utils import get_app_version

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
    version = get_app_version()

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
        if sys.platform == "linux":
            print("\n[HINT] On Linux, you may need to install GUI support libraries:")
            print("      sudo apt-get install python3-gi libayatana-appindicator3-1")
        print("\n[INFO] Falling back to Terminal mode.")
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

    def on_about(icon, item):
        import subprocess

        msg = f"OpenData Tool v{version}\nScientific Metadata & Packaging Assistant\n\nAccess Dashboard at: {url}"
        # Simple cross-platform "about" alert using notify-send/msg boxes if available
        # or just print to console for now as fallback
        print(f"\n--- ABOUT ---\n{msg}\n-------------")
        try:
            if sys.platform == "linux":
                subprocess.run(["notify-send", "About OpenData", msg])
            elif sys.platform == "win32":
                import ctypes

                ctypes.windll.user32.MessageBoxW(0, msg, "About OpenData", 0)
        except Exception:
            pass

    def on_exit(icon, item):
        print("[INFO] Shutting down...")
        icon.stop()

    # 3. Create and run the Tray Icon
    try:
        menu = pystray.Menu(
            pystray.MenuItem(f"OpenData v{version}", on_about, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start Dashboard", on_open_dashboard, default=True),
            pystray.MenuItem("About", on_about),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit OpenData", on_exit),
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
        if sys.platform == "linux":
            print("\n[HINT] On Linux, you may need to install GUI support libraries:")
            print("      sudo apt-get install python3-gi libayatana-appindicator3-1")
        print("\n[INFO] Falling back to Terminal mode (Server is still running).")
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
