"""Bug Report Dialog component.

Presents a dialog with editable title, reporter name, description, and an
attached-file list (the diagnostic YAML is auto-included).

Submission strategy:
- If ``OPENDATA_BUG_REPORT_TOKEN`` is set, the issue is created directly via
  the GitHub REST API (no user account needed).
- Otherwise the user is informed that automatic submission is not available
  and instructed to share the diagnostic YAML file with the maintainer.
"""

import asyncio
import logging
import os
from pathlib import Path

from nicegui import ui

from opendata.agents.project_agent import _GITHUB_BUG_REPORT_TOKEN_ENV
from opendata.i18n.translator import _
from opendata.ui.context import AppContext

logger = logging.getLogger("opendata.ui.bug_report_dialog")

_MAX_BODY_CHARS = 7000
_BODY_TRUNCATION_LENGTH = 6950
_MAX_EMBEDDABLE_FILE_SIZE = 50_000  # bytes
_ATTACHMENT_CONTENT_PREVIEW_LENGTH = 3000  # chars


def show_bug_report_dialog(ctx: AppContext, bug_report: dict) -> None:
    """Open the bug-report dialog.

    Args:
        ctx: Application context.
        bug_report: Dict produced by ``ProjectAnalysisAgent._handle_bug_command``
            containing ``title``, ``description``, ``system_body``, and
            ``extra_files`` keys.
    """
    from opendata.ui.components.file_picker import LocalFilePicker

    selected_files: list[str] = list(bug_report.get("extra_files", []))

    def _build_body(description: str, reporter_name: str) -> str:
        """Assemble the full issue body from description + auto context + files."""
        system_body = bug_report.get("system_body", "")
        reporter_section = (
            f"## Reporter\n- **Name:** {reporter_name}" if reporter_name.strip() else ""
        )
        parts = [
            p
            for p in [
                f"## Bug Description\n{description}",
                reporter_section,
                system_body,
            ]
            if p
        ]
        for fpath in selected_files:
            p = Path(fpath)
            if not p.exists():
                continue
            size = p.stat().st_size
            if size < _MAX_EMBEDDABLE_FILE_SIZE:
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                    parts.append(
                        f"### Attachment: `{p.name}`\n```yaml\n"
                        f"{content[:_ATTACHMENT_CONTENT_PREVIEW_LENGTH]}\n```"
                    )
                except Exception:
                    parts.append(f"### Attachment: `{p.name}`\n(unreadable)")
            else:
                parts.append(
                    f"### Attachment: `{p.name}`\n"
                    f"(too large to embed: {size // 1024} KB)"
                )
        body = "\n\n".join(parts)
        if len(body) > _MAX_BODY_CHARS:
            body = body[:_BODY_TRUNCATION_LENGTH] + "\n...(truncated)"
        return body

    with (
        ui.dialog() as dialog,
        ui.card().classes(
            "w-[650px] max-w-[95vw] h-[85vh] p-0 overflow-hidden flex flex-col"
        ),
    ):
        # --- Header ---
        with ui.row().classes(
            "w-full items-center justify-between bg-red-600 text-white p-3 shrink-0"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.icon("bug_report")
                ui.label(_("Report a Bug")).classes("text-lg font-bold")
            ui.button(icon="close", on_click=dialog.close).props(
                "flat dense color=white"
            )

        # --- Scrollable body (taller) ---
        with ui.scroll_area().classes("flex-grow w-full p-4"):
            with ui.column().classes("w-full gap-4"):
                # Check if token is configured
                has_token = bool((ctx.settings.github_bug_report_token or "").strip())

                # Show token setup if not configured
                if not has_token:
                    with ui.card().classes(
                        "w-full bg-yellow-50 border border-yellow-200 p-3"
                    ):
                        with ui.column().classes("w-full gap-2"):
                            ui.label(_("⚠️  GitHub Token Required")).classes(
                                "text-sm font-bold text-yellow-800"
                            )
                            ui.markdown(
                                _(
                                    "**Automatic bug reports require a GitHub token.**\n\n"
                                    "**To get the token:**\n"
                                    "Contact the application author to obtain the bug report token.\n\n"
                                    "**Then paste it below:**"
                                )
                            ).classes("w-full text-xs text-yellow-700")

                            token_input = (
                                ui.input(
                                    label=_("GitHub Token"),
                                    placeholder="ghp_...",
                                    password=True,
                                )
                                .props("outlined dense")
                                .classes("w-full")
                            )

                            async def save_token_and_submit():
                                token = token_input.value.strip()
                                if token:
                                    ctx.settings.github_bug_report_token = token
                                    ctx.wm.save_yaml(ctx.settings, "settings.yaml")
                                    ui.notify(_("GitHub token saved!"), type="positive")
                                    # Close dialog - user can click /bug again or Submit from here
                                    # Actually, let's just hide the yellow box and show normal submit
                                    # We don't have easy reference to instructions_card now, so we refresh
                                    ctx.refresh_all()
                                else:
                                    ui.notify(
                                        _("Please enter a valid token"), type="warning"
                                    )

                            save_btn = (
                                ui.button(
                                    _("Save Token & Submit"),
                                    icon="save",
                                    on_click=save_token_and_submit,
                                    color="yellow",
                                )
                                .props("elevated")
                                .classes("w-full")
                            )

                            ui.separator()

                # Issue Type Selection
                ui.label(_("Issue Type")).classes("text-sm font-bold text-slate-600")
                issue_type_select = (
                    ui.select(
                        label=_("Select issue type"),
                        options={
                            "bug": "🐛 Bug - Something isn't working",
                            "enhancement": "✨ Enhancement - New feature or request",
                            "documentation": "📚 Documentation - Improvements or additions",
                            "question": "❓ Question - Need help or information",
                            "feature": "🚀 Feature - New functionality",
                            "performance": "⚡ Performance - Speed or efficiency improvements",
                        },
                        value="bug",
                    )
                    .props("outlined dense")
                    .classes("w-full")
                )

                title_input = (
                    ui.input(
                        label=_("Title"),
                        value=bug_report.get("title", "Bug"),
                    )
                    .props("outlined dense")
                    .classes("w-full")
                )

                name_input = (
                    ui.input(
                        label=_("Your Name (for contact)"),
                        placeholder=_("Full name or nickname"),
                    )
                    .props("outlined dense")
                    .classes("w-full")
                )

                desc_input = (
                    ui.textarea(
                        label=_("Description"),
                        value=bug_report.get("description", ""),
                        placeholder=_(
                            "Describe what went wrong, steps to reproduce,"
                            " expected vs actual behaviour..."
                        ),
                    )
                    .props("outlined rows=8")
                    .classes("w-full")
                )

                ui.separator()

                ui.label(_("Attached Files")).classes(
                    "text-sm font-bold text-slate-700"
                )
                ui.label(
                    _(
                        "The diagnostic YAML is included automatically."
                        " You may add further files."
                    )
                ).classes("text-xs text-slate-500")

                file_list = ui.column().classes("w-full gap-1")

                def _refresh_files() -> None:
                    file_list.clear()
                    with file_list:
                        if not selected_files:
                            ui.label(_("No files attached.")).classes(
                                "text-xs text-slate-400 italic"
                            )
                            return
                        for fpath in list(selected_files):
                            p = Path(fpath)
                            size_str = (
                                f"{p.stat().st_size // 1024} KB"
                                if p.exists()
                                else _("missing")
                            )
                            with ui.row().classes(
                                "w-full items-center gap-2 p-2 bg-slate-50"
                                " rounded border border-slate-200"
                            ):
                                ui.icon("attach_file", color="blue-grey", size="sm")
                                ui.label(p.name).classes(
                                    "flex-grow text-sm font-mono truncate"
                                ).tooltip(fpath)
                                ui.label(f"({size_str})").classes(
                                    "text-xs text-slate-400"
                                )

                                def _make_remove(fp: str):
                                    def _remove() -> None:
                                        if fp in selected_files:
                                            selected_files.remove(fp)
                                        _refresh_files()

                                    return _remove

                                ui.button(
                                    icon="close",
                                    on_click=_make_remove(fpath),
                                ).props("flat dense color=red size=sm")

                _refresh_files()

                async def _add_file() -> None:
                    picker = LocalFilePicker(directory="~", directory_only=False)
                    result = await picker
                    if result and result not in selected_files:
                        selected_files.append(result)
                        _refresh_files()

                ui.button(
                    _("Add File"),
                    icon="add",
                    on_click=_add_file,
                ).props("flat dense color=blue-grey").classes("w-fit")

        # --- Footer ---
        with ui.row().classes(
            "w-full justify-between items-center p-3 gap-2 shrink-0"
            " border-t bg-slate-50"
        ):
            status_label = ui.label("").classes("text-xs text-slate-500 flex-grow")

            with ui.row().classes("gap-2"):
                ui.button(_("Cancel"), on_click=dialog.close).props("flat")

                async def _submit() -> None:
                    title = title_input.value.strip() or _("Bug Report")
                    reporter_name = name_input.value.strip()
                    description = desc_input.value.strip() or _(
                        "No description provided."
                    )

                    # Get selected issue type
                    selected_type = str(issue_type_select.value or "bug")

                    # Add issue type prefix to title if not already present
                    type_emojis = {
                        "bug": "🐛",
                        "enhancement": "✨",
                        "documentation": "📚",
                        "question": "❓",
                        "feature": "🚀",
                        "performance": "⚡",
                    }
                    emoji = type_emojis.get(selected_type, "")
                    if emoji and not title.startswith(emoji):
                        title = f"{emoji} [{selected_type.title()}] {title}"

                    body = _build_body(description, reporter_name)

                    # Try settings first, then env var, then embedded (build-time)
                    # Try settings, then env var
                    token = (ctx.settings.github_bug_report_token or "").strip()
                    if not token:
                        token = os.environ.get(_GITHUB_BUG_REPORT_TOKEN_ENV, "").strip()

                    if token:
                        submit_btn.disable()
                        status_label.set_text(_("Submitting…"))

                        # Pass labels to the API method
                        issue_url = await asyncio.to_thread(
                            ctx.agent._submit_bug_via_github_api,
                            title,
                            body,
                            token,
                            [selected_type],
                        )
                        if issue_url:
                            dialog.close()
                            ui.notify(
                                _("Bug report submitted!"),
                                caption=issue_url,
                                type="positive",
                                timeout=10_000,
                            )
                            ctx.agent.chat_history.append(
                                (
                                    "agent",
                                    f"✅ **{_('Bug report submitted!')}**\n\n"
                                    f"**[{issue_url}]({issue_url})**",
                                )
                            )
                            ctx.agent.save_state()
                            ctx.refresh("chat")
                            return
                        submit_btn.enable()
                        status_label.set_text(_("Direct submission failed."))
                        return

                    # No token configured — inform user and show file to share.
                    yaml_path = (
                        bug_report["extra_files"][0]
                        if bug_report.get("extra_files")
                        else None
                    )
                    dialog.close()
                    path_hint = f"\n`{yaml_path}`" if yaml_path else ""
                    ctx.agent.chat_history.append(
                        (
                            "agent",
                            f"ℹ️ **{_('Automatic bug submission requires a GitHub token.')}**\n\n"
                            + _(
                                "**To enable:**\n"
                                "1. Go to Settings tab\n"
                                "2. Add your GitHub token (public_repo scope)\n"
                                "3. Try /bug again\n\n"
                                "**For now, please share this file:**"
                            )
                            + path_hint,
                        )
                    )
                    ctx.agent.save_state()
                    ctx.refresh("chat")

                submit_btn = ui.button(
                    _("Submit Bug Report"),
                    icon="send",
                    on_click=_submit,
                ).props("elevated color=red")

    dialog.open()
