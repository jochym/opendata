from pathlib import Path
import socket
from typing import List, Set, Generator, Callable, Optional
from opendata.models import ProjectFingerprint


def get_local_ip() -> str:
    """Returns the local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def walk_project_files(root: Path) -> Generator[Path, None, None]:
    """
    Yields file paths while skipping common non-research directories.
    """
    skip_dirs = {".git", ".venv", "node_modules", "__pycache__", ".opendata_tool"}
    # Use os.walk for better control over directory skipping and performance
    import os

    for dirpath, dirnames, filenames in os.walk(root):
        # In-place modification of dirnames to skip unwanted trees
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]

        # Yield the current directory for progress reporting
        yield Path(dirpath)

        for f in filenames:
            yield Path(dirpath) / f


def scan_project_lazy(
    root: Path, progress_callback: Optional[Callable[[str], None]] = None
) -> ProjectFingerprint:
    """
    Scans a directory recursively without reading file contents.
    Optimized for huge datasets (TB scale).
    """
    file_count = 0
    total_size = 0
    extensions: Set[str] = set()
    structure_sample: List[str] = []

    for p in walk_project_files(root):
        if p.is_dir():
            if progress_callback:
                progress_callback(str(p.relative_to(root)) if p != root else ".")
            continue

        file_count += 1
        try:
            total_size += p.stat().st_size
        except OSError:
            pass  # Skip files that disappeared during scan
        extensions.add(p.suffix.lower())

        if len(structure_sample) < 100:
            structure_sample.append(str(p.relative_to(root)))

    return ProjectFingerprint(
        root_path=str(root.resolve()),
        file_count=file_count,
        total_size_bytes=total_size,
        extensions=list(extensions),
        structure_sample=structure_sample,
    )


def read_file_header(p: Path, max_bytes: int = 4096) -> str:
    """
    Reads only the first few KB of a file to detect metadata/headers.
    Safe for TB-scale data files.
    """
    try:
        with open(p, "rb") as f:
            chunk = f.read(max_bytes)
            # Try decoding as UTF-8, fallback to simple representation
            return chunk.decode("utf-8", errors="replace")
    except Exception:
        return ""
