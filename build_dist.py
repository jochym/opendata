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
    ]

    # Check for secrets in root or in the app's standard path
    secrets_path = root / "client_secrets.json"
    if secrets_path.exists():
        cmd.extend(["--add-data", f"{secrets_path}:."])
        print("Baking in client_secrets.json...")

    cmd.append(str(main_script))

    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("Build complete. Check the 'dist/' directory.")


if __name__ == "__main__":
    build_linux()
