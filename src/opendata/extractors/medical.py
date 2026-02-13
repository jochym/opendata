from pathlib import Path

import pydicom

from opendata.extractors.base import BaseExtractor, PartialMetadata


class DicomExtractor(BaseExtractor):
    """Extracts metadata from Medical Imaging (DICOM) files."""

    def can_handle(self, filepath: Path) -> bool:
        # Standard DICOM suffixes
        return filepath.suffix.lower() in [".dcm", ".dicom"]

    def extract(self, filepath: Path) -> PartialMetadata:
        metadata = PartialMetadata()
        try:
            # stop_before_pixels=True makes this a "lazy" read
            ds = pydicom.dcmread(filepath, stop_before_pixels=True)

            # DICOM study description can serve as title/description
            if hasattr(ds, "StudyDescription"):
                metadata.title = ds.StudyDescription

            # Map medical modality to kind of data
            if hasattr(ds, "Modality"):
                metadata.kind_of_data = f"Medical Imaging ({ds.Modality})"

        except Exception:
            pass

        return metadata
