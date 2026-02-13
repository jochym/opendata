from nicegui import ui

from opendata.i18n.translator import _
from opendata.models import ExtractionProtocol
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


def _make_textarea(value: str, is_readonly: bool, mono: bool = False):
    """Create a textarea that fills its parent absolutely."""
    extra_cls = " font-mono" if mono else ""
    ta = ui.textarea(value=value).props(
        f"outlined {'readonly' if is_readonly else ''} autogrow=false"
    )
    # Force the Quasar component + inner textarea to fill container
    # The 'h-full' class triggers the global CSS override for q-textarea
    ta.style("position:absolute; inset:0; width:100%; height:100%;").classes(
        f"h-full text-xs{extra_cls}"
    )
    ta.props('input-style="height:100%"')
    ta.props('input-class="h-full"')
    return ta


def render_protocol_editor(ctx: AppContext, protocol: ExtractionProtocol, on_save=None):
    is_readonly = protocol.is_read_only

    # Calculate available height: subtract header bar (if readonly banner shown, ~40px extra)

    with ui.element("div").style(
        "width:100%; height:100%; display:flex; flex-direction:column; overflow:hidden; padding:8px; gap:8px;"
    ):
        if is_readonly:
            with ui.element("div").style(
                "width:100%; flex-shrink:0; display:flex; align-items:center; gap:8px;"
                " background:#fff7ed; padding:8px; border-radius:4px; border:1px solid #fed7aa;"
            ):
                ui.icon("lock", color="orange")
                ui.label(_("This protocol is Read-Only.")).classes(
                    "text-xs text-orange-800 font-medium"
                )

        # CSS Grid 2x2 - this is the core layout
        with ui.element("div").style(
            "flex:1; min-height:0; display:grid;"
            " grid-template-columns:1fr 1fr; grid-template-rows:1fr 1fr;"
            " gap:8px;"
        ):
            # Cell 1: Exclusion Patterns (top-left)
            with ui.element("div").style(
                "display:flex; flex-direction:column; overflow:hidden;"
                " border:1px solid #e2e8f0; border-radius:8px; padding:12px;"
            ):
                ui.label(_("Exclusion Patterns (Glob)")).classes(
                    "text-sm font-bold text-slate-700"
                ).style("flex-shrink:0")
                with ui.element("div").style(
                    "flex:1; min-height:0; position:relative; margin-top:4px;"
                ):
                    exclude_area = _make_textarea(
                        "\n".join(protocol.exclude_patterns), is_readonly, mono=True
                    )
                ui.label(_("One per line. e.g. **/temp/*")).classes(
                    "text-slate-500"
                ).style("flex-shrink:0; font-size:10px; margin-top:2px;")

            # Cell 2: Metadata Agent Prompts (top-right)
            with ui.element("div").style(
                "display:flex; flex-direction:column; overflow:hidden;"
                " border:1px solid #dbeafe; border-radius:8px; padding:12px;"
                " background:rgba(239,246,255,0.3);"
            ):
                ui.label(_("Metadata Agent Prompts")).classes(
                    "text-sm font-bold text-blue-800"
                ).style("flex-shrink:0")
                with ui.element("div").style(
                    "flex:1; min-height:0; position:relative; margin-top:4px;"
                ):
                    meta_prompts_area = _make_textarea(
                        "\n".join(
                            protocol.metadata_prompts or protocol.extraction_prompts
                        ),
                        is_readonly,
                    )
                ui.label(_("Instructions for RODBUK metadata collection.")).classes(
                    "text-blue-500"
                ).style("flex-shrink:0; font-size:10px; margin-top:2px;")

            # Cell 3: Inclusion Patterns (bottom-left)
            with ui.element("div").style(
                "display:flex; flex-direction:column; overflow:hidden;"
                " border:1px solid #e2e8f0; border-radius:8px; padding:12px;"
            ):
                ui.label(_("Inclusion Patterns (Glob)")).classes(
                    "text-sm font-bold text-slate-700"
                ).style("flex-shrink:0")
                with ui.element("div").style(
                    "flex:1; min-height:0; position:relative; margin-top:4px;"
                ):
                    include_area = _make_textarea(
                        "\n".join(protocol.include_patterns), is_readonly, mono=True
                    )
                ui.label(_("Force include specific files.")).classes(
                    "text-slate-500"
                ).style("flex-shrink:0; font-size:10px; margin-top:2px;")

            # Cell 4: Curator Agent Prompts (bottom-right)
            with ui.element("div").style(
                "display:flex; flex-direction:column; overflow:hidden;"
                " border:1px solid #e9d5ff; border-radius:8px; padding:12px;"
                " background:rgba(250,245,255,0.3);"
            ):
                ui.label(_("Curator Agent Prompts")).classes(
                    "text-sm font-bold text-purple-800"
                ).style("flex-shrink:0")
                with ui.element("div").style(
                    "flex:1; min-height:0; position:relative; margin-top:4px;"
                ):
                    curator_prompts_area = _make_textarea(
                        "\n".join(protocol.curator_prompts), is_readonly
                    )
                ui.label(
                    _("Instructions for file selection and reproducibility.")
                ).classes("text-purple-500").style(
                    "flex-shrink:0; font-size:10px; margin-top:2px;"
                )

        if not is_readonly and on_save:
            with ui.element("div").style(
                "flex-shrink:0; display:flex; justify-content:flex-end; padding-top:4px;"
            ):

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
