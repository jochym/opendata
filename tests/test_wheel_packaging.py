"""Test wheel packaging to ensure all required data files are included.

Note: These tests are marked as local_only because they modify sys.path
which can interfere with other tests when run in the same session.
"""

import zipfile
from pathlib import Path
import tempfile
import shutil
import sys
import subprocess
import pytest


@pytest.fixture(scope="session")
def built_wheel():
    """Build wheel before testing.

    This fixture ensures a fresh wheel is built before running packaging tests.
    It cleans old builds, builds the wheel, and yields the wheel path.
    """
    dist_dir = Path("dist")
    build_dir = Path("build")

    # Clean old builds
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)

    # Build wheel
    print("\n🔨 Building wheel for packaging tests...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "build", "--wheel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to build wheel: {e}")
    except FileNotFoundError:
        pytest.fail("Build tool not found. Install with: pip install build")

    # Find wheel
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        pytest.fail("No wheel file found in dist/ after build")

    print(f"✅ Wheel built: {wheels[0].name}")
    yield wheels[0]

    # Cleanup (optional - comment out to inspect wheel)
    # if dist_dir.exists():
    #     shutil.rmtree(dist_dir)
    # if build_dir.exists():
    #     shutil.rmtree(build_dir)


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

    def test_version_file_included(self, built_wheel):
        """VERSION file must be included in wheel."""
        with zipfile.ZipFile(built_wheel, "r") as z:
            names = z.namelist()
            assert "opendata/VERSION" in names, "VERSION file missing from wheel"

    def test_client_secrets_included(self, built_wheel):
        """client_secrets.json must be included in wheel."""
        with zipfile.ZipFile(built_wheel, "r") as z:
            names = z.namelist()
            assert "opendata/client_secrets.json" in names, (
                "client_secrets.json missing from wheel"
            )

    def test_prompt_templates_included(self, built_wheel):
        """All prompt templates must be included in wheel."""
        required_prompts = [
            "opendata/prompts/chat_wrapper.md",
            "opendata/prompts/system_prompt_curator.md",
            "opendata/prompts/system_prompt_metadata.md",
            "opendata/prompts/full_text_extraction.md",
        ]
        with zipfile.ZipFile(built_wheel, "r") as z:
            names = z.namelist()
            for prompt in required_prompts:
                assert prompt in names, f"Prompt template {prompt} missing from wheel"

    def test_field_protocols_included(self, built_wheel):
        """Field protocol YAML files must be included in wheel."""
        with zipfile.ZipFile(built_wheel, "r") as z:
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

    def test_get_resource_path_client_secrets(self, built_wheel):
        """get_resource_path should find client_secrets.json in installed wheel."""
        test_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(built_wheel, "r") as z:
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

    def test_get_resource_path_prompts(self, built_wheel):
        """get_resource_path should find prompts directory in installed wheel."""
        test_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(built_wheel, "r") as z:
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

    def test_get_resource_path_version(self, built_wheel):
        """get_resource_path should find VERSION file in installed wheel."""
        test_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(built_wheel, "r") as z:
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

    def test_get_resource_path_field_protocols(self, built_wheel):
        """get_resource_path should find field protocol files in installed wheel."""
        test_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(built_wheel, "r") as z:
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

    def test_prompt_manager_initialization(self, built_wheel):
        """PromptManager should initialize with prompts from wheel."""
        test_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(built_wheel, "r") as z:
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

    def test_prompt_manager_render_chat_wrapper(self, built_wheel):
        """PromptManager should render chat_wrapper template."""
        test_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(built_wheel, "r") as z:
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
