import re
from pathlib import Path

from opendata.extractors.base import BaseExtractor, PartialMetadata
from opendata.utils import read_file_header


class VaspExtractor(BaseExtractor):
    """Extracts metadata from VASP calculation files (OUTCAR, INCAR, POSCAR)."""

    def can_handle(self, filepath: Path) -> bool:
        # Check for common VASP file names (case-insensitive)
        name = filepath.name.upper()
        return name in ["OUTCAR", "INCAR", "POSCAR", "KPOINTS", "POTCAR"]

    def extract(self, filepath: Path) -> PartialMetadata:
        metadata = PartialMetadata()
        name = filepath.name.upper()

        # We read the first 8KB to identify the calculation type/system
        content = read_file_header(filepath, max_bytes=8192)

        if name == "INCAR":
            # Extract SYSTEM tag if present
            system_match = re.search(r"SYSTEM\s*=\s*([^\n#]+)", content, re.IGNORECASE)
            if system_match:
                metadata.title = f"VASP Calculation: {system_match.group(1).strip()}"
            metadata.kind_of_data = "VASP Input (INCAR)"

        elif name == "OUTCAR":
            # Extract VASP version and parallelization info
            version_match = re.search(r"vasp\.([\d\.]+)", content)
            if version_match:
                metadata.description = [f"VASP version {version_match.group(1)} output"]
            metadata.kind_of_data = "VASP Output (OUTCAR)"

        elif name == "POSCAR":
            # First line of POSCAR is usually a comment/system name
            first_line = content.split("\n")[0].strip()
            if first_line:
                metadata.title = f"Structure: {first_line}"
            metadata.kind_of_data = "VASP Structure (POSCAR)"

        return metadata


class LatticeDynamicsExtractor(BaseExtractor):
    """Extracts metadata from Phonopy and ALAMODE files."""

    def can_handle(self, filepath: Path) -> bool:
        name = filepath.name.lower()
        # Phonopy commonly uses phonopy.yaml or band.yaml
        # ALAMODE uses .in or .out files with specific headers
        return "phonopy" in name or "alamode" in name or name.endswith(".yaml")

    def extract(self, filepath: Path) -> PartialMetadata:
        metadata = PartialMetadata()
        content = read_file_header(filepath, max_bytes=4096)

        if "phonopy" in filepath.name.lower():
            metadata.kind_of_data = "Lattice Dynamics (Phonopy)"
            # Look for system info in yaml
            if "natom:" in content:
                metadata.description = ["Phonopy calculation file"]

        if "alamode" in filepath.name.lower():
            metadata.kind_of_data = "Lattice Dynamics (ALAMODE)"

        return metadata


class ColumnarDataExtractor(BaseExtractor):
    """Extracts metadata from generic columnar text files (CSVs, dat, etc)."""

    def can_handle(self, filepath: Path) -> bool:
        return filepath.suffix.lower() in [".dat", ".csv", ".txt", ".out"]

    def extract(self, filepath: Path) -> PartialMetadata:
        metadata = PartialMetadata()
        content = read_file_header(filepath, max_bytes=2048)

        # Check if it looks like columns of numbers
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        if not lines:
            return metadata

        # Simple heuristic: if the first non-empty line has numbers
        # or common CSV separators, we tag it.
        first_line = lines[0]
        if re.search(r"[\d\.eE\-\+]+[\s,;]+[\d\.eE\-\+]+", first_line):
            metadata.kind_of_data = "Columnar Numerical Data"

        return metadata
