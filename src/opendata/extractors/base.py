from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class PartialMetadata(BaseModel):
    """
    Independent model where all fields are optional.
    Used for merging results from multiple extractors.
    """

    title: str | None = None
    authors: list[dict[str, Any]] | None = None
    contacts: list[dict[str, Any]] | None = None
    description: list[str] | None = None
    keywords: list[str] | None = None
    science_branches_mnisw: list[str] | None = None
    science_branches_oecd: list[str] | None = None
    languages: list[str] | None = None
    kind_of_data: str | None = None


class BaseExtractor(ABC):
    """Base class for all heuristic metadata extractors."""

    @abstractmethod
    def can_handle(self, filepath: Path) -> bool:
        """Returns True if this extractor can process the given file."""
        pass

    @abstractmethod
    def extract(self, filepath: Path) -> PartialMetadata:
        """
        Extracts partial metadata from the file.
        Should be 'lazy' and only read headers/metadata if possible.
        """
        pass


class ExtractorRegistry:
    """Registry to manage and trigger relevant extractors."""

    def __init__(self):
        self._extractors = []

    def register(self, extractor: BaseExtractor):
        self._extractors.append(extractor)

    def get_extractors_for(self, filepath: Path) -> list[BaseExtractor]:
        return [e for e in self._extractors if e.can_handle(filepath)]
