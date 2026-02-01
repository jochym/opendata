from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from opendata.models import Metadata, PersonOrOrg, Contact


class PartialMetadata(BaseModel):
    """
    Independent model where all fields are optional.
    Used for merging results from multiple extractors.
    """

    title: Optional[str] = None
    authors: Optional[List[PersonOrOrg]] = None
    contacts: Optional[List[Contact]] = None
    description: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    science_branches_mnisw: Optional[List[str]] = None
    science_branches_oecd: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    kind_of_data: Optional[str] = None


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

    def get_extractors_for(self, filepath: Path) -> List[BaseExtractor]:
        return [e for e in self._extractors if e.can_handle(filepath)]
