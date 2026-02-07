from pathlib import Path
import json
from typing import List, Set, Dict, Optional
from opendata.models import PackageManifest
from opendata.workspace import WorkspaceManager
from opendata.utils import walk_project_files
import fnmatch


class PackageManager:
    """Manages file selection and package content definition."""

    def __init__(self, workspace: WorkspaceManager):
        self.workspace = workspace

    def get_manifest(self, project_id: str) -> PackageManifest:
        """Loads or creates a package manifest for the project."""
        pdir = self.workspace.get_project_dir(project_id)
        manifest_path = pdir / "package_manifest.json"

        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    return PackageManifest.model_validate_json(f.read())
            except Exception as e:
                print(f"[ERROR] Failed to load manifest for {project_id}: {e}")

        return PackageManifest(project_id=project_id)

    def save_manifest(self, manifest: PackageManifest):
        """Persists the package manifest."""
        pdir = self.workspace.get_project_dir(manifest.project_id)
        pdir.mkdir(parents=True, exist_ok=True)
        with open(pdir / "package_manifest.json", "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))

    def build_file_tree(
        self, root_path: Path, exclude_patterns: List[str]
    ) -> List[Dict]:
        """
        Builds a hierarchical tree structure for NiceGUI ui.tree.
        Optimized for reasonable depth.
        """
        tree = []
        # Map path strings to their tree node dictionaries
        nodes = {}

        # We need to walk the directory to build the tree
        # Use existing walker but maybe we need to be careful with huge trees
        # For UI, we might want to limit depth or count

        # Root node
        root_key = str(root_path)
        nodes[root_key] = {
            "id": root_key,
            "label": root_path.name,
            "children": [],
            "icon": "folder",
            "path": str(root_path),
        }
        tree.append(nodes[root_key])

        try:
            # Walk and build
            for p in walk_project_files(
                root_path, exclude_patterns=None
            ):  # We handle exclusions visually
                path_str = str(p)
                if path_str == root_key:
                    continue

                parent_str = str(p.parent)

                # Check if excluded by protocol
                is_excluded = False
                if exclude_patterns:
                    for pattern in exclude_patterns:
                        if fnmatch.fnmatch(p.name, pattern):
                            is_excluded = True
                            break
                        # Check relative path match too?
                        rel_p = str(p.relative_to(root_path))
                        if fnmatch.fnmatch(rel_p, pattern):
                            is_excluded = True
                            break

                node = {
                    "id": path_str,
                    "label": p.name,
                    "children": [],
                    "icon": "description" if p.is_file() else "folder",
                    "path": str(p),
                    "excluded": is_excluded,
                }

                if parent_str in nodes:
                    nodes[parent_str]["children"].append(node)
                    nodes[path_str] = node
                else:
                    # Parent missing (maybe skipped?), attach to root or nearest ancestor
                    # For simplicity in this walker, parents are usually yielded first or exist
                    pass

        except Exception as e:
            print(f"Error building tree: {e}")

        return tree

    def get_effective_file_list(
        self,
        project_path: Path,
        manifest: PackageManifest,
        protocol_excludes: List[str],
    ) -> List[Path]:
        """
        Calculates the final list of files to include in the package.
        Logic:
        1. Start with all files
        2. Apply protocol excludes -> Excluded
        3. Apply manifest force_exclude -> Excluded
        4. Apply manifest force_include -> Included (overrides 2)
        """
        final_list = []

        for p in walk_project_files(
            project_path, exclude_patterns=None
        ):  # Get RAW list
            if not p.is_file():
                continue

            rel_p = str(p.relative_to(project_path))

            # 1. Check Forced
            if rel_p in manifest.force_include:
                final_list.append(p)
                continue

            if rel_p in manifest.force_exclude:
                continue

            # 2. Check Protocol Excludes
            is_excluded = False
            if protocol_excludes:
                for pattern in protocol_excludes:
                    if fnmatch.fnmatch(p.name, pattern) or fnmatch.fnmatch(
                        rel_p, pattern
                    ):
                        is_excluded = True
                        break

            if not is_excluded:
                final_list.append(p)

        return final_list

    def get_inventory_for_ui(
        self,
        project_path: Path,
        manifest: PackageManifest,
        protocol_excludes: List[str],
    ) -> List[dict]:
        """
        Returns a flat list of all files with their inclusion status and reasons.
        Reads from SQLite cache instead of re-scanning the disk.
        """
        from opendata.storage.project_db import ProjectInventoryDB

        db_path = self.workspace.get_project_db_path(manifest.project_id)
        if not db_path.exists():
            # If DB doesn't exist, we return empty list.
            # User must click "Analyze Directory" to populate it.
            return []

        db = ProjectInventoryDB(db_path)
        physical_files = db.get_inventory()
        inventory = []

        for f in physical_files:
            rel_path = f["path"]
            filename = Path(rel_path).name

            # Determine default status from protocol
            is_proto_excluded = False
            if protocol_excludes:
                for pattern in protocol_excludes:
                    if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(
                        rel_path, pattern
                    ):
                        is_proto_excluded = True
                        break

            # Apply overrides
            is_included = not is_proto_excluded
            reason = "📜 Protocol" if is_proto_excluded else "✅ Default"

            if rel_path in manifest.force_include:
                is_included = True
                reason = "👤 User (Forced)"
            elif rel_path in manifest.force_exclude:
                is_included = False
                reason = "👤 User (Excluded)"

            inventory.append(
                {
                    "path": rel_path,
                    "size": f["size"],
                    "included": is_included,
                    "reason": reason,
                    "is_proto_excluded": is_proto_excluded,
                }
            )

        return inventory
