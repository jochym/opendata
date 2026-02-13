from pathlib import Path
from opendata.extractors.base import BaseExtractor, PartialMetadata
import h5py


class Hdf5Extractor(BaseExtractor):
    """Extracts metadata from HDF5 files."""

    def can_handle(self, filepath: Path) -> bool:
        return filepath.suffix.lower() in [".h5", ".hdf5", ".he5"]

    def extract(self, filepath: Path) -> PartialMetadata:
        metadata = PartialMetadata()
        try:
            # We open in read-only mode and do not read datasets (only attributes)
            with h5py.File(filepath, "r") as f:
                # Look for common metadata attributes at the root
                if "title" in f.attrs:
                    metadata.title = str(f.attrs["title"])
                if "description" in f.attrs:
                    metadata.description = [str(f.attrs["description"])]

                # Check for RODBUK specific fields if they were saved previously
                if "authors" in f.attrs:
                    metadata.authors = [
                        {"name": str(a)} for a in list(f.attrs["authors"])
                    ]

                metadata.kind_of_data = "HDF5 Dataset"

        except Exception:
            pass

        return metadata
