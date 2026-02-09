import asyncio
from pathlib import Path
from nicegui import ui
from opendata.i18n.translator import _
from opendata.ui.state import ScanState, UIState
from opendata.ui.context import AppContext
from opendata.utils import format_size
from opendata.ui.components.metadata import metadata_preview_ui


@ui.refreshable
def render_preview_and_build(ctx: AppContext):
    with ui.column().classes("w-full gap-4"):
        with ui.card().classes("w-full p-6 shadow-md border-t-4 border-green-600"):
            with ui.row().classes("w-full justify-between items-center mb-4"):
                ui.label(_("RODBUK Submission Preview")).classes(
                    "text-h5 font-bold text-green-800"
                )
                with ui.row().classes("gap-2"):
                    ui.button(
                        _("Metadata Only"),
                        icon="description",
                        color="blue",
                        on_click=lambda: handle_build_package(ctx, mode="metadata"),
                    ).classes("px-4").props("outline")
                    ui.button(
                        _("Build Full Package"),
                        icon="archive",
                        color="green",
                        on_click=lambda: handle_build_package(ctx, mode="full"),
                    ).classes("px-6 font-bold")

            ui.markdown(
                _(
                    "Review your metadata before generating the final package. The full package will respect your file selection."
                )
            )
            ui.separator().classes("my-4")

            # Reuse metadata preview logic
            metadata_preview_ui(ctx)

        with ui.card().classes("w-full p-6 shadow-md"):
            ui.label(_("Final Selection Summary")).classes("text-h6 font-bold mb-2")
            if ctx.agent.project_id:
                if UIState.is_loading_inventory:
                    with ui.row().classes("items-center gap-2"):
                        ui.spinner(size="sm")
                        ui.label(_("Calculating package statistics...")).classes(
                            "text-slate-500 italic"
                        )
                else:
                    with ui.row().classes("gap-4 items-center"):
                        ui.icon("inventory", size="md", color="slate-600")
                        with ui.column().classes("gap-0"):
                            ui.label(
                                _("{count} files selected for inclusion").format(
                                    count=UIState.total_files_count
                                )
                            ).classes("font-bold")
                            ui.label(
                                _("Estimated Package Data Size: {size}").format(
                                    size=format_size(UIState.total_files_size)
                                )
                            ).classes("text-sm text-slate-500")

                ui.button(
                    _("Edit Selection"),
                    icon="edit",
                    on_click=lambda: UIState.main_tabs.set_value(UIState.package_tab),
                ).classes("mt-4").props("flat color=primary")
            else:
                ui.label(_("No project active.")).classes("text-slate-400 italic")


async def handle_build_package(ctx: AppContext, mode: str = "metadata"):
    if not ScanState.current_path or not ctx.agent.project_id:
        ui.notify(_("Please select a project first."), type="warning")
        return

    project_id: str = ctx.agent.project_id
    canonical_path = Path(ScanState.current_path).expanduser().resolve()

    # Validation
    errors = ctx.packaging_service.validate_for_rodbuk(ctx.agent.current_metadata)
    if errors:
        ui.notify(
            _("Metadata validation failed:") + "\n" + "\n".join(errors),
            type="negative",
            multi_line=True,
        )
        return

    try:
        ui.notify(
            _("Building metadata package...")
            if mode == "metadata"
            else _("Building full data package...")
        )

        if mode == "metadata":
            pkg_path = await asyncio.to_thread(
                ctx.packaging_service.generate_metadata_package,
                canonical_path,
                ctx.agent.current_metadata,
            )
        else:
            manifest = ctx.pkg_mgr.get_manifest(project_id)
            field_name = (
                ctx.agent.current_metadata.science_branches_mnisw[0]
                if ctx.agent.current_metadata.science_branches_mnisw
                else None
            )
            effective = ctx.pm.resolve_effective_protocol(project_id, field_name)
            protocol_excludes = effective.get("exclude", [])

            file_list = await asyncio.to_thread(
                ctx.pkg_mgr.get_effective_file_list,
                canonical_path,
                manifest,
                protocol_excludes,
            )

            pkg_path = await asyncio.to_thread(
                ctx.packaging_service.generate_package,
                canonical_path,
                ctx.agent.current_metadata,
                "rodbuk_full_package",
                file_list,
            )

        ui.notify(
            _("Package created: {name}").format(name=pkg_path.name), type="positive"
        )
        ui.download(pkg_path)

        ctx.agent.chat_history.append(
            (
                "assistant",
                _("Package created successfully: {name}").format(name=pkg_path.name),
            )
        )
        ctx.refresh("chat")
    except Exception as e:
        ui.notify(
            _("Failed to build package: {error}").format(error=str(e)),
            type="negative",
        )
