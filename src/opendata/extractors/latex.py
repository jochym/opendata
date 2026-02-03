import re
from pathlib import Path
from opendata.extractors.base import BaseExtractor, PartialMetadata
from opendata.utils import read_file_header


class LatexExtractor(BaseExtractor):
    """Extracts metadata from LaTeX files using robust regex for multiple authors."""

    def can_handle(self, filepath: Path) -> bool:
        return filepath.suffix.lower() == ".tex"

    def extract(self, filepath: Path) -> PartialMetadata:
        content = read_file_header(
            filepath, max_bytes=16384
        )  # Read more for large preambles
        metadata = PartialMetadata()

        # 1. Title
        title_match = re.search(r"\\title\{([^}]+)\}", content)
        if title_match:
            metadata.title = title_match.group(1).strip()

        # 2. Authors (Handling multiple formats)
        # We look for all \author blocks and handle internal separators
        authors = []
        author_blocks = re.findall(r"\\author\{([^}]+)\}", content)

        from opendata.models import PersonOrOrg

        for block in author_blocks:
            # Clean up LaTeX macros like \inst, \thanks, \orcidlink, but keep the content of some if needed
            # Here we aggressively remove them to get clean names
            clean_block = re.sub(r"\\[a-zA-Z]+(\[[^\]]*\])?(\{.*?\})?", " ", block)
            # Remove ~ (non-breaking space) and other common LaTeX artifacts
            clean_block = (
                clean_block.replace("~", " ").replace("{", "").replace("}", "")
            )

            # Split by common separators: comma, 'and', \and
            parts = re.split(r",|\band\b|\\and", clean_block)
            for p in parts:
                name = p.strip()
                if name and len(name) > 2:
                    authors.append(PersonOrOrg(name=name))

        if authors:
            metadata.authors = authors

        return metadata
