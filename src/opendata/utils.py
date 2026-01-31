from pathlib import Path
import socket
from typing import List, Set
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


def scan_project_lazy(root: Path) -> ProjectFingerprint:
    """
    Scans a directory recursively without reading file contents.
    Optimized for huge datasets (TB scale).
    """
    file_count = 0
    total_size = 0
    extensions: Set[str] = set()
    structure_sample: List[str] = []

    # rglob is lazy, but we still need to be careful with huge lists
    for p in root.rglob("*"):
        if p.is_file():
            file_count += 1
            # Get size without reading data
            total_size += p.stat().st_size
            extensions.add(p.suffix.lower())

            if len(structure_sample) < 50:
                structure_sample.append(str(p.relative_to(root)))

    return ProjectFingerprint(
        root_path=str(root),
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
