import logging
import os
import string
from pathlib import Path
from typing import Optional, List, Dict, Any
from nicegui import ui
from opendata.i18n.translator import _

logger = logging.getLogger("opendata.ui.file_picker")


def get_drives():
    """Returns a list of available drive letters on Windows."""
    if os.name != "nt":
        return []
    import ctypes

    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    drives = []
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(f"{letter}:\\")
        bitmask >>= 1
    return drives


class LocalFilePicker(ui.dialog):
    def __init__(
        self,
        directory: str = "~",
        show_hidden_files: bool = False,
        directory_only: bool = True,
    ) -> None:
        """
        Server-side directory picker for NiceGUI.
        """
        super().__init__()
        self.show_hidden_files = show_hidden_files
        self.directory_only = directory_only

        # Safe path initialization
        try:
            p = Path(directory).expanduser()
            if p.exists() and p.is_dir():
                self.path = p.resolve()
            else:
                self.path = Path.home().resolve()
        except Exception:
            self.path = Path.home().resolve()

        with (
            self,
            ui.card().classes("w-[500px] h-[600px] flex flex-col p-0 overflow-hidden"),
        ):
            # Header
            with ui.row().classes(
                "w-full items-center justify-between bg-slate-800 text-white p-3 shrink-0"
            ):
                with ui.row().classes("items-center gap-2 overflow-hidden"):
                    ui.icon("folder_open")
                    self.path_label = ui.label(str(self.path)).classes(
                        "text-xs font-mono truncate"
                    )
                ui.button(icon="close", on_click=self.close).props(
                    "flat dense color=white"
                )

            # Directory List
            with ui.scroll_area().classes("flex-grow w-full bg-white"):
                self.list_container = ui.column().classes("w-full gap-0")

            # Footer
            with ui.row().classes(
                "w-full justify-end p-3 gap-2 shrink-0 border-t bg-slate-50"
            ):
                ui.button(_("Cancel"), on_click=self.close).props("flat")
                self.submit_button = ui.button(
                    _("Select Current"), on_click=lambda: self.submit(str(self.path))
                ).props("elevated color=primary")

            self._update_list()

    def _update_list(self):
        try:
            self.list_container.clear()

            # Handle Windows "This PC" view
            if self.path is None:
                self.path_label.text = _("This PC")
                self.submit_button.disable()
                with self.list_container:
                    for d in get_drives():

                        def make_click_handler(drive_letter):
                            return lambda _: self._handle_click(
                                {"path": Path(drive_letter), "type": "dir"}
                            )

                        with ui.item(on_click=make_click_handler(d)).classes(
                            "w-full hover:bg-blue-50 cursor-pointer"
                        ):
                            with ui.item_section().props("side"):
                                ui.icon("storage", color="primary")
                            with ui.item_section():
                                ui.item_label(d)
                return

            self.path_label.text = str(self.path)
            self.submit_button.enable()

            rows = []
            # Up navigation
            if self.path.parent != self.path:
                rows.append({"name": "..", "type": "dir", "path": self.path.parent})
            elif os.name == "nt":
                # Already at root on Windows - offer "This PC" view
                rows.append({"name": "..", "type": "dir", "path": None})

            # List directory content
            if self.path.exists() and self.path.is_dir():
                for item in self.path.iterdir():
                    try:
                        if not self.show_hidden_files and item.name.startswith("."):
                            continue
                        if self.directory_only and not item.is_dir():
                            continue

                        rows.append(
                            {
                                "name": item.name,
                                "type": "dir" if item.is_dir() else "file",
                                "path": item,  # Store as Path object
                            }
                        )
                    except (PermissionError, OSError):
                        continue

            # Sort: .. first, then dirs, then files
            sorted_rows = sorted(
                rows,
                key=lambda r: (
                    r["name"] != "..",
                    r["type"] != "dir",
                    r["name"].lower(),
                ),
            )

            with self.list_container:
                if not sorted_rows:
                    ui.label(_("Directory is empty")).classes(
                        "p-4 text-slate-400 italic"
                    )
                else:
                    for row in sorted_rows:
                        icon = "folder" if row["type"] == "dir" else "insert_drive_file"
                        color = "orange" if row["type"] == "dir" else "slate"

                        def make_row_click_handler(r):
                            return lambda _: self._handle_click(r)

                        with ui.item(on_click=make_row_click_handler(row)).classes(
                            "w-full hover:bg-blue-50 cursor-pointer"
                        ):
                            with ui.item_section().props("side"):
                                ui.icon(icon, color=color)
                            with ui.item_section():
                                ui.item_label(row["name"])
        except Exception as e:
            logger.error(f"Error listing {self.path}: {e}")
            with self.list_container:
                ui.label(_("Error reading directory")).classes("p-4 text-red-500")

    def _handle_click(self, row):
        # row["path"] can be None (Drives view) or Path object
        new_path = row["path"]

        if new_path is None:
            self.path = None
            self._update_list()
            return

        if new_path.is_dir():
            self.path = new_path.resolve()
            self._update_list()
        else:
            self.submit(str(new_path))
