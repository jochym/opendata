#!/usr/bin/env python3
"""
Field Protocol GUI Debug Script

This script monitors the field protocol selection in real-time while you test in the browser.
It checks:
1. What's in project_config.json
2. What the UI dropdown shows
3. Whether they stay in sync

Usage:
    Terminal 1: python src/opendata/main.py
    Terminal 2: python tests/e2e/debug_field_protocol.py
"""

import json
import time
from pathlib import Path
from datetime import datetime

# Configuration
PROJECT_ID = "ec7e33c23da584709f6322cb52b01d52"  # Your test project
CONFIG_PATH = (
    Path.home() / ".opendata_tool" / "projects" / PROJECT_ID / "project_config.json"
)


def read_config():
    """Reads the current field protocol from disk."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
            return config.get("field_name", "NOT SET")
    return "FILE NOT FOUND"


def main():
    print("=" * 80)
    print("Field Protocol Debug Monitor")
    print("=" * 80)
    print(f"Monitoring: {CONFIG_PATH}")
    print(f"Project ID: {PROJECT_ID}")
    print("=" * 80)
    print()

    last_value = None
    check_count = 0

    try:
        while True:
            check_count += 1
            current_value = read_config()
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Check if value changed
            if current_value != last_value:
                print(f"[{timestamp}] ✅ Field changed: {last_value} → {current_value}")
                last_value = current_value
            else:
                # Periodic status update
                if check_count % 10 == 0:
                    print(f"[{timestamp}] ⏳ Field: {current_value} (unchanged)")

            # Check every second
            time.sleep(1)

    except KeyboardInterrupt:
        print()
        print("=" * 80)
        print("Monitoring stopped")
        print(f"Final field value: {read_config()}")
        print("=" * 80)


if __name__ == "__main__":
    main()
