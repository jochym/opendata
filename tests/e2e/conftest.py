"""
Test Configuration and Fixtures for E2E Tests

Provides fixtures for automated project loading and API access.
"""

import pytest
import requests
from pathlib import Path
import time


# Configuration
BASE_URL = "http://127.0.0.1:8080"
API_TIMEOUT = 10


@pytest.fixture(scope="session")
def api_base_url():
    """Returns the base URL for API calls."""
    return BASE_URL


@pytest.fixture(scope="session")
def test_project_path():
    """Returns the path to the test project (uses realistic fixture)."""
    # Use the realistic project fixture instead of hardcoded path
    fixture_path = (
        Path(__file__).parent.parent / "fixtures" / "realistic_projects" / "3C-SiC"
    )
    if fixture_path.exists():
        return fixture_path

    # Fallback to old path for backward compatibility
    return Path("/home/jochym/calc/3C-SiC/Project")


@pytest.fixture(scope="function")
def preloaded_project(page):
    """
    Hybrid fixture for project loading.

    Automatically loads the test project via API before each test.
    Can be overridden by setting request.param for custom loading.

    Usage:
        # Auto-load default project
        def test_something(page, preloaded_project):
            pass

        # Skip auto-loading (manual control)
        @pytest.mark.parametrize("preloaded_project", [None], indirect=True)
        def test_custom_load(page, preloaded_project):
            # Manual loading logic here
            pass
    """
    # Check if test wants to skip auto-loading
    if hasattr(preloaded_project, "param") and preloaded_project.param is None:
        yield page
        return

    # Auto-load project via API
    try:
        # Get project path from fixture
        fixture_path = (
            Path(__file__).parent.parent / "fixtures" / "realistic_projects" / "3C-SiC"
        )
        project_path = (
            str(fixture_path)
            if fixture_path.exists()
            else "/home/jochym/calc/3C-SiC/Project"
        )

        response = requests.post(
            f"{BASE_URL}/api/projects/load",
            json={"project_path": project_path},
            timeout=API_TIMEOUT,
        )

        if response.status_code == 200:
            project_data = response.json()
            print(f"✅ Project loaded via API: {project_data['project_id']}")

            # Wait for UI to update
            page.wait_for_timeout(2000)

            # Verify project is loaded
            page.goto(f"{BASE_URL}/protocols")
            page.wait_for_selector("text=Protocols", timeout=5000)

            yield page
        else:
            print(f"⚠️  API returned {response.status_code}: {response.text}")
            yield page

    except requests.exceptions.ConnectionError:
        print("⚠️  API not available, skipping auto-load")
        yield page
    except Exception as e:
        print(f"⚠️  Error loading project: {e}")
        yield page


@pytest.fixture(scope="function")
def field_protocol_config(page, preloaded_project):
    """
    Fixture for managing field protocol configuration via API.

    Usage:
        def test_field_protocol(page, field_protocol_config):
            # Set field protocol
            field_protocol_config.set("physics")

            # Get current config
            config = field_protocol_config.get()
    """

    class FieldProtocolManager:
        def __init__(self, page):
            self.page = page
            self.project_id = self._get_project_id()

        def _get_project_id(self):
            """Get current project ID from API"""
            try:
                response = requests.get(f"{BASE_URL}/api/projects", timeout=5)
                projects = response.json().get("projects", [])
                return projects[0]["id"] if projects else None
            except:
                return None

        def set(self, field_name: str):
            """Set field protocol"""
            if not self.project_id:
                raise RuntimeError("No project loaded")

            response = requests.post(
                f"{BASE_URL}/api/projects/{self.project_id}/field-protocol",
                params={"field_name": field_name},
                timeout=5,
            )
            response.raise_for_status()
            return response.json()

        def get(self):
            """Get current field protocol"""
            if not self.project_id:
                return None

            response = requests.get(
                f"{BASE_URL}/api/projects/{self.project_id}/config", timeout=5
            )
            response.raise_for_status()
            config = response.json().get("config", {})
            return config.get("field_name")

    return FieldProtocolManager(page)


@pytest.fixture(scope="session")
def api_session():
    """Creates a requests session for API calls."""
    session = requests.Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def api_project(api_session):
    """
    Fixture for project CRUD operations via API.

    Usage:
        def test_project_api(api_project):
            # List projects
            projects = api_project.list()

            # Get project details
            project = api_project.get(project_id)

            # Get/set config
            config = api_project.get_config(project_id)
            api_project.set_config(project_id, {"field_name": "physics"})
    """

    class ProjectAPI:
        def __init__(self, session):
            self.session = session
            self.base_url = BASE_URL

        def list(self):
            """List all projects"""
            response = self.session.get(f"{self.base_url}/api/projects", timeout=5)
            response.raise_for_status()
            return response.json().get("projects", [])

        def get(self, project_id: str):
            """Get project details"""
            response = self.session.get(
                f"{self.base_url}/api/projects/{project_id}", timeout=5
            )
            response.raise_for_status()
            return response.json()

        def get_config(self, project_id: str):
            """Get project configuration"""
            response = self.session.get(
                f"{self.base_url}/api/projects/{project_id}/config", timeout=5
            )
            response.raise_for_status()
            return response.json().get("config", {})

        def set_config(self, project_id: str, config: dict):
            """Update project configuration"""
            response = self.session.put(
                f"{self.base_url}/api/projects/{project_id}/config",
                json=config,
                timeout=5,
            )
            response.raise_for_status()
            return response.json()

        def set_field_protocol(self, project_id: str, field_name: str):
            """Set field protocol"""
            response = self.session.post(
                f"{self.base_url}/api/projects/{project_id}/field-protocol",
                params={"field_name": field_name},
                timeout=5,
            )
            response.raise_for_status()
            return response.json()

    return ProjectAPI(api_session)
