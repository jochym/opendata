"""Test for the bug report button in the header."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.workspace import WorkspaceManager


@pytest.fixture
def mock_wm(tmp_path):
    """Create a temporary workspace manager."""
    wm = WorkspaceManager(base_path=tmp_path)
    return wm


@pytest.fixture
def agent(mock_wm):
    """Create a project analysis agent with temporary workspace."""
    return ProjectAnalysisAgent(wm=mock_wm)


class TestHeaderBugReportButton:
    """Test the bug report button functionality in the header."""

    def test_handle_bug_report_generates_pending_report(self, agent, tmp_path):
        """handle_bug_report triggers bug report generation."""
        from opendata.ui.components.header import handle_bug_report

        # Setup: Configure agent and context
        agent.project_id = "test-project"
        agent.wm.bug_reports_dir = tmp_path

        # Mock context
        ctx = Mock()
        ctx.agent = agent
        ctx.settings = Mock()
        ctx.settings.github_bug_report_token = None
        ctx.wm = agent.wm
        ctx.refresh_all = Mock()

        # Call the handler
        import asyncio

        asyncio.run(handle_bug_report(ctx))

        # Verify: The pending bug report was consumed (set to None)
        # and dialog was shown
        assert (
            not hasattr(agent, "_pending_bug_report")
            or agent._pending_bug_report is None
        )

    def test_handle_bug_report_fallback_creates_basic_report(self, agent, tmp_path):
        """handle_bug_report creates fallback report if _pending_bug_report is not set."""
        from opendata.ui.components.header import handle_bug_report
        from opendata.utils import get_app_version
        import platform
        import sys

        # Setup: Ensure no pending report exists
        agent._pending_bug_report = None
        agent.project_id = "test-project"
        agent.wm.bug_reports_dir = tmp_path

        # Mock context
        ctx = Mock()
        ctx.agent = agent
        ctx.settings = Mock()
        ctx.settings.github_bug_report_token = None
        ctx.wm = agent.wm
        ctx.refresh_all = Mock()

        # Track what was passed to show_bug_report_dialog
        dialog_args = {}

        def capture_dialog_args(context, report):
            dialog_args["report"] = report

        # Mock the dialog function to capture arguments
        with patch(
            "opendata.ui.components.bug_report_dialog.show_bug_report_dialog"
        ) as mock_dialog:
            mock_dialog.side_effect = capture_dialog_args

            # Call the handler
            import asyncio

            asyncio.run(handle_bug_report(ctx))

        # Verify: Basic report was created
        assert "report" in dialog_args
        report = dialog_args["report"]
        assert "title" in report
        assert "system_body" in report
        assert "OS:" in report["system_body"]
        assert "Python:" in report["system_body"]
        assert "App Version:" in report["system_body"]

    def test_handle_bug_report_generates_fresh_report(self, agent, tmp_path):
        """handle_bug_report always generates a fresh bug report via _handle_bug_command."""
        from opendata.ui.components.header import handle_bug_report

        # Setup
        agent.project_id = "test-project"
        agent.wm.bug_reports_dir = tmp_path

        # Mock context
        ctx = Mock()
        ctx.agent = agent
        ctx.settings = Mock()
        ctx.settings.github_bug_report_token = None
        ctx.wm = agent.wm
        ctx.refresh_all = Mock()

        # Track what was passed to show_bug_report_dialog
        dialog_args = {}

        def capture_dialog_args(context, report):
            dialog_args["report"] = report

        # Mock the dialog function to capture arguments
        with patch(
            "opendata.ui.components.bug_report_dialog.show_bug_report_dialog"
        ) as mock_dialog:
            mock_dialog.side_effect = capture_dialog_args

            # Call the handler
            import asyncio

            asyncio.run(handle_bug_report(ctx))

        # Verify: A fresh report was generated
        assert "report" in dialog_args
        report = dialog_args["report"]
        assert "title" in report
        assert "system_body" in report
        assert "extra_files" in report
        # Verify YAML file was created
        assert len(report["extra_files"]) > 0
        assert Path(report["extra_files"][0]).exists()
        assert report["extra_files"][0].endswith(".yaml")

        # Verify: Pending report was cleared after consumption
        assert agent._pending_bug_report is None
