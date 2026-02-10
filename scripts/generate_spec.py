import os
import sys


def generate_spec(artifact_name, runner_os):
    data_sep = ";" if runner_os == "Windows" else ":"

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None
added_files = [('src/opendata/ui', 'opendata/ui')]
if os.path.exists('client_secrets.json'):
    added_files.append(('client_secrets.json', '.'))

a = Analysis(
    ['src/opendata/main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=['gi', 'gi.repository.Gtk', 'gi.repository.WebKit2'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Linux GUI stability fix: exclude problematic system libraries
if os.name == 'posix' and '{runner_os}' == 'Linux':
    excluded_libs = {{
        'libglib-2.0.so.0', 'libgobject-2.0.so.0', 'libgio-2.0.so.0', 
        'libgmodule-2.0.so.0', 'libz.so.1', 'libsecret-1.so.0'
    }}
    a.binaries = [x for x in a.binaries if x[0] not in excluded_libs]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    strip=False,
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
    with open("opendata.spec", "w") as f:
        f.write(spec_content)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_spec.py <artifact_name> <runner_os>")
        sys.exit(1)
    generate_spec(sys.argv[1], sys.argv[2])
