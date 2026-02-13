from pathlib import Path

from docx import Document

from opendata.extractors.base import BaseExtractor, PartialMetadata


class DocxExtractor(BaseExtractor):
    """Extracts metadata from Office (.docx) files."""

    def can_handle(self, filepath: Path) -> bool:
        return filepath.suffix.lower() == ".docx"

    def extract(self, filepath: Path) -> PartialMetadata:
        metadata = PartialMetadata()
        try:
            # We use python-docx's built-in core properties (fast, no heavy read)
            doc = Document(filepath)
            props = doc.core_properties

            if props.title:
                metadata.title = props.title
            if props.author:
                metadata.authors = [{"name": props.author}]
            if props.comments:
                metadata.description = [props.comments]
            if props.keywords:
                metadata.keywords = [k.strip() for k in props.keywords.split(",")]

        except Exception:
            # If docx reading fails, we gracefully return empty partial metadata
            pass

        return metadata
