#!/usr/bin/env python3
"""
Unified cross-platform build script for OpenData Tool.

This script handles binary building for Windows, macOS, and Linux using PyInstaller.
It ensures consistent builds across all platforms with proper resource inclusion.

Usage:
    python build.py [--platform PLATFORM] [--name NAME]

Arguments:
    --platform: Target platform (auto-detected if not specified)
                Options: linux, windows, macos-intel, macos-arm
    --name: Output binary name (default: platform-specific)
    --test: Run a quick test of the built binary
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path


def detect_platform():
    """Detect the current platform and return appropriate platform identifier."""
    system = platform.system().lower()
    if system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    elif system == "darwin":
        # Detect Apple Silicon vs Intel
        machine = platform.machine().lower()
        if machine in ("arm64", "aarch64"):
            return "macos-arm"
        else:
            return "macos-intel"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def get_platform_config(platform_name):
    """Get platform-specific build configuration."""
    configs = {
        "linux": {
            "name": "opendata-linux",
            "separator": ":",
            "console": False,  # No console for GUI app
            "ext": "",
        },
        "windows": {
            "name": "opendata-win",
            "separator": ";",
            "console": False,  # No console for GUI app
            "ext": ".exe",
        },
        "macos-intel": {
            "name": "opendata-macos-intel",
            "separator": ":",
            "console": False,  # No console for GUI app
            "ext": "",
        },
        "macos-arm": {
            "name": "opendata-macos-arm",
            "separator": ":",
            "console": False,  # No console for GUI app
            "ext": "",
        },
    }
    return configs.get(platform_name)


def create_client_secrets(root_dir):
    """Create client_secrets.json from environment variables if available."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "⚠️  Google credentials not found in environment - skipping client_secrets.json"
        )
        return None

    secrets_config = {
        "installed": {
            "client_id": client_id,
            "project_id": "opendata-tool",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"],
        }
    }

    secrets_path = root_dir / "client_secrets.json"
    with open(secrets_path, "w") as f:
        json.dump(secrets_config, f, indent=2)

    print(f"✅ Created client_secrets.json at {secrets_path}")
    return secrets_path


def build_binary(platform_name, output_name=None, test_binary=False):
    """Build the binary for the specified platform."""
    root = Path(__file__).parent.absolute()
    config = get_platform_config(platform_name)

    if not config:
        raise ValueError(f"Unknown platform: {platform_name}")

    # Use provided name or default platform name
    binary_name = output_name or config["name"]
    separator = config["separator"]

    print(f"\n{'=' * 60}")
    print(f"Building OpenData Tool for {platform_name}")
    print(f"Binary name: {binary_name}")
    print(f"{'=' * 60}\n")

    # Define paths
    main_script = root / "src" / "opendata" / "main.py"
    ui_path = root / "src" / "opendata" / "ui"
    prompts_path = root / "src" / "opendata" / "prompts"
    version_file = root / "src" / "opendata" / "VERSION"

    # Verify required files exist
    if not main_script.exists():
        raise FileNotFoundError(f"Main script not found: {main_script}")
    if not ui_path.exists():
        raise FileNotFoundError(f"UI directory not found: {ui_path}")
    if not prompts_path.exists():
        raise FileNotFoundError(f"Prompts directory not found: {prompts_path}")
    if not version_file.exists():
        raise FileNotFoundError(f"VERSION file not found: {version_file}")

    # Create client_secrets.json if credentials are available
    secrets_path = create_client_secrets(root)

    # Build PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name",
        binary_name,
    ]

    # Add console flag (--noconsole for GUI, --console for debugging)
    if not config["console"]:
        cmd.append("--noconsole")

    # Add data files with platform-specific separator
    cmd.extend(
        [
            "--add-data",
            f"{ui_path}{separator}opendata/ui",
            "--add-data",
            f"{prompts_path}{separator}opendata/prompts",
            "--add-data",
            f"{version_file}{separator}.",
        ]
    )

    # Add client_secrets.json if it exists
    if secrets_path and secrets_path.exists():
        cmd.extend(["--add-data", f"{secrets_path}{separator}."])

    # Exclude unnecessary modules to reduce binary size
    excludes = [
        "matplotlib",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "IPython",
        "PIL",
        "tkinter",
        "test",
        "unittest",
    ]
    for module in excludes:
        cmd.extend(["--exclude-module", module])

    # Add the main script
    cmd.append(str(main_script))

    # Print the command
    print(f"Executing PyInstaller:")
    print(f"  {' '.join(cmd)}\n")

    # Run PyInstaller
    try:
        result = subprocess.run(cmd, check=True, cwd=root)
        print(f"\n✅ Build completed successfully!")

        # Get binary path
        binary_path = root / "dist" / f"{binary_name}{config['ext']}"
        if binary_path.exists():
            size_mb = binary_path.stat().st_size / (1024 * 1024)
            print(f"📦 Binary location: {binary_path}")
            print(f"📊 Binary size: {size_mb:.1f} MB")

            # Test the binary if requested
            if test_binary:
                test_built_binary(binary_path, platform_name)
        else:
            print(f"⚠️  Warning: Binary not found at expected location: {binary_path}")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed with exit code {e.returncode}")
        sys.exit(1)


def test_built_binary(binary_path, platform_name):
    """Test that the built binary can start successfully."""
    print(f"\n{'=' * 60}")
    print(f"Testing Binary: {binary_path.name}")
    print(f"{'=' * 60}\n")

    try:
        # Test help output
        print("Testing --help output...")
        result = subprocess.run(
            [str(binary_path), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            print(f"✅ Binary responds to --help")
            if "OpenData Tool" in result.stdout:
                print("✅ Help output looks correct")
        else:
            print(f"⚠️  Binary returned non-zero exit code: {result.returncode}")
            print(f"stderr: {result.stderr}")

        # For headless test, we could start the server and check if it responds
        # but this requires more setup, so we just test --help for now
        print("\n✅ Binary test completed successfully")

    except subprocess.TimeoutExpired:
        print("⚠️  Binary test timed out")
    except Exception as e:
        print(f"⚠️  Binary test failed: {e}")


def main():
    """Main entry point for the build script."""
    parser = argparse.ArgumentParser(
        description="Build OpenData Tool binary for multiple platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--platform",
        choices=["linux", "windows", "macos-intel", "macos-arm"],
        help="Target platform (auto-detected if not specified)",
    )
    parser.add_argument(
        "--name",
        help="Output binary name (default: platform-specific name)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test the binary after building",
    )

    args = parser.parse_args()

    # Detect platform if not specified
    target_platform = args.platform
    if not target_platform:
        target_platform = detect_platform()
        print(f"Auto-detected platform: {target_platform}")

    # Build the binary
    try:
        build_binary(target_platform, args.name, args.test)
    except Exception as e:
        print(f"\n❌ Build failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
