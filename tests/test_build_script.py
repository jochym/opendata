"""
Tests for the unified build.py script.

These tests ensure the build script works correctly across all platforms.
"""

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from build import detect_platform, get_platform_config, create_client_secrets


def test_detect_platform_linux():
    """Test platform detection on Linux."""
    with mock.patch("platform.system", return_value="Linux"):
        assert detect_platform() == "linux"


def test_detect_platform_windows():
    """Test platform detection on Windows."""
    with mock.patch("platform.system", return_value="Windows"):
        assert detect_platform() == "windows"


def test_detect_platform_macos_arm():
    """Test platform detection on macOS with Apple Silicon."""
    with mock.patch("platform.system", return_value="Darwin"):
        with mock.patch("platform.machine", return_value="arm64"):
            assert detect_platform() == "macos-arm"


def test_detect_platform_macos_intel():
    """Test platform detection on macOS with Intel."""
    with mock.patch("platform.system", return_value="Darwin"):
        with mock.patch("platform.machine", return_value="x86_64"):
            assert detect_platform() == "macos-intel"


def test_get_platform_config_linux():
    """Test platform configuration for Linux."""
    config = get_platform_config("linux")
    assert config["name"] == "opendata-linux"
    assert config["separator"] == ":"
    assert config["console"] is False
    assert config["ext"] == ""


def test_get_platform_config_windows():
    """Test platform configuration for Windows."""
    config = get_platform_config("windows")
    assert config["name"] == "opendata-win"
    assert config["separator"] == ";"
    assert config["console"] is False
    assert config["ext"] == ".exe"


def test_get_platform_config_macos_intel():
    """Test platform configuration for macOS Intel."""
    config = get_platform_config("macos-intel")
    assert config["name"] == "opendata-macos-intel"
    assert config["separator"] == ":"
    assert config["console"] is False
    assert config["ext"] == ""


def test_get_platform_config_macos_arm():
    """Test platform configuration for macOS ARM."""
    config = get_platform_config("macos-arm")
    assert config["name"] == "opendata-macos-arm"
    assert config["separator"] == ":"
    assert config["console"] is False
    assert config["ext"] == ""


def test_get_platform_config_invalid():
    """Test that invalid platform returns None."""
    config = get_platform_config("invalid-platform")
    assert config is None


def test_create_client_secrets_with_credentials(tmp_path):
    """Test creating client_secrets.json with credentials."""
    with mock.patch.dict(
        os.environ,
        {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-secret",
        },
    ):
        secrets_path = create_client_secrets(tmp_path)
        
        assert secrets_path is not None
        assert secrets_path.exists()
        
        # Verify content
        import json
        with open(secrets_path) as f:
            data = json.load(f)
        
        assert "installed" in data
        assert data["installed"]["client_id"] == "test-client-id"
        assert data["installed"]["client_secret"] == "test-secret"
        assert data["installed"]["project_id"] == "opendata-tool"


def test_create_client_secrets_without_credentials(tmp_path):
    """Test that create_client_secrets returns None without credentials."""
    with mock.patch.dict(os.environ, {}, clear=True):
        secrets_path = create_client_secrets(tmp_path)
        assert secrets_path is None


def test_required_files_exist():
    """Test that all required files for building exist."""
    root = project_root
    
    # Check main script
    assert (root / "src" / "opendata" / "main.py").exists()
    
    # Check ui directory
    assert (root / "src" / "opendata" / "ui").is_dir()
    
    # Check prompts directory
    assert (root / "src" / "opendata" / "prompts").is_dir()
    
    # Check VERSION file
    assert (root / "src" / "opendata" / "VERSION").exists()
    
    # Check build.py itself
    assert (root / "build.py").exists()


def test_all_platforms_have_valid_config():
    """Test that all supported platforms have valid configurations."""
    platforms = ["linux", "windows", "macos-intel", "macos-arm"]
    
    for platform in platforms:
        config = get_platform_config(platform)
        
        assert config is not None, f"Config for {platform} is None"
        assert "name" in config, f"Config for {platform} missing 'name'"
        assert "separator" in config, f"Config for {platform} missing 'separator'"
        assert "console" in config, f"Config for {platform} missing 'console'"
        assert "ext" in config, f"Config for {platform} missing 'ext'"
        
        # Validate separator
        assert config["separator"] in [":", ";"], f"Invalid separator for {platform}"
        
        # Validate console is boolean
        assert isinstance(config["console"], bool), f"Console for {platform} not a boolean"


def test_build_script_is_executable():
    """Test that build.py is executable."""
    build_script = project_root / "build.py"
    
    # Check it has a shebang
    with open(build_script) as f:
        first_line = f.readline()
    
    assert first_line.startswith("#!/usr/bin/env python"), "Missing shebang"


def test_backward_compatibility_script_exists():
    """Test that build_dist.py exists for backward compatibility."""
    assert (project_root / "build_dist.py").exists()


def test_documentation_exists():
    """Test that build documentation exists."""
    assert (project_root / "docs" / "BUILDING.md").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
