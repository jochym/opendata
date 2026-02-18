import re
import yaml
from nicegui import ui
from opendata.i18n.translator import _
from opendata.ui.state import ScanState, UIState
from opendata.ui.context import AppContext


@ui.refreshable
def metadata_preview_ui(ctx: AppContext):
    if ScanState.is_scanning:
        with ui.column().classes("w-full items-center justify-center p-8 gap-1"):
            ui.spinner(size="lg")
            ui.label("").classes("text-xs font-bold text-slate-700").bind_text_from(
                ScanState, "progress"
            )
            with ui.label("").classes(
                "text-[10px] text-slate-500 animate-pulse text-center w-full truncate cursor-help"
            ) as lbl:
                ui.tooltip("").bind_text_from(ScanState, "full_path")
                lbl.bind_text_from(ScanState, "short_path")
            ScanState.progress_label = lbl
        return

    if not ctx.agent.project_id:
        return

    # Significant Files Section (Foldable)
    if (
        ctx.agent.current_fingerprint
        and ctx.agent.current_fingerprint.significant_files
    ):
        with ui.expansion(
            _("Significant Files for Analysis"), icon="fact_check"
        ).classes(
            "w-full bg-blue-50 border border-blue-100 rounded-lg shadow-none mt--6 mb-2"
        ):
            with ui.column().classes("w-full p-3 pt-0"):
                with ui.row().classes("w-full items-center justify-end mb-1"):
                    ui.button(
                        _("Edit List"),
                        icon="edit",
                        on_click=lambda: open_significant_files_dialog(ctx),
                    ).props("flat dense size=sm color=primary")

                with ui.column().classes("w-full gap-1"):
                    for f in ctx.agent.current_fingerprint.significant_files:
                        ui.label(f).classes("text-sm font-mono text-blue-700 truncate")

    fields = ctx.agent.current_metadata.model_dump(exclude_unset=True)

    def create_expandable_text(text, key=None):
        with ui.column().classes(
            "w-full gap-0 bg-slate-50 border border-slate-100 rounded relative group pb-6"
        ):
            # Lock indicator
            if key:
                is_locked = key in ctx.agent.current_metadata.locked_fields

                async def toggle_lock(e, k=key):
                    if k in ctx.agent.current_metadata.locked_fields:
                        ctx.agent.current_metadata.locked_fields.remove(k)
                    else:
                        ctx.agent.current_metadata.locked_fields.append(k)
                    ctx.agent.save_state()
                    ctx.refresh("metadata")

                with (
                    ui.button(
                        icon="lock" if is_locked else "lock_open",
                        on_click=toggle_lock,
                    )
                    .props("flat dense")
                    .classes(
                        f"absolute top-1 right-1 z-10 opacity-0 group-hover:opacity-100 transition-opacity {'text-orange-600 opacity-100' if is_locked else 'text-slate-400'}"
                    )
                ):
                    ui.tooltip(
                        _("Lock field from AI updates")
                        if not is_locked
                        else _("Unlock field")
                    )

            if key == "description":
                md_text = "\n\n".join(text) if isinstance(text, list) else text
                content = ui.markdown(md_text).classes(
                    "px-3 py-2 text-sm text-gray-800 break-words overflow-hidden transition-all duration-300 cursor-pointer"
                )
                content.style(
                    "max-height: 100px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical;"
                )
            elif key == "keywords":
                kw_text = ", ".join(text) if isinstance(text, list) else text
                content = ui.markdown(kw_text).classes(
                    "px-2 py-0 text-sm text-gray-800 break-words overflow-hidden transition-all duration-300 cursor-pointer"
                )
                content.style("max-height: 110px; line-height: 1.5;")
            else:
                display_text = str(text)
                content = ui.markdown(display_text).classes(
                    "px-3 py-2 text-sm text-gray-800 break-words overflow-hidden transition-all duration-300 cursor-pointer"
                )
                content.style(
                    "max-height: 100px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical;"
                )

            if key:
                content.on("click", lambda: open_edit_dialog(ctx, key))

            if (
                (key == "description" and isinstance(text, list) and len(text) > 0)
                or (isinstance(text, list) and len(text) > 1)
                or len(str(text)) > 300
                or key in ["abstract", "notes"]
            ):

                def toggle(e, target=content):
                    is_expanded = target.style["max-height"] == "none"
                    if key == "description":
                        target.style(
                            f"max-height: {'100px' if is_expanded else 'none'}; -webkit-line-clamp: {'4' if is_expanded else 'unset'}"
                        )
                    elif key in ["abstract", "notes"] or not isinstance(text, list):
                        target.style(
                            f"max-height: {'100px' if is_expanded else 'none'}; -webkit-line-clamp: {'4' if is_expanded else 'unset'}"
                        )
                    else:
                        target.style(
                            f"max-height: {'110px' if is_expanded else 'none'}"
                        )
                    e.sender.text = _("more...") if is_expanded else _("less...")

                with ui.row().classes("w-full justify-end px-2 pb-1 absolute bottom-0"):
                    ui.button(_("more..."), on_click=toggle).props(
                        "flat dense color=primary"
                    ).classes("text-xs")
            else:
                content.style("max-height: none")

    with ui.column().classes("w-full gap-2"):
        for key, value in fields.items():
            if key == "locked_fields":
                continue
            if key == "authors" or key == "contacts":
                ui.label(key.replace("_", " ").title()).classes(
                    "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                )
                with ui.row().classes("w-full gap-1 flex-wrap items-center mt--1"):
                    for item in value:
                        if isinstance(item, dict):
                            name = item.get(
                                "name", item.get("person_to_contact", str(item))
                            )
                            name_clean = (
                                name.replace("{", "")
                                .replace("}", "")
                                .replace("\\", "")
                                .replace("orcidlink", "")
                            )
                            affiliation = item.get("affiliation", "")
                            identifier = item.get("identifier", "")
                            email = item.get("email", "")

                            bg_color = (
                                "bg-slate-100 border-slate-200"
                                if key == "authors"
                                else "bg-indigo-50 border-indigo-100 hover:bg-indigo-100"
                            )

                            with ui.label("").classes(
                                f"py-0.5 px-1.5 rounded {bg_color} border cursor-pointer text-sm inline-block mr-1 mb-1 relative group"
                            ) as container:
                                is_locked = (
                                    key in ctx.agent.current_metadata.locked_fields
                                )

                                async def toggle_lock_list(e, k=key):
                                    if k in ctx.agent.current_metadata.locked_fields:
                                        ctx.agent.current_metadata.locked_fields.remove(
                                            k
                                        )
                                    else:
                                        ctx.agent.current_metadata.locked_fields.append(
                                            k
                                        )
                                    ctx.agent.save_state()
                                    ctx.refresh("metadata")

                                with (
                                    ui.button(
                                        icon="lock" if is_locked else "lock_open",
                                        on_click=toggle_lock_list,
                                    )
                                    .props("flat dense")
                                    .classes(
                                        f"absolute -top-2 -right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity {'text-orange-600 opacity-100' if is_locked else 'text-slate-400'}"
                                    )
                                    .style(
                                        "font-size: 10px; background: white; border-radius: 50%; border: 1px solid #eee; width: 20px; height: 20px;"
                                    )
                                ):
                                    ui.tooltip(
                                        _("Lock field from AI updates")
                                        if not is_locked
                                        else _("Unlock field")
                                    )

                                container.on(
                                    "click",
                                    lambda _e, k=key: open_edit_dialog(ctx, k),
                                )

                                ui.label(name_clean).classes(
                                    "text-sm font-medium inline mr-1"
                                )
                                with ui.row().classes(
                                    "inline-flex items-center gap-0.5"
                                ):
                                    if identifier:
                                        ui.icon(
                                            "verified", size="0.75rem", color="green"
                                        ).classes("inline-block align-middle")
                                    if affiliation:
                                        ui.icon(
                                            "business", size="0.75rem", color="blue"
                                        ).classes("inline-block align-middle")
                                    if email:
                                        ui.icon(
                                            "email", size="0.75rem", color="indigo"
                                        ).classes("inline-block align-middle")

                                with ui.tooltip().classes(
                                    "bg-slate-800 text-white p-2 text-xs whitespace-normal max-w-xs"
                                ):
                                    ui.label(f"Name: {name_clean}")
                                    if affiliation:
                                        ui.label(f"Affiliation: {affiliation}")
                                    if identifier:
                                        ui.label(f"ORCID: {identifier}")
                                    if email:
                                        ui.label(f"Email: {email}")
                        else:
                            ui.label(str(item)).classes(
                                "text-sm bg-slate-50 p-1 rounded border border-slate-100 break-words"
                            )
            elif key == "description":
                ui.label(key.replace("_", " ").title()).classes(
                    "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                )
                with ui.column().classes("w-full gap-0 mt--1"):
                    create_expandable_text(value, key=key)
            elif key == "keywords":
                ui.label(key.replace("_", " ").title()).classes(
                    "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                )
                with ui.row().classes(
                    "w-full gap-1 flex-wrap items-center relative group mt--1"
                ) as kw_container:
                    is_locked = key in ctx.agent.current_metadata.locked_fields
                    kw_container.on("click", lambda _e, k=key: open_edit_dialog(ctx, k))

                    with (
                        ui.button(
                            icon="lock" if is_locked else "lock_open",
                            on_click=lambda _e, k=key: toggle_lock_list(_e, k),
                        )
                        .props("flat dense")
                        .classes(
                            f"absolute -top-4 right-0 z-10 opacity-0 group-hover:opacity-100 transition-opacity {'text-orange-600 opacity-100' if is_locked else 'text-slate-400'}"
                        )
                        .style(
                            "font-size: 10px; background: white; border-radius: 50%; border: 1px solid #eee; width: 20px; height: 20px;"
                        )
                    ):
                        ui.tooltip(
                            _("Lock field from AI updates")
                            if not is_locked
                            else _("Unlock field")
                        )

                    for kw in value:
                        ui.label(str(kw)).classes(
                            "text-sm bg-slate-100 py-0.5 px-2 rounded border border-slate-200 inline-block mr-1 mb-1"
                        )
            elif key == "related_publications":
                ui.label(key.replace("_", " ").title()).classes(
                    "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                )
                with ui.column().classes("w-full gap-1 items-start mt--1"):
                    for pub in value:
                        if isinstance(pub, dict):
                            title = pub.get("title", "Untitled")
                            rel_type = pub.get("relation_type", "")
                            id_type = pub.get("id_type", "")
                            id_val = pub.get("id_number", "")

                            if id_val:
                                id_val = id_val.replace("https://doi.org/", "")

                            with ui.label("").classes(
                                "py-1 px-1.5 rounded bg-blue-50 border border-blue-100 cursor-pointer hover:bg-blue-100 text-sm inline-block w-full relative group"
                            ) as pub_container:
                                is_locked = (
                                    key in ctx.agent.current_metadata.locked_fields
                                )
                                pub_container.on(
                                    "click", lambda _e, k=key: open_edit_dialog(ctx, k)
                                )

                                with (
                                    ui.button(
                                        icon="lock" if is_locked else "lock_open",
                                        on_click=lambda _e, k=key: toggle_lock_list(
                                            _e, k
                                        ),
                                    )
                                    .props("flat dense")
                                    .classes(
                                        f"absolute -top-2 -right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity {'text-orange-600 opacity-100' if is_locked else 'text-slate-400'}"
                                    )
                                    .style(
                                        "font-size: 10px; background: white; border-radius: 50%; border: 1px solid #eee; width: 20px; height: 20px;"
                                    )
                                ):
                                    ui.tooltip(
                                        _("Lock field from AI updates")
                                        if not is_locked
                                        else _("Unlock field")
                                    )

                                ui.label(title).classes(
                                    "text-sm font-medium break-words leading-tight"
                                )

                                with ui.tooltip().classes(
                                    "bg-slate-800 text-white p-2 text-xs whitespace-normal max-w-xs"
                                ):
                                    ui.label(f"Title: {title}")
                                    if rel_type:
                                        ui.label(f"Relation: {rel_type}")
                                    if id_type or id_val:
                                        label_prefix = (
                                            f"{id_type}:" if id_type else "DOI:"
                                        )
                                        ui.label(f"{label_prefix} {id_val or ''}")
            elif key == "software":
                ui.label(key.replace("_", " ").title()).classes(
                    "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                )
                with ui.row().classes(
                    "w-full gap-1 flex-wrap items-center relative group mt--1"
                ) as soft_container:
                    is_locked = key in ctx.agent.current_metadata.locked_fields
                    soft_container.on(
                        "click", lambda _e, k=key: open_edit_dialog(ctx, k)
                    )

                    with (
                        ui.button(
                            icon="lock" if is_locked else "lock_open",
                            on_click=lambda _e, k=key: toggle_lock_list(_e, k),
                        )
                        .props("flat dense")
                        .classes(
                            f"absolute -top-4 right-0 z-10 opacity-0 group-hover:opacity-100 transition-opacity {'text-orange-600 opacity-100' if is_locked else 'text-slate-400'}"
                        )
                        .style(
                            "font-size: 10px; background: white; border-radius: 50%; border: 1px solid #eee; width: 20px; height: 20px;"
                        )
                    ):
                        ui.tooltip(
                            _("Lock field from AI updates")
                            if not is_locked
                            else _("Unlock field")
                        )

                    for s in value:
                        # Handle both SoftwareInfo objects and dicts (from AI)
                        if isinstance(s, dict):
                            name = s.get("name", str(s))
                            version = s.get("version")
                        else:
                            # SoftwareInfo object
                            name = getattr(s, "name", str(s))
                            version = getattr(s, "version", None)

                        with ui.badge(name, color="purple-1").classes(
                            "text-purple-800 px-2 py-1 rounded-md cursor-help"
                        ):
                            if version:
                                ui.tooltip(f"Version: {version}")
                            else:
                                ui.tooltip(_("Version unknown"))
            elif key == "funding":
                ui.label(key.replace("_", " ").title()).classes(
                    "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                )
                with ui.row().classes(
                    "w-full gap-1 flex-wrap items-center mt--1"
                ) as fund_container:
                    is_locked = key in ctx.agent.current_metadata.locked_fields
                    fund_container.on(
                        "click", lambda _e, k=key: open_edit_dialog(ctx, k)
                    )

                    for f in value:
                        if isinstance(f, dict):
                            # Handle different key naming conventions (RODBUK vs Dataverse vs AI)
                            agency = f.get("funder_name", f.get("agency", ""))
                            award = f.get("award_title", "")
                            grant_id = f.get(
                                "grant_id",
                                f.get("grantnumber", f.get("grant_number", "")),
                            )

                            agency_name = agency if agency else award
                            if not agency_name:
                                agency_name = _("Funding")

                            display_title = (
                                f"{agency_name} ({grant_id})"
                                if grant_id
                                else agency_name
                            )

                            with ui.badge(display_title, color="amber-1").classes(
                                "text-amber-900 px-2 py-1 rounded-md cursor-help"
                            ):
                                with ui.tooltip().classes(
                                    "bg-slate-800 text-white p-2 text-xs max-w-xs"
                                ):
                                    if agency:
                                        ui.label(f"Funder: {agency}")
                                    if award:
                                        ui.label(f"Award: {award}")
                                    if grant_id:
                                        ui.label(f"Grant ID: {grant_id}")
            elif (
                key == "science_branches_mnisw"
                or key == "science_branches_oecd"
                or key == "languages"
            ):
                ui.label(key.replace("_", " ").title()).classes(
                    "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                )
                with ui.row().classes("w-full gap-1 flex-wrap items-center mt--1"):
                    for item in value:
                        ui.label(str(item)).classes(
                            "text-sm bg-slate-100 py-0.5 px-2 rounded border border-slate-200 inline-block mr-1 mb-1"
                        )
            # Fallback for other fields
            else:
                label_text = key.replace("_", " ").title()
                label_class = (
                    "text-[10px] font-bold text-slate-500 ml-1 uppercase tracking-wider"
                )

                # Special styling for Title
                if key == "title":
                    ui.label(_("Dataset Title")).classes(label_class)
                    with ui.column().classes("w-full mt--1 mb-2"):
                        with ui.column().classes(
                            "w-full gap-0 bg-white border border-slate-200 rounded-lg relative group shadow-sm p-3"
                        ):
                            # Lock indicator for title
                            is_locked = key in ctx.agent.current_metadata.locked_fields

                            async def toggle_lock_title(e, k=key):
                                if k in ctx.agent.current_metadata.locked_fields:
                                    ctx.agent.current_metadata.locked_fields.remove(k)
                                else:
                                    ctx.agent.current_metadata.locked_fields.append(k)
                                ctx.agent.save_state()
                                ctx.refresh("metadata")

                            with (
                                ui.button(
                                    icon="lock" if is_locked else "lock_open",
                                    on_click=toggle_lock_title,
                                )
                                .props("flat dense")
                                .classes(
                                    f"absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity {'text-orange-600 opacity-100' if is_locked else 'text-slate-400'}"
                                )
                            ):
                                ui.tooltip(_("Lock field from AI updates"))

                            content = ui.label(value).classes(
                                "text-lg font-bold text-slate-900 cursor-pointer m-0 p-0"
                            )
                            content.on("click", lambda: open_edit_dialog(ctx, key))
                    continue

                ui.label(label_text).classes(label_class)

                if isinstance(value, list):
                    with ui.column().classes("w-full gap-1 mt--1"):
                        for v_item in value:
                            create_expandable_text(str(v_item), key=key)
                else:
                    with ui.column().classes("w-full mt--1"):
                        create_expandable_text(str(value), key=key)


async def open_edit_dialog(ctx: AppContext, key: str):
    val = getattr(ctx.agent.current_metadata, key)

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
        ui.label(_("Edit {field}").format(field=key.replace("_", " ").title())).classes(
            "text-h6"
        )

        if isinstance(val, list):
            if val and not isinstance(val[0], str):
                current_text = yaml.dump(
                    [i.model_dump() if hasattr(i, "model_dump") else i for i in val],
                    allow_unicode=True,
                )
                edit_area = (
                    ui.textarea(value=current_text)
                    .classes("w-full font-mono text-xs")
                    .props("rows=15")
                )
                ui.markdown(_("Edit YAML structure for complex data.")).classes(
                    "text-xs text-slate-500"
                )
            else:
                if key == "description":
                    current_text = "\n\n".join(val) if val else ""
                    help_text = _(
                        "Enter one paragraph per block. Use double newlines to separate."
                    )
                else:
                    current_text = "\n".join(val) if val else ""
                    help_text = _("Enter one item per line.")

                edit_area = (
                    ui.textarea(value=current_text)
                    .classes("w-full")
                    .props("rows=10 auto-grow")
                )
                ui.markdown(help_text).classes("text-xs text-slate-500")
        else:
            edit_area = (
                ui.textarea(value=val or "").classes("w-full").props("rows=5 auto-grow")
            )

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button(_("Cancel"), on_click=dialog.close).props("flat")

            async def save_value():
                new_val = edit_area.value
                try:
                    if isinstance(val, list):
                        if val and not isinstance(val[0], str):
                            parsed_list = yaml.safe_load(new_val)
                            if not isinstance(parsed_list, list):
                                raise ValueError("YAML must be a list")
                            setattr(ctx.agent.current_metadata, key, parsed_list)
                        else:
                            if key == "description":
                                new_list = [
                                    p.strip()
                                    for p in re.split(r"\n\s*\n", new_val)
                                    if p.strip()
                                ]
                            else:
                                new_list = [
                                    line.strip()
                                    for line in new_val.split("\n")
                                    if line.strip()
                                ]
                            setattr(ctx.agent.current_metadata, key, new_list)
                    else:
                        setattr(ctx.agent.current_metadata, key, new_val)

                    if key not in ctx.agent.current_metadata.locked_fields:
                        ctx.agent.current_metadata.locked_fields.append(key)

                    ctx.agent.save_state()
                    dialog.close()
                    ctx.refresh("metadata")
                    ui.notify(
                        _("Field '{field}' updated and locked.").format(field=key)
                    )
                except Exception as e:
                    ui.notify(
                        _("Failed to save: {error}").format(error=str(e)),
                        type="negative",
                    )

            ui.button(_("Save"), on_click=save_value, color="primary")

    dialog.open()


async def handle_clear_metadata(ctx: AppContext):
    ctx.agent.clear_metadata()
    ctx.refresh("metadata")
    ui.notify(_("Metadata reset"))


async def open_significant_files_dialog(ctx: AppContext):
    """Dialog to manage the list of files selected for deep analysis."""
    if not ctx.agent.current_fingerprint:
        return

    with ui.dialog() as dialog, ui.card().classes("w-[600px]"):
        ui.label(_("Manage Significant Files")).classes("text-h6 mb-4")
        ui.markdown(
            _(
                "These files are used as context for AI analysis. You can add or remove files from this list."
            )
        )

        current_files = list(ctx.agent.current_fingerprint.significant_files)

        with ui.column().classes("w-full gap-2 mb-4"):
            file_list_container = ui.column().classes(
                "w-full border rounded p-2 max-h-60 overflow-y-auto"
            )

            def refresh_list():
                file_list_container.clear()
                with file_list_container:
                    if not current_files:
                        ui.label(_("No files selected.")).classes(
                            "text-slate-400 italic text-sm"
                        )
                    for f in current_files:
                        with ui.row().classes(
                            "w-full items-center justify-between hover:bg-slate-50 p-1 rounded"
                        ):
                            ui.label(f).classes("text-xs font-mono truncate flex-grow")
                            ui.button(
                                icon="delete",
                                on_click=lambda _e, path=f: remove_file(path),
                            ).props("flat dense color=red size=sm")

            def remove_file(path):
                if path in current_files:
                    current_files.remove(path)
                    refresh_list()

            refresh_list()

        new_file_input = (
            ui.input(label=_("Add file path (relative to root)"))
            .classes("w-full mb-4")
            .props("dense outlined")
        )

        def add_file():
            path = new_file_input.value.strip()
            if path and path not in current_files:
                current_files.append(path)
                new_file_input.value = ""
                refresh_list()

        ui.button(_("Add File"), on_click=add_file).classes("w-full mb-4").props(
            "outline"
        )

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button(_("Cancel"), on_click=dialog.close).props("flat")

            def save():
                ctx.agent.current_fingerprint.significant_files = current_files
                ctx.agent.save_state()
                ctx.refresh("metadata")
                dialog.close()
                ui.notify(_("Significant files updated."))

            ui.button(_("Save Changes"), on_click=save).props("elevated color=primary")

    dialog.open()
