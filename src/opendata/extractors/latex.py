import re
from pathlib import Path
from opendata.extractors.base import BaseExtractor, PartialMetadata
from opendata.utils import read_file_header


class LatexExtractor(BaseExtractor):
    """Extracts metadata from LaTeX files using regex."""

    def can_handle(self, filepath: Path) -> bool:
        return filepath.suffix.lower() == ".tex"

    def extract(self, filepath: Path) -> PartialMetadata:
        # Read the first 8KB of the TeX file (usually contains the preamble)
        content = read_file_header(filepath, max_bytes=8192)

        metadata = PartialMetadata()

        # Title extraction: \title{...}
        title_match = re.search(r"\\title\{([^}]+)\}", content)
        if title_match:
            metadata.title = title_match.group(1).strip()

        # Author extraction: \author{...}
        # Note: This is a simple regex, might need AI for complex cases
        author_match = re.search(r"\\author\{([^}]+)\}", content)
        if author_match:
            # Placeholder for name parsing logic
            metadata.authors = [{"name": author_match.group(1).strip()}]

        return metadata
