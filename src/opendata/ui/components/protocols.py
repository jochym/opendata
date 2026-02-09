from nicegui import ui
from opendata.i18n.translator import _
from opendata.models import ExtractionProtocol
from opendata.ui.state import ScanState
from opendata.ui.context import AppContext


@ui.refreshable
def render_protocols_tab(ctx: AppContext):
    # Overall container taking full height
    # 104px is the height of header + tabs in main layout
    with ui.column().classes("w-full h-[calc(100vh-104px)] gap-0 p-0 overflow-hidden"):
        # Header and Tabs on the same row
        with ui.row().classes(
            "w-full items-center justify-between px-4 bg-slate-50 border-b shrink-0"
        ):
            ui.label(_("Protocols")).classes("text-h5 font-bold text-slate-700 py-2")

            with ui.tabs().classes("flex-grow justify-end") as protocol_tabs:
                sys_tab = ui.tab(_("System"), icon="settings_suggest")
                glob_tab = ui.tab(_("Global"), icon="public")
                field_tab = ui.tab(_("Field"), icon="science")
                proj_tab = ui.tab(_("Project"), icon="folder_special")

        with ui.tab_panels(protocol_tabs, value=sys_tab).classes(
            "w-full flex-grow bg-white overflow-hidden"
        ):
            with ui.tab_panel(sys_tab).classes("p-0 h-full"):
                render_protocol_editor(ctx, ctx.pm.system_protocol)

            with ui.tab_panel(glob_tab).classes("p-0 h-full"):
                render_protocol_editor(
                    ctx,
                    ctx.pm.get_global_protocol(),
                    on_save=ctx.pm.save_global_protocol,
                )

            with ui.tab_panel(field_tab).classes("p-0 h-full"):
                current_fields = ctx.pm.list_fields()

                with ui.column().classes("w-full h-full gap-0"):
                    # Field selector bar
                    with ui.row().classes(
                        "w-full items-center gap-4 p-4 border-b bg-slate-50 shrink-0"
                    ):
                        field_select = (
                            ui.select(
                                options=current_fields,
                                label=_("Field Domain"),
                                value=current_fields[0] if current_fields else None,
                            )
                            .classes("w-64")
                            .props("dense outlined")
                        )

                        new_field_input = (
                            ui.input(placeholder=_("New Field Name"))
                            .classes("w-48")
                            .props("dense outlined")
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
                            new_fields = ctx.pm.list_fields()
                            field_select.options = new_fields
                            field_select.value = name
                            new_field_input.value = ""
                            ctx.refresh("protocols")

                        ui.button(icon="add", on_click=create_new_field).props(
                            "outline dense"
                        ).classes("h-10")

                    # Editor area
                    field_container = ui.column().classes("w-full flex-grow h-0")

                    @ui.refreshable
                    def render_field_content():
                        if field_select.value:
                            render_protocol_editor(
                                ctx,
                                ctx.pm.get_field_protocol(field_select.value),
                                on_save=ctx.pm.save_field_protocol,
                            )

                    with field_container:
                        render_field_content()

                    field_select.on("update:model-value", render_field_content.refresh)

            with ui.tab_panel(proj_tab).classes("p-0 h-full"):
                if ctx.agent.project_id:
                    pid: str = ctx.agent.project_id
                    render_protocol_editor(
                        ctx,
                        ctx.pm.get_project_protocol(pid),
                        on_save=lambda p, pid=pid: ctx.pm.save_project_protocol(pid, p),
                    )
                else:
                    with ui.column().classes(
                        "w-full h-full items-center justify-center p-20 gap-4"
                    ):
                        ui.icon("folder_open", size="xl", color="grey-400")
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

    with ui.column().classes("w-full h-full p-4 gap-4 overflow-hidden no-wrap"):
        if is_readonly:
            with ui.row().classes(
                "w-full bg-orange-50 p-2 rounded border border-orange-100 items-center gap-2 shrink-0"
            ):
                ui.icon("lock", color="orange")
                ui.label(_("This protocol is Read-Only.")).classes(
                    "text-xs text-orange-800 font-medium"
                )

        # Main layout row - distributed equally (50/50)
        # Using specific flex classes to ensure filling
        with ui.row().classes("w-full flex-grow gap-4 no-wrap items-stretch h-0"):
            # LEFT: Patterns
            with (
                ui.column()
                .style("width: 50%")
                .classes("h-full gap-4 no-wrap items-stretch")
            ):
                # We use flex-col on the card and then allow the textarea container to grow
                with ui.card().classes(
                    "w-full flex-grow p-4 shadow-none border flex flex-col no-wrap items-stretch overflow-hidden"
                ):
                    ui.label(_("Exclusion Patterns (Glob)")).classes(
                        "text-sm font-bold text-slate-700 shrink-0"
                    )
                    # Container for textarea to force full height
                    with ui.column().classes("w-full flex-grow relative"):
                        exclude_area = (
                            ui.textarea(value="\n".join(protocol.exclude_patterns))
                            .classes("w-full h-full absolute inset-0 font-mono text-xs")
                            .props(
                                f'outlined {"readonly" if is_readonly else ""} autogrow=false input-style="height:100%" class="h-full"'
                            )
                        )
                    ui.markdown(_("One per line. e.g. `**/temp/*`")).classes(
                        "text-[10px] text-slate-500 shrink-0 mt-1"
                    )

                with ui.card().classes(
                    "w-full flex-grow p-4 shadow-none border flex flex-col no-wrap items-stretch overflow-hidden"
                ):
                    ui.label(_("Inclusion Patterns (Glob)")).classes(
                        "text-sm font-bold text-slate-700 shrink-0"
                    )
                    with ui.column().classes("w-full flex-grow relative"):
                        include_area = (
                            ui.textarea(value="\n".join(protocol.include_patterns))
                            .classes("w-full h-full absolute inset-0 font-mono text-xs")
                            .props(
                                f'outlined {"readonly" if is_readonly else ""} autogrow=false input-style="height:100%" class="h-full"'
                            )
                        )
                    ui.markdown(_("Force include specific files.")).classes(
                        "text-[10px] text-slate-500 shrink-0 mt-1"
                    )

            # RIGHT: Agent Prompts - distributed equally (50/50)
            with (
                ui.column()
                .style("width: 50%")
                .classes("h-full gap-4 no-wrap items-stretch")
            ):
                with ui.card().classes(
                    "w-full flex-grow p-4 shadow-none border border-blue-100 bg-blue-50/30 flex flex-col no-wrap items-stretch overflow-hidden"
                ):
                    ui.label(_("Metadata Agent Prompts")).classes(
                        "text-sm font-bold text-blue-800 shrink-0"
                    )
                    with ui.column().classes("w-full flex-grow relative"):
                        meta_prompts_area = (
                            ui.textarea(
                                value="\n".join(
                                    protocol.metadata_prompts
                                    or protocol.extraction_prompts
                                )
                            )
                            .classes("w-full h-full absolute inset-0 text-xs")
                            .props(
                                f'outlined {"readonly" if is_readonly else ""} autogrow=false input-style="height:100%" class="h-full"'
                            )
                        )
                    ui.markdown(
                        _("Instructions for RODBUK metadata collection.")
                    ).classes("text-[10px] text-blue-500 shrink-0 mt-1")

                with ui.card().classes(
                    "w-full flex-grow p-4 shadow-none border border-purple-100 bg-purple-50/30 flex flex-col no-wrap items-stretch overflow-hidden"
                ):
                    ui.label(_("Curator Agent Prompts")).classes(
                        "text-sm font-bold text-purple-800 shrink-0"
                    )
                    with ui.column().classes("w-full flex-grow relative"):
                        curator_prompts_area = (
                            ui.textarea(value="\n".join(protocol.curator_prompts))
                            .classes("w-full h-full absolute inset-0 text-xs")
                            .props(
                                f'outlined {"readonly" if is_readonly else ""} autogrow=false input-style="height:100%" class="h-full"'
                            )
                        )
                    ui.markdown(
                        _("Instructions for file selection and reproducibility.")
                    ).classes("text-[10px] text-purple-500 shrink-0 mt-1")

        if not is_readonly and on_save:
            with ui.row().classes("w-full mt-2 justify-end shrink-0"):

                def handle_save():
                    protocol.exclude_patterns = [
                        l.strip() for l in exclude_area.value.split("\n") if l.strip()
                    ]
                    protocol.include_patterns = [
                        l.strip() for l in include_area.value.split("\n") if l.strip()
                    ]
                    protocol.metadata_prompts = [
                        l.strip()
                        for l in meta_prompts_area.value.split("\n")
                        if l.strip()
                    ]
                    protocol.curator_prompts = [
                        l.strip()
                        for l in curator_prompts_area.value.split("\n")
                        if l.strip()
                    ]
                    on_save(protocol)
                    ui.notify(
                        _("Protocol '{name}' saved.").format(name=protocol.name),
                        type="positive",
                    )

                ui.button(
                    _("Save Protocol Changes"), icon="save", on_click=handle_save
                ).classes("px-8").props("elevated color=primary")
