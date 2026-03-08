"""
Tests for folder toggling logic in the package tab.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import os
from opendata.ui.components.package import toggle_folder
from opendata.models import PackageManifest


@pytest.mark.asyncio
async def test_toggle_folder_recursive_windows_separators():
    """
    Test that toggle_folder correctly matches sub-paths using Windows separators
    when running on a system where os.sep is '\\'.
    """
    # 1. Arrange
    ctx = MagicMock()
    ctx.agent.project_id = "test-project"

    manifest = PackageManifest(project_id="test-project")
    ctx.pkg_mgr.get_manifest.return_value = manifest

    # Simulate an inventory that might have been scanned on Windows
    # (using backslashes in paths)
    ctx.session.inventory_cache = [
        {"path": "data\\file1.txt", "size": 100},
        {"path": "data\\subdir\\file2.txt", "size": 200},
        {"path": "other\\file3.txt", "size": 300},
        {"path": "data", "size": 0},  # The folder itself
    ]

    # 2. Act
    # Mock os.sep to be '\\' (Windows style)
    with (
        patch("os.sep", "\\"),
        patch(
            "opendata.ui.components.package.load_inventory_background",
            new_callable=AsyncMock,
        ) as mock_load,
        patch("opendata.ui.components.package.ui.notify") as mock_notify,
    ):
        # Toggle 'data' folder from unchecked to checked
        await toggle_folder(ctx, "data", "unchecked")

        # 3. Assert
        # Should include: data, data\file1.txt, data\subdir\file2.txt
        # Should NOT include: other\file3.txt
        assert "data" in manifest.force_include
        assert "data\\file1.txt" in manifest.force_include
        assert "data\\subdir\\file2.txt" in manifest.force_include
        assert "other\\file3.txt" not in manifest.force_include

        assert (
            len(manifest.force_include) == 3
        )  # data, data\file1.txt, data\subdir\file2.txt
        # Wait, the folder itself is also in the inventory in this mock
        # Let's check the logic: p == folder_path or p.startswith(folder_prefix)
        # If folder_path is "data", and sep is "\\", folder_prefix is "data\\"
        # p="data" matches p == folder_path
        # p="data\\file1.txt" matches p.startswith("data\\")

        mock_load.assert_called_once_with(ctx)


@pytest.mark.asyncio
async def test_toggle_folder_recursive_posix_separators():
    """
    Test that toggle_folder correctly matches sub-paths using POSIX separators.
    """
    # 1. Arrange
    ctx = MagicMock()
    ctx.agent.project_id = "test-project"

    manifest = PackageManifest(project_id="test-project")
    ctx.pkg_mgr.get_manifest.return_value = manifest

    ctx.session.inventory_cache = [
        {"path": "data/file1.txt", "size": 100},
        {"path": "data/subdir/file2.txt", "size": 200},
        {"path": "other/file3.txt", "size": 300},
        {"path": "data", "size": 0},
    ]

    # 2. Act
    # Mock os.sep to be '/' (POSIX style)
    with (
        patch("os.sep", "/"),
        patch(
            "opendata.ui.components.package.load_inventory_background",
            new_callable=AsyncMock,
        ) as mock_load,
        patch("opendata.ui.components.package.ui.notify") as mock_notify,
    ):
        await toggle_folder(ctx, "data", "unchecked")

        # 3. Assert
        assert "data" in manifest.force_include
        assert "data/file1.txt" in manifest.force_include
        assert "data/subdir/file2.txt" in manifest.force_include
        assert "other/file3.txt" not in manifest.force_include

        mock_load.assert_called_once_with(ctx)
