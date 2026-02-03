from pathlib import Path
from opendata.utils import walk_project_files
import os

root = Path("test_walk_dir")
root.mkdir(exist_ok=True)
(root / "file1.txt").write_text("hello")

print(f"Walking {root.absolute()}")
for p in walk_project_files(root):
    print(f"Found: {p} (is_file: {p.is_file()}, is_dir: {p.is_dir()})")
