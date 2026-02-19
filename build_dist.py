#!/usr/bin/env python3
"""
Legacy build script for backward compatibility.
This script redirects to the new unified build.py script.

DEPRECATED: Please use build.py directly instead.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Redirect to the new build.py script."""
    print("⚠️  build_dist.py is deprecated. Please use 'python build.py' instead.")
    print("Redirecting to build.py...\n")
    
    build_script = Path(__file__).parent / "build.py"
    
    # Pass through all arguments
    cmd = [sys.executable, str(build_script)] + sys.argv[1:]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()

