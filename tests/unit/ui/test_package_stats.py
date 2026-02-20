"""
Tests for package tab inventory and selection statistics.

Ensures that the package tab displays the total inventory summary
and statistics for selected files.
"""

from unittest.mock import MagicMock, patch
import pytest
from opendata.ui.context import AppContext
from opendata.ui.components.package import render_package_tab


class TestPackageStats:
    """Test that package tab displays inventory and selection statistics."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock AppContext with inventory data."""
        ctx = MagicMock(spec=AppContext)
        ctx.agent = MagicMock()
        ctx.agent.project_id = "test-project"
        ctx.agent.current_analysis = None

        ctx.session = MagicMock()
        ctx.session.last_inventory_project = "test-project"
        ctx.session.is_loading_inventory = False
        ctx.session.show_suggestions_banner = False
        ctx.session.show_only_included = False

        # Mock inventory cache with some files
        ctx.session.inventory_cache = [
            {"path": "file1.txt", "size": 1024, "included": True, "type": "file"},
            {"path": "file2.txt", "size": 2048, "included": False, "type": "file"},
            {"path": "file3.txt", "size": 4096, "included": True, "type": "file"},
        ]

        ctx.main_tabs = MagicMock()
        return ctx

    def test_package_tab_displays_total_inventory_count(self, mock_ctx):
        """Package tab should display total number of files in inventory."""
        with patch("opendata.ui.components.package.ui") as mock_ui:
            # We need to mock the context managers used in render_package_tab
            mock_ui.column.return_value.__enter__ = MagicMock()
            mock_ui.row.return_value.__enter__ = MagicMock()
            mock_ui.card.return_value.__enter__ = MagicMock()

            render_package_tab(mock_ctx)

            # Check if total count (3 files) is mentioned in any label
            # Current implementation only shows included count (2 files)
            # We want it to show something like "Total: 3 files"
            calls = [
                call[0][0] for call in mock_ui.label.call_args_list if len(call[0]) > 0
            ]
            assert any(
                "Total: 3 files" in str(c) or "3 files in inventory" in str(c)
                for c in calls
            )

    def test_package_tab_displays_selection_ratio(self, mock_ctx):
        """Package tab should display ratio of selected files."""
        with patch("opendata.ui.components.package.ui") as mock_ui:
            mock_ui.column.return_value.__enter__ = MagicMock()
            mock_ui.row.return_value.__enter__ = MagicMock()

            render_package_tab(mock_ctx)

            calls = [
                call[0][0] for call in mock_ui.label.call_args_list if len(call[0]) > 0
            ]
            # Should show something like "Selected: 2/3 files"
            assert any("2/3" in str(c) for c in calls)
