import os
import sys


def generate_spec(artifact_name, runner_os):
    spec_template = """# -*- mode: python ; coding: utf-8 -*-
import os

added_files = [
    ('src/opendata/ui', 'opendata/ui'),
    ('src/opendata/prompts', 'opendata/prompts')
]
if os.path.exists('client_secrets.json'):
    added_files.append(('client_secrets.json', '.'))

# General excludes to reduce size
general_excludes = [
    'tkinter', 'tcl', 'tk', 'unittest', 'test', 'distutils', 'pydoc'
]

a = Analysis(
    ['src/opendata/main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=['gi', 'gi.repository.Gtk', 'gi.repository.WebKit2'],
    hookspath=['pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=general_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Linux GUI stability fix: exclude problematic system libraries
if os.name == 'posix' and '{RUNNER_OS}' == 'Linux':
    excluded_libs = {
        'libglib-2.0.so.0', 'libgobject-2.0.so.0', 'libgio-2.0.so.0', 
        'libgmodule-2.0.so.0', 'libz.so.1', 'libsecret-1.so.0',
        'libwebkit2gtk-4.1.so.0', 'libjavascriptcoregtk-4.1.so.0',
        'libgtk-3.so.0', 'libgdk-3.so.0', 'libatk-1.0.so.0',
        'libpangocairo-1.0.so.0', 'libpango-1.0.so.0', 'libcairo.so.2'
    }
    a.binaries = [x for x in a.binaries if x[0] not in excluded_libs]

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{ARTIFACT_NAME}',
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
    content = spec_template.replace("{RUNNER_OS}", runner_os).replace(
        "{ARTIFACT_NAME}", artifact_name
    )

    with open("opendata.spec", "w") as f:
        f.write(content)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_spec.py <artifact_name> <runner_os>")
        sys.exit(1)
    generate_spec(sys.argv[1], sys.argv[2])
