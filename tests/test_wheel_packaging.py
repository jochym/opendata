"""Test wheel packaging to ensure all required data files are included.

Note: These tests are marked as local_only because they modify sys.path
which can interfere with other tests when run in the same session.
"""

import zipfile
from pathlib import Path
import tempfile
import shutil
import sys
import pytest


@pytest.mark.local_only
def get_wheel_path():
    """Find the built wheel file."""
    dist_dir = Path("dist")
    if not dist_dir.exists():
        pytest.skip("No dist directory found. Run 'python -m build --wheel' first.")

    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        pytest.skip(
            "No wheel file found in dist/. Run 'python -m build --wheel' first."
        )

    return wheels[0]


def extract_wheel(wheel_path):
    """Extract wheel to a temporary directory."""
    test_dir = Path(tempfile.mkdtemp())
    try:
        with zipfile.ZipFile(wheel_path, "r") as z:
            z.extractall(test_dir)
        yield test_dir
    finally:
        shutil.rmtree(test_dir)


@pytest.mark.local_only
class TestWheelContents:
    """Test that wheel contains all required data files."""

    def test_version_file_included(self):
        """VERSION file must be included in wheel."""
        wheel_path = get_wheel_path()
        with zipfile.ZipFile(wheel_path, "r") as z:
            names = z.namelist()
            assert "opendata/VERSION" in names, "VERSION file missing from wheel"

    def test_client_secrets_included(self):
        """client_secrets.json must be included in wheel."""
        wheel_path = get_wheel_path()
        with zipfile.ZipFile(wheel_path, "r") as z:
            names = z.namelist()
            assert "opendata/client_secrets.json" in names, (
                "client_secrets.json missing from wheel"
            )

    def test_prompt_templates_included(self):
        """All prompt templates must be included in wheel."""
        wheel_path = get_wheel_path()
        required_prompts = [
            "opendata/prompts/chat_wrapper.md",
            "opendata/prompts/system_prompt_curator.md",
            "opendata/prompts/system_prompt_metadata.md",
            "opendata/prompts/full_text_extraction.md",
        ]
        with zipfile.ZipFile(wheel_path, "r") as z:
            names = z.namelist()
            for prompt in required_prompts:
                assert prompt in names, f"Prompt template {prompt} missing from wheel"

    def test_field_protocols_included(self):
        """Field protocol YAML files must be included in wheel."""
        wheel_path = get_wheel_path()
        with zipfile.ZipFile(wheel_path, "r") as z:
            names = z.namelist()
            # Check for at least one field protocol
            field_protocols = [
                n for n in names if "protocols/fields/" in n and n.endswith(".yaml")
            ]
            assert len(field_protocols) > 0, "No field protocol YAML files in wheel"
            assert "opendata/protocols/fields/physics.yaml" in names, (
                "physics.yaml missing from wheel"
            )


@pytest.mark.local_only
class TestWheelResourceAccess:
    """Test that resources are accessible after wheel installation."""

    def test_get_resource_path_client_secrets(self):
        """get_resource_path should find client_secrets.json in installed wheel."""
        wheel_path = get_wheel_path()
        test_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(wheel_path, "r") as z:
                z.extractall(test_dir)

            sys.path.insert(0, str(test_dir))

            # Force fresh import to avoid caching
            for mod in list(sys.modules.keys()):
                if mod.startswith("opendata"):
                    del sys.modules[mod]

            from opendata.utils import get_resource_path

            p = get_resource_path("client_secrets.json")
            assert p.exists(), f"client_secrets.json not found at {p}"
        finally:
            shutil.rmtree(test_dir)
            if str(test_dir) in sys.path:
                sys.path.remove(str(test_dir))

    def test_get_resource_path_prompts(self):
        """get_resource_path should find prompts directory in installed wheel."""
        wheel_path = get_wheel_path()
        test_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(wheel_path, "r") as z:
                z.extractall(test_dir)

            sys.path.insert(0, str(test_dir))

            # Force fresh import to avoid caching
            for mod in list(sys.modules.keys()):
                if mod.startswith("opendata"):
                    del sys.modules[mod]

            from opendata.utils import get_resource_path

            p = get_resource_path("src/opendata/prompts")
            assert p.exists(), f"prompts directory not found at {p}"
            assert p.is_dir(), "prompts path is not a directory"
        finally:
            shutil.rmtree(test_dir)
            if str(test_dir) in sys.path:
                sys.path.remove(str(test_dir))

    def test_get_resource_path_version(self):
        """get_resource_path should find VERSION file in installed wheel."""
        wheel_path = get_wheel_path()
        test_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(wheel_path, "r") as z:
                z.extractall(test_dir)

            sys.path.insert(0, str(test_dir))

            # Force fresh import to avoid caching
            for mod in list(sys.modules.keys()):
                if mod.startswith("opendata"):
                    del sys.modules[mod]

            from opendata.utils import get_resource_path

            p = get_resource_path("src/opendata/VERSION")
            assert p.exists(), f"VERSION file not found at {p}"
        finally:
            shutil.rmtree(test_dir)
            if str(test_dir) in sys.path:
                sys.path.remove(str(test_dir))

    def test_get_resource_path_field_protocols(self):
        """get_resource_path should find field protocol files in installed wheel."""
        wheel_path = get_wheel_path()
        test_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(wheel_path, "r") as z:
                z.extractall(test_dir)

            sys.path.insert(0, str(test_dir))

            # Force fresh import to avoid caching
            for mod in list(sys.modules.keys()):
                if mod.startswith("opendata"):
                    del sys.modules[mod]

            from opendata.utils import get_resource_path

            p = get_resource_path("src/opendata/protocols/fields/physics.yaml")
            assert p.exists(), f"physics.yaml not found at {p}"
        finally:
            shutil.rmtree(test_dir)
            if str(test_dir) in sys.path:
                sys.path.remove(str(test_dir))


@pytest.mark.local_only
class TestPromptManager:
    """Test PromptManager can load templates from wheel."""

    def test_prompt_manager_initialization(self):
        """PromptManager should initialize with prompts from wheel."""
        wheel_path = get_wheel_path()
        test_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(wheel_path, "r") as z:
                z.extractall(test_dir)

            sys.path.insert(0, str(test_dir))

            # Force fresh import to avoid caching
            for mod in list(sys.modules.keys()):
                if mod.startswith("opendata"):
                    del sys.modules[mod]

            from opendata.utils import PromptManager

            pm = PromptManager()
            assert pm.templates_dir.exists(), (
                f"Templates directory not found: {pm.templates_dir}"
            )
        finally:
            shutil.rmtree(test_dir)
            if str(test_dir) in sys.path:
                sys.path.remove(str(test_dir))

    def test_prompt_manager_render_chat_wrapper(self):
        """PromptManager should render chat_wrapper template."""
        wheel_path = get_wheel_path()
        test_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(wheel_path, "r") as z:
                z.extractall(test_dir)

            sys.path.insert(0, str(test_dir))

            # Force fresh import to avoid caching
            for mod in list(sys.modules.keys()):
                if mod.startswith("opendata"):
                    del sys.modules[mod]

            from opendata.utils import PromptManager

            pm = PromptManager()
            # Render with minimal context
            result = pm.render(
                "chat_wrapper",
                {"messages": [], "context": {}, "history": [], "user_input": ""},
            )
            assert len(result) > 0, "chat_wrapper template rendered empty"
        finally:
            shutil.rmtree(test_dir)
            if str(test_dir) in sys.path:
                sys.path.remove(str(test_dir))
