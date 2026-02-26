"""
Model Selection Dialog Component

Displays a dialog when the configured AI model is invalid,
allowing the user to select a valid model from available options.
"""

from nicegui import ui
from opendata.i18n.translator import _
from opendata.ui.context import AppContext


def show_model_selection_dialog(ctx: AppContext, suggestion: dict):
    """
    Show a dialog allowing user to select a valid model.

    Args:
        ctx: Application context
        suggestion: Dict with 'current', 'available', 'suggested' keys
    """
    current_model = suggestion["current"]
    available_models = suggestion["available"]
    suggested_model = suggestion["suggested"]

    with ui.dialog() as dialog, ui.card().classes("w-96 p-6"):
        ui.label(_("Invalid AI Model Detected")).classes(
            "text-h5 font-bold text-red-600 mb-4"
        )

        ui.markdown(
            _(
                f"The configured model **`{current_model}`** is not available. "
                "Please select a valid model from the list:"
            )
        )

        model_select = (
            ui.select(
                options=available_models,
                value=suggested_model,
                label=_("Available Models"),
            )
            .props("outlined dense")
            .classes("w-full mb-4")
        )

        with ui.row().classes("w-full justify-end gap-2 mt-4"):

            async def apply_selection():
                """Apply the selected model."""
                await _apply_model_selection(ctx, model_select.value)
                dialog.close()

            ui.button(
                _("Use Selected Model"),
                on_click=apply_selection,
                color="primary",
            ).props("outline")

            async def skip_for_now():
                """Skip model selection (keep using invalid model)."""
                dialog.close()
                ui.notify(
                    _("Warning: AI features may not work with invalid model"),
                    type="warning",
                    timeout=5000,
                )

            ui.button(_("Skip for Now"), on_click=skip_for_now, color="grey")

    dialog.open()


async def _apply_model_selection(ctx: AppContext, model_name: str):
    """
    Apply the selected model and persist to settings.

    Args:
        ctx: Application context
        model_name: Selected model name
    """
    ctx.ai.switch_model(model_name)

    # Update settings based on provider
    if ctx.settings.ai_provider in ["google", "genai"]:
        ctx.settings.google_model = model_name
    elif ctx.settings.ai_provider == "openai":
        ctx.settings.openai_model = model_name

    # Persist settings
    ctx.wm.save_yaml(ctx.settings, "settings.yaml")

    # Update agent metadata if project is loaded
    if ctx.agent.project_id:
        ctx.agent.current_metadata.ai_model = model_name
        ctx.agent.save_state()

    ui.notify(
        _("Model switched to") + f": {model_name}",
        type="positive",
        timeout=3000,
    )


def check_and_show_model_dialog(ctx: AppContext):
    """
    Check if current model is invalid and show dialog if needed.

    Args:
        ctx: Application context
    """
    suggestion = ctx.ai.get_invalid_model_suggestion()
    if suggestion:
        show_model_selection_dialog(ctx, suggestion)
