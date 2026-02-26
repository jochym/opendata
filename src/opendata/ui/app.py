import asyncio
import time
import logging
import uvicorn
from pathlib import Path
from nicegui import app, ui
from opendata.utils import get_local_ip
from opendata.workspace import WorkspaceManager
from opendata.packager import PackagingService
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.ai.service import AIService
from opendata.protocols.manager import ProtocolManager
from opendata.packaging.manager import PackageManager
from opendata.i18n.translator import setup_i18n, _

from opendata.ui.state import UIState, ScanState
from opendata.ui.context import AppContext
from opendata.ui.components import (
    header_content_ui,
    render_analysis_dashboard,
    chat_messages_ui,
    metadata_preview_ui,
    render_protocols_tab,
    render_package_tab,
    render_settings_tab,
    render_setup_wizard,
    render_preview_and_build,
    check_and_show_model_dialog,
)

logger = logging.getLogger("opendata.ui")


def start_ui(host: str = "127.0.0.1", port: int = 8080, enable_api: bool = False):
    """Start the NiceGUI application server.

    Note: When running in a multiprocessing child process, NiceGUI's ui.run()
    returns early by design (see nicegui.ui_run line 165-166). We handle this
    by manually starting uvicorn if the app wasn't started.

    Args:
        host: Host address to bind the server to (default: 127.0.0.1)
        port: Port number to bind the server to (default: 8080)
        enable_api: Enable REST API endpoints for test automation (default: False)
    """
    # 1. Initialize Backend
    wm = WorkspaceManager()
    settings = wm.get_settings()
    setup_i18n(settings.language)

    agent = ProjectAnalysisAgent(wm)
    ai = AIService(Path(settings.workspace_path), settings)
    pm = ProtocolManager(wm)
    pkg_mgr = PackageManager(wm)
    packaging_service = PackagingService(Path(settings.workspace_path))

    ctx = AppContext(
        wm=wm,
        agent=agent,
        ai=ai,
        pm=pm,
        pkg_mgr=pkg_mgr,
        packaging_service=packaging_service,
        settings=settings,
        port=port,
    )

    # Initialize model from global settings
    if settings.ai_provider in ["google", "genai"] and settings.google_model:
        ai.switch_model(settings.google_model)
    elif settings.ai_provider == "openai" and settings.openai_model:
        ai.switch_model(settings.openai_model)

    ai.authenticate(silent=True)

    # Note: We used to do auto-fix here, but now we rely on
    # check_and_show_model_dialog(ctx) inside index() to show a proper
    # selection dialog to the user.

    # --- REFRESH LOGIC ---
    ctx.session._is_refreshing_global = False

    def refresh_all():
        if ctx.session._is_refreshing_global:
            return

        now = time.time()
        if now - ctx.session.last_refresh_time < 0.5:
            return

        ctx.session.last_refresh_time = now
        ctx.session._is_refreshing_global = True
        try:
            # Thread-safe refresh calls
            ctx.refresh("chat")
            ctx.refresh("metadata")
            ctx.refresh("header")
            ctx.refresh("preview")
            ctx.refresh("protocols")
            ctx.refresh("package")
            ctx.refresh("significant_files_editor")
            ctx.refresh("inventory_selector")
        except Exception as e:
            logger.error(f"Refresh error: {e}")
        finally:
            ctx.session._is_refreshing_global = False

    ctx.refresh_all = refresh_all

    ctx.refresh_all = refresh_all

    # Register API endpoints for test automation (only if enabled)
    if enable_api:
        from opendata.api import register_project_api

        register_project_api(ctx)
        logger.info(
            f"✅ API endpoints ENABLED (localhost:{port}) - For test automation"
        )
    else:
        logger.info(f"🔒 API endpoints DISABLED (use --api flag to enable)")

    @ui.page("/")
    def index():
        setup_i18n(settings.language)

        ui.add_head_html("""
            <style>
                .nicegui-content { padding: 4px !important; }
                /* Force Quasar textarea to fill its container */
                .q-textarea.h-full,
                .q-textarea.h-full .q-field__control,
                .q-textarea.h-full .q-field__control-container,
                .q-textarea.h-full .q-field__native {
                    height: 100% !important;
                }
                .q-textarea.h-full .q-field__native {
                    resize: none !important;
                }
            </style>
        """)
        ui.query("body").style("background-color: #f8f9fa; margin: 0; padding: 0;")
        ui.query("html").style("margin: 0; padding: 0;")

        # QR Dialog for mobile
        with ui.dialog() as qr_dialog, ui.card().classes("p-6 items-center"):
            ui.label(_("Continue on Mobile")).classes("text-h6 q-mb-md")
            url = f"http://{get_local_ip()}:{port}"
            ui.interactive_image(
                f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url}"
            )
            ui.label(url).classes("text-caption text-slate-500 q-mt-md")
            ui.button(_("Close"), on_click=qr_dialog.close).props("flat")

        ScanState.qr_dialog = qr_dialog

        with ui.header().classes(
            "bg-slate-800 text-white py-2 px-4 justify-between items-center shadow-lg"
        ):
            # Register refreshable header
            ctx.register_refreshable("header", header_content_ui)
            header_content_ui(ctx)

            with ui.tabs().classes("bg-slate-800") as main_tabs:
                analysis_tab = ui.tab(_("Analysis"), icon="analytics")
                protocols_tab = ui.tab(_("Protocols"), icon="rule")
                package_tab = ui.tab(_("Package"), icon="inventory_2")
                preview_tab = ui.tab(_("Preview"), icon="visibility")
                settings_tab = ui.tab(_("Settings"), icon="settings")

                ctx.main_tabs = main_tabs
                ctx.analysis_tab = analysis_tab
                ctx.package_tab = package_tab
                ctx.preview_tab = preview_tab

                # Sync to UIState for global access in callbacks
                UIState.main_tabs = main_tabs
                UIState.analysis_tab = analysis_tab
                UIState.package_tab = package_tab
                UIState.preview_tab = preview_tab

        container = ui.column().classes("w-full p-0 max-w-none mx-0 h-full")
        with container:
            if not settings.ai_consent_granted:
                render_setup_wizard(ctx)
            else:
                # Check for invalid model and show dialog if needed
                check_and_show_model_dialog(ctx)

                with ui.tab_panels(main_tabs, value=analysis_tab).classes(
                    "w-full bg-transparent p-0 h-full"
                ):
                    with ui.tab_panel(analysis_tab).classes("p-0 h-full"):
                        # Analysis Dashboard manages its own refreshables (chat/metadata)
                        ctx.register_refreshable("chat", chat_messages_ui)
                        ctx.register_refreshable("metadata", metadata_preview_ui)
                        render_analysis_dashboard(ctx)

                    with ui.tab_panel(protocols_tab).classes("p-0 h-full"):
                        ctx.register_refreshable("protocols", render_protocols_tab)
                        render_protocols_tab(ctx)

                    with ui.tab_panel(package_tab).classes("p-0 h-full"):
                        ctx.register_refreshable("package", render_package_tab)
                        render_package_tab(ctx)

                    with ui.tab_panel(preview_tab).classes("p-0 h-full"):
                        ctx.register_refreshable("preview", render_preview_and_build)
                        render_preview_and_build(ctx)

                    with ui.tab_panel(settings_tab):
                        render_settings_tab(ctx)

    # Initialize NiceGUI app (completes setup even in child processes)
    ui.run(title="OpenData Agent", port=port, show=False, reload=False, host=host)

    # Start server manually if ui.run() returned early (multiprocessing child)
    if not app.is_started:
        uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_ui()
