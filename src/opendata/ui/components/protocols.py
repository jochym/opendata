from nicegui import ui
from opendata.i18n.translator import _
from opendata.models import ExtractionProtocol
from opendata.ui.state import ScanState
from opendata.ui.context import AppContext


@ui.refreshable
def render_protocols_tab(ctx: AppContext):
    with ui.column().classes("w-full gap-4"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(_("Extraction Protocols")).classes("text-h4 font-bold")
            with ui.row().classes("gap-2"):
                ui.icon("info", color="primary").classes("cursor-help")
                ui.tooltip(
                    _(
                        "Protocols guide the AI and scanner. Rules are applied from System to Project level."
                    )
                )

        with ui.tabs().classes("w-full") as protocol_tabs:
            sys_tab = ui.tab(_("System"), icon="settings_suggest")
            glob_tab = ui.tab(_("Global"), icon="public")
            field_tab = ui.tab(_("Field/Domain"), icon="science")
            proj_tab = ui.tab(_("Project"), icon="folder_special")

        with ui.tab_panels(protocol_tabs, value=sys_tab).classes(
            "w-full bg-white border rounded shadow-sm"
        ):
            with ui.tab_panel(sys_tab):
                render_protocol_editor(ctx, ctx.pm.system_protocol)
            with ui.tab_panel(glob_tab):
                render_protocol_editor(
                    ctx,
                    ctx.pm.get_global_protocol(),
                    on_save=ctx.pm.save_global_protocol,
                )
            with ui.tab_panel(field_tab):
                current_fields = ctx.pm.list_fields()
                field_container = ui.column().classes("w-full")

                def refresh_field_editor():
                    field_container.clear()
                    if field_select.value:
                        with field_container:
                            render_protocol_editor(
                                ctx,
                                ctx.pm.get_field_protocol(field_select.value),
                                on_save=ctx.pm.save_field_protocol,
                            )

                with ui.column().classes("w-full gap-4 mb-4"):
                    with ui.row().classes("w-full items-center gap-4"):
                        field_select = ui.select(
                            options=current_fields,
                            label=_("Select Field Domain"),
                            value=current_fields[0] if current_fields else None,
                        ).classes("w-64")

                        new_field_input = (
                            ui.input(label=_("New Field Name"))
                            .classes("w-48")
                            .props("dense")
                        )

                        def create_new_field():
                            name = new_field_input.value.strip()
                            if not name:
                                ui.notify(
                                    _("Field name cannot be empty."), type="warning"
                                )
                                return
                            new_p = ctx.pm.get_field_protocol(name)
                            ctx.pm.save_field_protocol(new_p)
                            ui.notify(_("Field '{name}' created.").format(name=name))
                            # Update selector
                            new_fields = ctx.pm.list_fields()
                            field_select.options = new_fields
                            field_select.value = name
                            new_field_input.value = ""
                            refresh_field_editor()

                        ui.button(
                            _("Create Field"), icon="add", on_click=create_new_field
                        ).props("outline")

                    field_container = ui.column().classes("w-full mt-4")
                    field_select.on("update:model-value", refresh_field_editor)
                    refresh_field_editor()

            with ui.tab_panel(proj_tab):
                if ctx.agent.project_id:
                    # Use a local variable to capture the non-None value for the lambda
                    pid: str = ctx.agent.project_id
                    render_protocol_editor(
                        ctx,
                        ctx.pm.get_project_protocol(pid),
                        on_save=lambda p, pid=pid: ctx.pm.save_project_protocol(pid, p),
                    )

                else:
                    with ui.column().classes("w-full items-center p-8"):
                        ui.icon("folder_open", size="lg", color="grey-400")
                        ui.label(_("Please select and open a project first.")).classes(
                            "text-orange-600 font-bold"
                        )
                        ui.markdown(
                            _(
                                "Use the **Open** button in the Analysis tab to activate this project."
                            )
                        ).classes("text-sm text-slate-500")


def render_protocol_editor(ctx: AppContext, protocol: ExtractionProtocol, on_save=None):
    is_readonly = protocol.is_read_only

    with ui.column().classes("w-full gap-6 p-4"):
        if is_readonly:
            ui.label(_("This protocol is Read-Only.")).classes(
                "text-xs text-orange-600 italic"
            )

        # Exclusion Patterns
        with ui.column().classes("w-full gap-2"):
            ui.label(_("Exclude Patterns (Glob)")).classes(
                "text-sm font-bold text-slate-700"
            )
            exclude_area = (
                ui.textarea(value="\n".join(protocol.exclude_patterns))
                .classes("w-full font-mono text-sm")
                .props(f"outlined {'readonly' if is_readonly else ''} rows=4")
            )
            ui.markdown(_("One pattern per line. e.g. `**/temp/*` or `*.log`")).classes(
                "text-[10px] text-slate-500"
            )

        # Include Patterns
        with ui.column().classes("w-full gap-2"):
            ui.label(_("Include Patterns (Glob)")).classes(
                "text-sm font-bold text-slate-700"
            )
            include_area = (
                ui.textarea(value="\n".join(protocol.include_patterns))
                .classes("w-full font-mono text-sm")
                .props(f"outlined {'readonly' if is_readonly else ''} rows=3")
            )
            ui.markdown(_("Force include specific files.")).classes(
                "text-[10px] text-slate-500"
            )

        # AI Prompts
        with ui.column().classes("w-full gap-2"):
            ui.label(_("AI Instructions / Prompts")).classes(
                "text-sm font-bold text-slate-700"
            )
            prompts_area = (
                ui.textarea(value="\n".join(protocol.extraction_prompts))
                .classes("w-full text-sm")
                .props(f"outlined {'readonly' if is_readonly else ''} rows=6")
            )
            ui.markdown(_("Specific instructions for the AI agent.")).classes(
                "text-[10px] text-slate-500"
            )

        if not is_readonly and on_save:

            def handle_save():
                protocol.exclude_patterns = [
                    l.strip() for l in exclude_area.value.split("\n") if l.strip()
                ]
                protocol.include_patterns = [
                    l.strip() for l in include_area.value.split("\n") if l.strip()
                ]
                protocol.extraction_prompts = [
                    l.strip() for l in prompts_area.value.split("\n") if l.strip()
                ]
                on_save(protocol)
                ui.notify(
                    _("Protocol '{name}' saved.").format(name=protocol.name),
                    type="positive",
                )

            ui.button(_("Save Changes"), icon="save", on_click=handle_save).classes(
                "w-full mt-4"
            ).props("color=primary")
