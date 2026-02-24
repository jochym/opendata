import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Generator, List, Optional, Tuple

from opendata.models import ProjectFingerprint

logger = logging.getLogger("opendata.utils")


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev, PyInstaller and installed mode (pyApp/pip)"""
    # 1. PyInstaller case - bundled executable
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
        # PyInstaller structure depends on --add-data flags
        # We added: "src/opendata/VERSION:." so VERSION is in base_path
        if relative_path.startswith("src/opendata/"):
            stripped = relative_path.replace("src/opendata/", "", 1)
            if (base_path / stripped).exists():
                return base_path / stripped
        return base_path / relative_path

    # 2. Installed mode (pyApp / pip) or Development mode
    # Path to the 'opendata' package directory
    package_root = Path(__file__).parent.absolute()

    # Check if we're in development mode (src layout)
    # In dev: __file__ is /path/to/OpenData/src/opendata/utils.py
    # parent.parent = /path/to/OpenData/src -> has 'src' dir
    project_src = package_root.parent
    if project_src.name == "src" and (project_src.parent / ".git").exists():
        # Development mode - return path relative to project root
        return project_src.parent / relative_path

    # 3. Installed mode (pyApp / pip)
    # __file__ is /path/to/site-packages/opendata/utils.py
    # Files are in /path/to/site-packages/opendata/
    # So "src/opendata/VERSION" should become just "VERSION"
    if relative_path.startswith("src/opendata/"):
        stripped = relative_path.replace("src/opendata/", "", 1)
        return package_root / stripped

    # Fallback for other paths
    return package_root / relative_path


def get_app_version() -> str:
    """Reads the application version from the VERSION file or package metadata."""
    version_str = "0.0.0"

    # 1. Try to find VERSION file in the opendata package directory
    try:
        version_file = get_resource_path("src/opendata/VERSION")
        if version_file.exists():
            version_str = version_file.read_text(encoding="utf-8").strip()
    except Exception:
        # 2. Try package metadata (installed mode)
        try:
            from importlib.metadata import version

            version_str = version("opendata-tool")
        except Exception:
            pass

    # 3. Append git SHA if in development mode (not bundled and .git exists)
    if not getattr(sys, "frozen", False):
        try:
            import subprocess

            sha = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            if sha and "+" not in version_str:
                version_str = f"{version_str}+{sha}"
        except Exception:
            pass

    return version_str


def get_local_ip() -> str:
    """Detects the local IP address of the machine."""
    import socket

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def format_size(size_bytes: int) -> str:
    """Formats file size in bytes to human-readable string."""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    import math

    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


class PromptManager:
    """Manages loading and rendering of markdown prompt templates."""

    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or get_resource_path("src/opendata/prompts")

    def render(self, template_name: str, context: dict) -> str:
        # Try multiple possible paths for flexibility
        possible_paths = [
            self.templates_dir / f"{template_name}.md",
            self.templates_dir / f"system_prompt_{template_name}.md",
        ]

        path = None
        for p in possible_paths:
            if p.exists():
                path = p
                break

        # Fallback for installed package
        if not path:
            for p in possible_paths:
                fallback = get_resource_path(f"prompts/{p.name}")
                if Path(fallback).exists():
                    path = Path(fallback)
                    break

        if not path:
            raise FileNotFoundError(f"Prompt template not found: {template_name}")

        template = path.read_text(encoding="utf-8")
        return template.format(**context)


class FullTextReader:
    """Handles reading and converting various file formats to plain text for AI."""

    @staticmethod
    def read_full_text(path: Path) -> str:
        if not path.exists():
            return ""

        suffix = path.suffix.lower()
        try:
            if suffix in [".txt", ".md", ".yaml", ".yml", ".json", ".tex", ".bib"]:
                return path.read_text(encoding="utf-8")
            elif suffix == ".docx":
                import docx2txt

                return docx2txt.process(str(path))
            elif suffix == ".pdf":
                import pypdf

                reader = pypdf.PdfReader(str(path))
                return "\n".join([page.extract_text() for page in reader.pages])
        except Exception as e:
            logger.warning(f"Failed to read text from {path}: {e}")
        return ""


def is_path_excluded(rel_path_str: str, name: str, exclude_patterns: List[str]) -> bool:
    """Checks if a relative path string or filename is excluded by any pattern."""
    if not exclude_patterns:
        return False

    import fnmatch

    clean_path = rel_path_str.replace("\\", "/")

    for pattern in exclude_patterns:
        clean_pat = pattern.replace("\\", "/").rstrip("/")
        try:
            # 1. Direct name match
            if name == clean_pat:
                return True

            # 2. Glob match on full relative path
            if fnmatch.fnmatch(clean_path, clean_pat) or fnmatch.fnmatch(
                name, clean_pat
            ):
                return True

            # 3. Handle root-level match for **/ patterns
            if clean_pat.startswith("**/"):
                sub_pat = clean_pat[3:]
                if fnmatch.fnmatch(name, sub_pat) or fnmatch.fnmatch(
                    clean_path, sub_pat
                ):
                    return True

            # 4. Handle leading slash in pattern
            if clean_pat.startswith("/") and fnmatch.fnmatch(clean_path, clean_pat[1:]):
                return True

        except ValueError:
            pass
    return False


def walk_project_files(
    root: Path,
    stop_event: Optional[Any] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> Generator[Tuple[Path, Any], None, None]:
    """
    Yields (Path, stat) tuples for all relevant files, skipping excluded ones.
    """
    import os

    skip_dirs = {".git", ".venv", "node_modules", "__pycache__", ".opendata_tool"}
    root_str = str(root.expanduser().resolve())
    excludes = exclude_patterns or []

    if excludes:
        logger.debug(f"Walking {root_str} with exclusions: {excludes}")

    def _walk(current_dir):
        if stop_event and stop_event.is_set():
            return

        if (Path(current_dir) / ".ignore").exists():
            return

        rel_dir = os.path.relpath(current_dir, root_str).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""

        if rel_dir and is_path_excluded(
            rel_dir, os.path.basename(current_dir), excludes
        ):
            return

        yield Path(current_dir), None

        try:
            with os.scandir(current_dir) as it:
                subdirs = []
                for entry in it:
                    if stop_event and stop_event.is_set():
                        return

                    if entry.name.startswith(".") or entry.is_symlink():
                        continue

                    rel_entry_path = (
                        os.path.join(rel_dir, entry.name).replace("\\", "/")
                        if rel_dir
                        else entry.name
                    )

                    if is_path_excluded(rel_entry_path, entry.name, excludes):
                        continue

                    if entry.is_dir():
                        if entry.name in skip_dirs:
                            continue
                        subdirs.append(entry.path)
                    elif entry.is_file():
                        try:
                            yield Path(entry.path), entry.stat()
                        except (FileNotFoundError, PermissionError):
                            continue

                for sd in subdirs:
                    yield from _walk(sd)

        except (PermissionError, FileNotFoundError):
            return

    yield from _walk(root_str)


def scan_project_lazy(
    root: Path,
    progress_callback: Optional[Callable[[str, str, str], None]] = None,
    stop_event: Optional[Any] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> Tuple[ProjectFingerprint, List[dict]]:
    """
    Scans a directory recursively. Optimized for huge datasets.
    """
    import time

    file_count = 0
    total_size = 0
    extensions = set()
    structure_sample = []
    full_inventory = []

    last_ui_update = 0
    UI_UPDATE_INTERVAL = 0.1

    for p, stat in walk_project_files(root, stop_event, exclude_patterns):
        if stop_event and stop_event.is_set():
            import asyncio

            raise asyncio.CancelledError("Scan cancelled by user")

        if stat is not None:  # It's a file
            file_count += 1
            size = stat.st_size
            total_size += size
            suffix = p.suffix.lower()
            extensions.add(suffix)

            rel_path = str(p.relative_to(root))
            full_inventory.append(
                {"path": rel_path, "size": size, "mtime": stat.st_mtime}
            )

            if len(structure_sample) < 50:
                structure_sample.append(rel_path)

        now = time.time()
        if progress_callback and (now - last_ui_update > UI_UPDATE_INTERVAL):
            total_size_str = format_size(total_size)
            progress_callback(
                f"{total_size_str} - {file_count} files",
                str(p.relative_to(root)),
                f"Scanning {p.name}...",
            )
            last_ui_update = now

    fingerprint = ProjectFingerprint(
        root_path=str(root.absolute()),
        file_count=file_count,
        total_size_bytes=total_size,
        extensions=list(extensions),
        structure_sample=structure_sample,
    )

    return fingerprint, full_inventory


def setup_logging(level: int = logging.INFO):
    """Configures the global logging for the application."""
    import sys

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Suppress noisy debug logs from heavy libraries
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)


def format_file_list(files: List[Path], root: Path) -> str:
    """Formats a list of files for AI context."""
    lines = []
    for f in sorted(files):
        try:
            rel = f.relative_to(root)
            size = format_size(f.stat().st_size)
            lines.append(f"- `{rel}` ({size})")
        except Exception:
            continue
    return "\n".join(lines)


def read_file_header(filepath: Path, max_bytes: int = 4096) -> str:
    """Reads the first N bytes of a file as text, handling encoding errors gracefully."""
    try:
        with open(filepath, "rb") as f:
            raw = f.read(max_bytes)
        # Try UTF-8 first, fallback to latin-1 which accepts any byte
        try:
            return raw.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="replace")
    except Exception as e:
        logger.warning(f"Failed to read file header from {filepath}: {e}")
        return ""
