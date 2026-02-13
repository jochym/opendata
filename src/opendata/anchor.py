import logging
import os
import signal
import sys
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from opendata.utils import get_app_version

logger = logging.getLogger("opendata.anchor")


class AppAnchor:
    """
    A lightweight Tkinter GUI that acts as the 'Anchor' for the application.
    It manages the lifecycle of the heavy NiceGUI server process.
    """

    def __init__(self, root, server_process, url):
        self.root = root
        self.server_process = server_process
        self.url = url

        # Configuration
        self.root.title("OpenData Tool")
        self.root.geometry("350x240")
        self.root.resizable(False, False)

        # Handle window close (X button or Alt+F4)
        self.root.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        # Styling
        style = ttk.Style()
        style.configure("Action.TButton", font=("Helvetica", 10, "bold"))

        # Layout
        frame = ttk.Frame(root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(
            header_frame, text="OpenData Tool", font=("Helvetica", 12, "bold")
        ).pack(side=tk.LEFT)

        version = get_app_version()
        ttk.Label(
            header_frame, text=f"v{version}", font=("Helvetica", 9), foreground="gray"
        ).pack(side=tk.RIGHT, pady=(3, 0))

        # About / Description
        about_text = (
            "Guided metadata preparation and packaging for the RODBUK repository."
        )
        ttk.Label(
            frame,
            text=about_text,
            font=("Helvetica", 9),
            wraplength=300,
            justify=tk.CENTER,
        ).pack(pady=(0, 10))

        # Status Indicator
        self.status_label = ttk.Label(
            frame, text="● Status: Active", foreground="green"
        )
        self.status_label.pack(pady=(0, 15))

        # Open Browser Button
        self.btn_open = ttk.Button(
            frame,
            text="Open Dashboard",
            style="Action.TButton",
            command=self.open_browser,
        )
        self.btn_open.pack(fill=tk.X, pady=5)

        # Kill Switch
        ttk.Button(frame, text="Stop & Exit", command=self.confirm_exit).pack(
            fill=tk.X, pady=5
        )

        # Auto-check if server died
        self.root.after(1000, self.check_server_health)

    def open_browser(self):
        """Open the application in the default web browser."""
        webbrowser.open(self.url)

    def check_server_health(self):
        """Check if the server process is still running."""
        if not self.server_process.is_alive():
            self.status_label.config(text="● Status: Stopped", foreground="red")
            messagebox.showerror(
                "Error",
                f"Server process died unexpectedly (Exit code: {self.server_process.exitcode}).",
            )
            self.root.destroy()
        else:
            # Check again in 1 second
            self.root.after(1000, self.check_server_health)

    def confirm_exit(self):
        """Confirm with the user before stopping the server."""
        if messagebox.askokcancel(
            "Confirm Exit", "Stop OpenData Tool server and exit?"
        ):
            self.shutdown()

    def shutdown(self):
        """Terminate the server process and close the anchor window."""
        self.status_label.config(text="Stopping...", foreground="orange")
        self.root.update()

        if self.server_process.is_alive():
            # Try graceful termination
            self.server_process.terminate()
            self.server_process.join(timeout=2)

            # Force kill if still alive
            if self.server_process.is_alive():
                try:
                    os.kill(self.server_process.pid, signal.SIGKILL)
                except OSError:
                    # Process might have just finished
                    pass

        self.root.destroy()
        sys.exit(0)
