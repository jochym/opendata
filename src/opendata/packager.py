import zipfile
from pathlib import Path

import yaml

from opendata.models import Metadata
from opendata.utils import walk_project_files


class PackagingService:
    """Handles the creation of the final RODBUK submission package."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path

    def generate_metadata_package(
        self,
        project_dir: Path,
        metadata: Metadata,
        package_name: str = "rodbuk_package",
    ) -> Path:
        """
        Creates a ZIP package containing ONLY the metadata and root documentation.
        Excludes research data.
        """
        target_zip = self.workspace_path / f"{package_name}.zip"

        with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. Generated Metadata (YAML and JSON)
            metadata_yaml = yaml.dump(
                metadata.model_dump(), allow_unicode=True, sort_keys=False
            )
            zf.writestr("metadata.yaml", metadata_yaml)
            zf.writestr("metadata.json", metadata.model_dump_json(indent=2))

            # 2. Root Documentation (Standard files)
            doc_prefixes = ("README", "LICENSE", "COPYING", "CITATION", "NOTICE")
            exact_docs = ("codemeta.json",)

            for p in project_dir.iterdir():
                if p.is_file():
                    name_upper = p.name.upper()
                    is_doc = any(
                        name_upper.startswith(pref) for pref in doc_prefixes
                    ) or (p.name.lower() in exact_docs)

                    if is_doc:
                        zf.write(p, arcname=p.name)

        return target_zip

    def generate_package(
        self,
        project_dir: Path,
        metadata: Metadata,
        package_name: str = "rodbuk_package",
        file_list: list[Path] | None = None,
    ) -> Path:
        """
        Creates a ZIP package containing the research data and the RODBUK metadata.
        Strictly Read-Only regarding the project_dir.
        """
        target_zip = self.workspace_path / f"{package_name}.zip"

        with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. Add the metadata file (YAML for human-readability in the package too)
            metadata_yaml = yaml.dump(
                metadata.model_dump(), allow_unicode=True, sort_keys=False
            )
            zf.writestr("metadata.yaml", metadata_yaml)

            # 2. Add the research files (Lazy/Safe copying)
            if file_list is not None:
                for p in file_list:
                    if p.exists() and p.is_file():
                        rel_path = p.relative_to(project_dir)
                        zf.write(p, arcname=rel_path)
            else:
                # Fallback to old behavior if no list provided
                for p, stat in walk_project_files(project_dir):
                    if stat is not None:
                        rel_path = p.relative_to(project_dir)
                        zf.write(p, arcname=rel_path)

        return target_zip

    def validate_for_rodbuk(self, metadata: Metadata) -> list[str]:
        """
        Final validation check against mandatory RODBUK fields.
        Returns a list of error messages (empty if valid).
        """
        errors = []
        # Pydantic already does a lot of this, but we can add domain-specific rules
        if not metadata.title or len(metadata.title) < 5:
            errors.append("Title is missing or too short.")

        if not metadata.authors:
            errors.append("At least one author is required.")
        else:
            for author in metadata.authors:
                if not author.name:
                    errors.append("Author name cannot be empty.")

        if not metadata.contacts:
            errors.append("At least one contact is required.")

        if not metadata.science_branches_mnisw or not metadata.science_branches_oecd:
            errors.append("Science branch classification (MNiSW & OECD) is mandatory.")

        return errors
