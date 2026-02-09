from nicegui import ui
from opendata.i18n.translator import _, setup_i18n
from opendata.ui.state import ScanState
from opendata.ui.context import AppContext
from opendata.utils import get_local_ip


def render_settings_tab(ctx: AppContext):
    qr_dialog = ScanState.qr_dialog
    with ui.card().classes("w-full p-8 shadow-md"):
        ui.label(_("Application Settings")).classes("text-h4 q-mb-md font-bold")

        with ui.column().classes("w-full gap-6"):
            # Model Selection
            with ui.column().classes("gap-1"):
                ui.label(_("AI Model")).classes("text-sm font-bold text-slate-600")
                if ctx.ai.is_authenticated():
                    models = ctx.ai.list_available_models()

                    async def handle_model_change(e):
                        ctx.ai.switch_model(e.value)
                        if ctx.settings.ai_provider == "google":
                            ctx.settings.google_model = e.value
                        else:
                            ctx.settings.openai_model = e.value
                        ctx.wm.save_yaml(ctx.settings, "settings.yaml")
                        if ctx.agent.project_id:
                            ctx.agent.current_metadata.ai_model = e.value
                            ctx.agent.save_state()

                    ui.select(
                        options=models,
                        value=ctx.ai.model_name,
                        on_change=handle_model_change,
                    ).props("outlined dense behavior=menu").classes("w-full max-w-md")

            # Language
            with ui.column().classes("gap-1"):
                ui.label(_("Language")).classes("text-sm font-bold text-slate-600")
                with ui.row().classes("gap-2"):
                    ui.button("English", on_click=lambda: set_lang(ctx, "en")).props(
                        f"outline color={'primary' if ctx.settings.language == 'en' else 'grey'}"
                    ).classes("w-32")
                    ui.button("Polski", on_click=lambda: set_lang(ctx, "pl")).props(
                        f"outline color={'primary' if ctx.settings.language == 'pl' else 'grey'}"
                    ).classes("w-32")

            # Mobile
            with ui.column().classes("gap-1"):
                ui.label(_("Mobile Access")).classes("text-sm font-bold text-slate-600")
                ui.button(
                    _("Show QR Code"),
                    icon="qr_code_2",
                    on_click=lambda: qr_dialog.open() if qr_dialog else None,
                ).props("outline color=primary").classes("w-full max-w-md")

            ui.separator()

            # Auth
            if ctx.settings.ai_consent_granted:
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label(_("AI Session")).classes(
                        "text-sm font-bold text-slate-600"
                    )
                    ui.button(
                        _("Logout from AI"),
                        icon="logout",
                        on_click=lambda: confirm_logout(ctx),
                        color="red",
                    ).props("flat")


def render_setup_wizard(ctx: AppContext):
    with ui.card().classes("w-full max-w-xl p-8 shadow-xl border-t-4 border-primary"):
        ui.label(_("AI Configuration")).classes("text-h4 q-mb-md font-bold")
        with ui.tabs().classes("w-full") as tabs:
            google_tab = ui.tab("Google Gemini").classes("w-1/2")
            openai_tab = ui.tab("OpenAI / Ollama").classes("w-1/2")
        with ui.tab_panels(
            tabs,
            value="Google Gemini"
            if ctx.settings.ai_provider == "google"
            else "OpenAI / Ollama",
        ).classes("w-full"):
            with ui.tab_panel(google_tab):
                ui.markdown(
                    _(
                        "Uses **Google Gemini** (Recommended). No API keys needed—just sign in."
                    )
                )
                with ui.expansion(_("Security & Privacy FAQ"), icon="security").classes(
                    "bg-blue-50 q-mb-lg"
                ):
                    faq_items = [
                        _("Read-Only: We never modify your research files."),
                        _("Local: Analysis happens on your machine."),
                        _(
                            "Consent: We only send text snippets to AI with your permission."
                        ),
                    ]
                    ui.markdown("\n".join([f"- {item}" for item in faq_items]))
                ui.button(
                    _("Sign in with Google"),
                    icon="login",
                    on_click=lambda: handle_auth_provider(ctx, "google"),
                ).classes("w-full py-4 bg-primary text-white font-bold rounded-lg")
            with ui.tab_panel(openai_tab):
                ui.markdown(
                    _("Connect to **OpenAI**, **Ollama**, or compatible local APIs.")
                )
                api_key_input = ui.input(
                    label=_("API Key"),
                    password=True,
                    placeholder="sk-...",
                    value=ctx.settings.openai_api_key or "",
                ).classes("w-full")
                base_url_input = ui.input(
                    label=_("Base URL"),
                    placeholder="https://api.openai.com/v1",
                    value=ctx.settings.openai_base_url,
                ).classes("w-full")
                model_input = ui.input(
                    label=_("Model Name"),
                    placeholder="gpt-3.5-turbo",
                    value=ctx.settings.openai_model,
                ).classes("w-full")
                ui.markdown(
                    _(
                        "**Common Local URLs:**\n- Ollama: `http://localhost:11434/v1`\n- LocalAI: `http://localhost:8080/v1`"
                    )
                )

                async def save_openai():
                    ctx.settings.openai_api_key = api_key_input.value
                    ctx.settings.openai_base_url = base_url_input.value
                    ctx.settings.openai_model = model_input.value
                    ctx.settings.ai_provider = "openai"
                    await handle_auth_provider(ctx, "openai")

                ui.button(
                    _("Save & Connect"), icon="link", on_click=save_openai
                ).classes(
                    "w-full py-4 bg-secondary text-white font-bold rounded-lg q-mt-md"
                )


async def handle_auth_provider(ctx: AppContext, provider: str):
    setattr(ctx.settings, "ai_provider", provider)
    ctx.wm.save_yaml(ctx.settings, "settings.yaml")

    ctx.ai.reload_provider(ctx.settings)
    if ctx.ai.authenticate(silent=False):
        ctx.settings.ai_consent_granted = True
        ctx.wm.save_yaml(ctx.settings, "settings.yaml")
        ui.navigate.to("/")
    else:
        msg = _("Authorization failed.")
        if provider == "google":
            msg += " " + _("Please ensure client_secrets.json is present.")
        else:
            msg += " " + _("Could not connect to API.")
        ui.notify(msg, type="negative")


async def confirm_logout(ctx: AppContext):
    with ui.dialog() as dialog, ui.card().classes("p-4"):
        ui.label(_("Are you sure you want to logout from AI?")).classes("text-lg mb-4")
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button(_("Cancel"), on_click=dialog.close).props("flat")

            async def logout_action():
                dialog.close()
                await handle_logout(ctx)

            ui.button(_("Logout"), on_click=logout_action, color="red")
    dialog.open()


async def handle_logout(ctx: AppContext):
    ctx.ai.logout()
    ctx.settings.ai_consent_granted = False
    ctx.wm.save_yaml(ctx.settings, "settings.yaml")
    ui.notify(_("Logged out from AI"))
    ui.navigate.to("/")


def set_lang(ctx: AppContext, l):
    ctx.settings.language = l
    ctx.wm.save_yaml(ctx.settings, "settings.yaml")
    setup_i18n(l)
    ui.navigate.to("/")
