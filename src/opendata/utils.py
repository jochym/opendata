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


def walk_project_files(
    root: Path, stop_event: Optional[Any] = None
) -> Generator[Path, None, None]:
    """
    Yields file paths while skipping common non-research directories.
    Supports cancellation via stop_event.
    """
    skip_dirs = {".git", ".venv", "node_modules", "__pycache__", ".opendata_tool"}
    # Use os.walk for better control over directory skipping and performance
    import os

    for dirpath, dirnames, filenames in os.walk(root):
        if stop_event and stop_event.is_set():
            return

        # In-place modification of dirnames to skip unwanted trees
        # Skip both explicitly listed directories and any hidden ones starting with '.'
        dirnames[:] = [
            d for d in dirnames if d not in skip_dirs and not d.startswith(".")
        ]

        # Skip files starting with '.'
        filenames = [f for f in filenames if not f.startswith(".")]

        # Yield the current directory for progress reporting
        yield Path(dirpath)

        for f in filenames:
            if stop_event and stop_event.is_set():
                return
            yield Path(dirpath) / f


def scan_project_lazy(
    root: Path,
    progress_callback: Optional[Callable[[str], None]] = None,
    stop_event: Optional[Any] = None,
) -> ProjectFingerprint:
    """
    Scans a directory recursively without reading file contents.
    Optimized for huge datasets (TB scale).
    Supports cancellation via stop_event.
    """
    file_count = 0
    total_size = 0
    extensions: Set[str] = set()
    structure_sample: List[str] = []

    for p in walk_project_files(root, stop_event=stop_event):
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
        """
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
