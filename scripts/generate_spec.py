import os
import sys
import json
from pathlib import Path


def generate_spec(artifact_name, runner_os):
    # Get the project root directory (current working directory in CI)
    root = Path.cwd().absolute()

    # 1. Bake in secrets if present in environment
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    if client_id and client_secret:
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
        with open(root / "client_secrets.json", "w") as f:
            json.dump(secrets_config, f)
        print(f"[INFO] client_secrets.json created at {root}")

    # Define resource paths relative to project root
    ui_path = root / "src" / "opendata" / "ui"
    prompts_path = root / "src" / "opendata" / "prompts"
    secrets_file = root / "client_secrets.json"

    # Construction of datas list for PyInstaller
    added_files = [
        (str(ui_path), "opendata/ui"),
        (str(prompts_path), "opendata/prompts"),
    ]

    if secrets_file.exists():
        added_files.append((str(secrets_file), "."))

    # General excludes to reduce size - REMOVED unittest as it's needed by pyparsing
    general_excludes = ["tkinter", "tcl", "tk", "test", "distutils", "pydoc"]

    spec_template = f"""# -*- mode: python ; coding: utf-8 -*-
import os

added_files = {added_files}

a = Analysis(
    ['src/opendata/main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=['gi', 'gi.repository.Gtk', 'gi.repository.WebKit2'],
    hookspath=['pyinstaller_hooks'],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={general_excludes},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Linux GUI stability fix: exclude problematic system libraries
if os.name == 'posix' and '{runner_os}' == 'Linux':
    excluded_libs = {{
        'libglib-2.0.so.0', 'libgobject-2.0.so.0', 'libgio-2.0.so.0', 
        'libgmodule-2.0.so.0', 'libz.so.1', 'libsecret-1.so.0',
        'libwebkit2gtk-4.1.so.0', 'libjavascriptcoregtk-4.1.so.0',
        'libgtk-3.so.0', 'libgdk-3.so.0', 'libatk-1.0.so.0',
        'libpangocairo-1.0.so.0', 'libpango-1.0.so.0', 'libcairo.so.2',
        'libmount.so.1', 'libblkid.so.1', 'libuuid.so.1', 'libselinux.so.1'
    }}
    a.binaries = [x for x in a.binaries if x[0] not in excluded_libs]

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{artifact_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
    with open(root / "opendata.spec", "w") as f:
        f.write(spec_template)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_spec.py <artifact_name> <runner_os>")
        sys.exit(1)
    generate_spec(sys.argv[1], sys.argv[2])
