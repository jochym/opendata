import sys
from pathlib import Path

file_path = Path("src/opendata/ui/components/chat.py")
content = file_path.read_text(encoding="utf-8")

old_code = """    # Current selections (from existing analysis or empty)
    current_selections = {}
    if ctx.agent.current_analysis and ctx.agent.current_analysis.file_suggestions:
        for fs in ctx.agent.current_analysis.file_suggestions:
            # Infer category from reason
            reason_lower = fs.reason.lower()
            if (
                "main" in reason_lower
                or "article" in reason_lower
                or "paper" in reason_lower
            ):
                current_selections[fs.path] = "main_article"
            elif "visual" in reason_lower or "script" in reason_lower:
                current_selections[fs.path] = "visualization_scripts"
            elif "data" in reason_lower:
                current_selections[fs.path] = "data_files"
            elif "doc" in reason_lower:
                current_selections[fs.path] = "documentation"
            else:
                current_selections[fs.path] = "other"

    # Build dialog
    with ui.dialog() as dialog, ui.card().classes("w-[700px] h-[600px]"):
        ui.label(_("Select Significant Files")).classes("text-h6 mb-2")
        ui.markdown(
            _(
                "**Instructions:** Select files for deep analysis and assign categories. "
                "The AI will read these files to extract metadata."
            )
        ).classes("text-sm text-slate-600 mb-4")

        # File selection table
        selected_paths = {}

        with ui.scroll_area().classes("h-96 w-full border rounded-md"):
            with ui.column().classes("gap-0"):
                # Header
                with ui.row().classes(
                    "w-full items-center gap-2 p-2 bg-slate-100 font-bold text-sm"
                ):
                    ui.label(_("File")).classes("flex-grow")
                    ui.label(_("Category")).classes("w-48")

                # Files
                for item in inventory:
                    path = item.get("path", "")
                    if not path or item.get("type") == "folder":
                        continue

                    with ui.row().classes(
                        "w-full items-center gap-2 p-1 hover:bg-slate-50"
                    ):
                        # Checkbox
                        is_selected = path in current_selections
                        cb = ui.checkbox(
                            value=is_selected,
                            on_change=lambda e, p=path: (
                                selected_paths.update({p: "other"})
                                if e.value
                                else selected_paths.pop(p, None)
                            ),
                        ).props("dense")"""

new_code = """    # Current selections (from existing analysis or empty)
    current_selections = {}
    if ctx.agent.current_analysis and ctx.agent.current_analysis.file_suggestions:
        for fs in ctx.agent.current_analysis.file_suggestions:
            # Infer category from reason
            reason_lower = fs.reason.lower()
            if (
                "main" in reason_lower
                or "article" in reason_lower
                or "paper" in reason_lower
            ):
                current_selections[fs.path] = "main_article"
            elif "visual" in reason_lower or "script" in reason_lower:
                current_selections[fs.path] = "visualization_scripts"
            elif "data" in reason_lower:
                current_selections[fs.path] = "data_files"
            elif "doc" in reason_lower:
                current_selections[fs.path] = "documentation"
            else:
                current_selections[fs.path] = "other"

    # File selection state
    # Initialize with current selections to avoid disconnect on open
    selected_paths = dict(current_selections)

    # Build dialog
    with ui.dialog() as dialog, ui.card().classes("w-[700px] h-[600px]"):
        ui.label(_("Select Significant Files")).classes("text-h6 mb-2")
        ui.markdown(
            _(
                "**Instructions:** Select files for deep analysis and assign categories. "
                "The AI will read these files to extract metadata."
            )
        ).classes("text-sm text-slate-600 mb-4")

        with ui.scroll_area().classes("h-96 w-full border rounded-md"):
            with ui.column().classes("gap-0"):
                # Header
                with ui.row().classes(
                    "w-full items-center gap-2 p-2 bg-slate-100 font-bold text-sm"
                ):
                    ui.label(_("File")).classes("flex-grow")
                    ui.label(_("Category")).classes("w-48")

                # Files
                for item in inventory:
                    path = item.get("path", "")
                    if not path or item.get("type") == "folder":
                        continue

                    with ui.row().classes(
                        "w-full items-center gap-2 p-1 hover:bg-slate-50"
                    ):
                        # Category dropdown (needs to be defined before checkbox for on_change access)
                        # but logically appears after the file path label in layout
                        # We use a placeholder and then define it
                        
                        # Checkbox
                        is_selected = path in current_selections
                        
                        def toggle_selection(e, p=path, dropdown=None):
                            if e.value:
                                # Use dropdown value if available, else default to 'other'
                                cat = dropdown.value if dropdown else "other"
                                selected_paths[p] = cat
                            else:
                                selected_paths.pop(p, None)

                        cb = ui.checkbox(
                            value=is_selected,
                        ).props("dense")"""

# This script is getting complicated due to nested logic. 
# Let's try a simpler replacement.
