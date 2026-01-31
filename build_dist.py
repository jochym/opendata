import os
import sys
import subprocess
from pathlib import Path


def build_linux():
    print("Building OpenData Tool for Linux...")

    # Define paths
    root = Path(__file__).parent
    main_script = root / "src" / "opendata" / "main.py"

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name",
        "opendata-tool",
        "--add-data",
        f"{root}/src/opendata/ui:opendata/ui",
        # We need to make sure NiceGUI's static files are included if they are outside the standard path
        # But usually NiceGUI handles its internal static files.
        # We also need to add client_secrets.json if it exists in the root for the build
        str(main_script),
    ]

    if (root / "client_secrets.json").exists():
        cmd.extend(["--add-data", f"{root}/client_secrets.json:."])
        print("Baking in client_secrets.json...")

    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("Build complete. Check the 'dist/' directory.")


if __name__ == "__main__":
    build_linux()
