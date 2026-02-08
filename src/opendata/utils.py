import re
from pathlib import Path
import socket
from typing import List, Set, Generator, Callable, Optional, Any
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


def shorten_path(path: str, max_len: int = 60) -> str:
    """Shortens a path by keeping the first two and last two components."""
    if len(path) <= max_len:
        return path
    parts = path.split("/")
    if len(parts) <= 4:
        return path
    return f"{parts[0]}/{parts[1]}/.../{parts[-2]}/{parts[-1]}"


def format_size(size_bytes: int) -> str:
    """Formats bytes into human readable string."""
    import math

    if size_bytes == 0:
        return "0 B"
    units = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    return f"{size_bytes / (1024**i):.1f} {units[i]}"


def walk_project_files(
    root: Path,
    stop_event: Optional[Any] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> Generator[Path, None, None]:
    """
    Yields file paths while skipping common non-research directories and user-defined patterns.
    Does NOT follow symbolic links.
    Skips the entire directory tree if a '.ignore' file is present in the root of that tree.
    Supports cancellation via stop_event.
    """
    import os
    import fnmatch

    skip_dirs = {".git", ".venv", "node_modules", "__pycache__", ".opendata_tool"}

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        if stop_event and stop_event.is_set():
            return

        # Check for '.ignore' file in the current directory
        if ".ignore" in filenames:
            # Clear dirnames and filenames to skip this entire tree
            dirnames[:] = []
            filenames[:] = []
            continue

        # Filter out directories
        original_dir_count = len(dirnames)
        dirnames[:] = [
            d
            for d in dirnames
            if d not in skip_dirs
            and not d.startswith(".")
            and not os.path.islink(os.path.join(dirpath, d))
        ]

        # Filter files
        original_file_count = len(filenames)
        final_filenames = [
            f
            for f in filenames
            if not f.startswith(".") and not os.path.islink(os.path.join(dirpath, f))
        ]

        if exclude_patterns:
            for pattern in exclude_patterns:
                # If pattern ends with / it's a directory pattern
                if pattern.endswith("/"):
                    clean_p = pattern[:-1]
                    dirnames[:] = [
                        d for d in dirnames if not fnmatch.fnmatch(d, clean_p)
                    ]
                else:
                    final_filenames = [
                        f for f in final_filenames if not fnmatch.fnmatch(f, pattern)
                    ]

        if original_file_count > 0 and len(final_filenames) == 0:
            # This is suspicious - we had files but filtered them all out
            import logging

            logging.getLogger("opendata.utils").debug(
                f"Filtered out all {original_file_count} files in {dirpath}"
            )

        # Yield the current directory for progress reporting
        yield Path(dirpath)

        for f in final_filenames:
            if stop_event and stop_event.is_set():
                return
            yield Path(dirpath) / f


def scan_project_lazy(
    root: Path,
    progress_callback: Optional[Callable[[str, str, str], None]] = None,
    stop_event: Optional[Any] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> ProjectFingerprint:
    """
    Scans a directory recursively without reading file contents.
    Optimized for huge datasets (TB scale).
    Supports cancellation via stop_event.
    """
    import time

    file_count = 0
    total_size = 0
    extensions = set()
    structure_sample = []

    last_ui_update = 0
    # Throttling UI updates to 10Hz to prevent flickering and performance lag
    UI_UPDATE_INTERVAL = 0.1

    for p in walk_project_files(root, stop_event, exclude_patterns):
        if p.is_file():
            file_count += 1
            try:
                total_size += p.stat().st_size
            except Exception:
                pass
            extensions.add(p.suffix.lower())
            if len(structure_sample) < 50:
                structure_sample.append(str(p.relative_to(root)))

        now = time.time()
        if progress_callback and (now - last_ui_update > UI_UPDATE_INTERVAL):
            total_size_str = format_size(total_size)
            progress_callback(
                f"{total_size_str} - {file_count} files",
                str(p.relative_to(root)),
                f"Scanning {p.name}...",
            )
            last_ui_update = now

    return ProjectFingerprint(
        root_path=str(root),
        file_count=file_count,
        total_size_bytes=total_size,
        extensions=list(extensions),
        structure_sample=structure_sample,
    )


def list_project_files_full(
    root: Path,
    stop_event: Optional[Any] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> List[dict]:
    """
    Returns a full list of files with metadata (size, rel_path) for UI inventory.
    Skips directories, yields only files.
    """
    files = []
    for p in walk_project_files(root, stop_event, exclude_patterns=exclude_patterns):
        if p.is_file():
            rel_path = str(p.relative_to(root))
            try:
                stat = p.stat()
                files.append(
                    {
                        "path": rel_path,
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                    }
                )
            except Exception:
                # Handle files that might have disappeared or are inaccessible
                pass
    return files


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


class PromptManager:
    """Manages external Markdown-based prompt templates."""

    def __init__(self, prompts_dir: Path | None = None):
        if not prompts_dir:
            # Assume src/opendata/prompts relative to this file
            prompts_dir = Path(__file__).parent / "prompts"
        self.prompts_dir = prompts_dir

    def render(self, template_name: str, context: dict) -> str:
        """Loads a .md template and renders it with the provided context."""
        template_path = self.prompts_dir / f"{template_name}.md"
        if not template_path.exists():
            return f"Error: Template {template_name} not found."

        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        return template.format(**context)


class FullTextReader:
    """
    Utility for deep reading of research documents (LaTeX, Docx) to support
    full-text context extraction.
    """

    @staticmethod
    def read_latex_full(filepath: Path) -> str:
        r"""
        Reads the full content of a LaTeX file.
        Recursively resolves \input{} and \include{} commands.
        """
        try:
            content = []
            base_dir = filepath.parent

            def resolve_recursive(current_path: Path):
                with open(current_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        # Simple regex for \input{file} and \include{file}
                        match = re.search(r"\\(?:input|include)\{([^}]+)\}", line)
                        if match:
                            sub_file = match.group(1)
                            if not sub_file.endswith(".tex"):
                                sub_file += ".tex"
                            sub_path = base_dir / sub_file
                            if sub_path.exists():
                                resolve_recursive(sub_path)
                            else:
                                content.append(f" [Missing file: {sub_file}] ")
                        else:
                            content.append(line)

            resolve_recursive(filepath)
            return "".join(content)
        except Exception as e:
            return f"[Error reading LaTeX file: {e}]"

    @staticmethod
    def read_docx_full(filepath: Path) -> str:
        """
        Reads the full text content of a .docx file, including paragraphs and tables.
        """
        try:
            from docx import Document  # type: ignore

            doc = Document(filepath)
            full_text = []

            # Extract paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)

            # Extract tables (naive linear reading)
            for table in doc.tables:
                for row in table.rows:
                    row_text = [
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    ]
                    if row_text:
                        full_text.append(" | ".join(row_text))

            return "\n\n".join(full_text)
        except Exception as e:
            return f"[Error reading Docx file: {e}]"

    @staticmethod
    def read_full_text(filepath: Path) -> str:
        """
        Dispatches to the appropriate reader based on file extension.
        """
        suffix = filepath.suffix.lower()
        if suffix == ".tex":
            return FullTextReader.read_latex_full(filepath)
        elif suffix == ".docx":
            return FullTextReader.read_docx_full(filepath)
        else:
            # Fallback for plain text files
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception as e:
                return f"[Error reading text file: {e}]"
