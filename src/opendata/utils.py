import re
from pathlib import Path
import socket
from typing import List, Set, Generator, Callable, Optional, Any, Tuple
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
) -> Generator[Tuple[Path, Any], None, None]:
    """
    Yields (Path, stat) tuples for all relevant files, skipping excluded ones.
    Optimized using os.scandir for high-performance directory traversal.
    """
    import os
    import fnmatch

    skip_dirs = {".git", ".venv", "node_modules", "__pycache__", ".opendata_tool"}
    root_str = str(root)

    def _walk(current_dir):
        if stop_event and stop_event.is_set():
            return

        try:
            with os.scandir(current_dir) as it:
                entries = list(it)
        except OSError:
            return

        # Check for '.ignore'
        if any(e.name == ".ignore" for e in entries):
            return

        # Yield directory itself (with None for stat)
        yield Path(current_dir), None

        rel_dir = os.path.relpath(current_dir, root_str)
        if rel_dir == ".":
            rel_dir = ""

        subdirs = []
        for entry in entries:
            if entry.name.startswith(".") or entry.is_symlink():
                continue

            if entry.is_dir():
                if entry.name in skip_dirs:
                    continue
                if exclude_patterns:
                    rel_d_path = (
                        os.path.join(rel_dir, entry.name).replace("\\", "/") + "/"
                    )
                    if any(
                        fnmatch.fnmatch(rel_d_path, p)
                        or fnmatch.fnmatch(entry.name + "/", p)
                        for p in exclude_patterns
                    ):
                        continue
                subdirs.append(entry.path)
            elif entry.is_file():
                if exclude_patterns:
                    rel_f_path = os.path.join(rel_dir, entry.name).replace("\\", "/")
                    if any(
                        fnmatch.fnmatch(rel_f_path, p) or fnmatch.fnmatch(entry.name, p)
                        for p in exclude_patterns
                    ):
                        continue
                try:
                    yield Path(entry.path), entry.stat()
                except OSError:
                    continue

        for subdir in subdirs:
            yield from _walk(subdir)

    yield from _walk(root_str)


def scan_project_lazy(
    root: Path,
    progress_callback: Optional[Callable[[str, str, str], None]] = None,
    stop_event: Optional[Any] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> Tuple[ProjectFingerprint, List[dict]]:
    """
    Scans a directory recursively. Optimized for huge datasets.
    Returns both the Fingerprint and the full file list for database indexing.
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
        if stat is None:  # It's a directory
            pass
        else:  # It's a file
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

    fp = ProjectFingerprint(
        root_path=str(root),
        file_count=file_count,
        total_size_bytes=total_size,
        extensions=list(extensions),
        structure_sample=structure_sample,
    )
    return fp, full_inventory


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

            doc = Document(str(filepath))
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
