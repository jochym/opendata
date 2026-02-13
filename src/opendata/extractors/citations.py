from pathlib import Path

import bibtexparser

from opendata.extractors.base import BaseExtractor, PartialMetadata


class BibtexExtractor(BaseExtractor):
    """Extracts metadata from BibTeX files."""

    def can_handle(self, filepath: Path) -> bool:
        return filepath.suffix.lower() == ".bib"

    def extract(self, filepath: Path) -> PartialMetadata:
        metadata = PartialMetadata()
        try:
            with open(filepath, encoding="utf-8") as bibtex_file:
                bib_database = bibtexparser.load(bibtex_file)

            if bib_database.entries:
                # We take the first entry as a representative for the project
                entry = bib_database.entries[0]
                if "title" in entry:
                    metadata.title = entry["title"].strip("{}")
                if "author" in entry:
                    # Very simple author split
                    from opendata.models import PersonOrOrg

                    authors = entry["author"].split(" and ")
                    metadata.authors = [
                        PersonOrOrg(
                            name=a.strip("{} ").replace("{", "").replace("}", "")
                        )
                        for a in authors
                        if a.strip()
                    ]
                if "keywords" in entry:
                    metadata.keywords = [
                        k.strip() for k in entry["keywords"].split(",")
                    ]

        except Exception:
            pass

        return metadata
