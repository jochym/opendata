"""
Global pytest fixtures for OpenData Tool tests.

For E2E tests, use the automated runner:
    ./tests/run_e2e_tests.sh

This will automatically start the app, run tests, and clean up.
"""

import pytest
import os
import requests
from pathlib import Path


@pytest.fixture(scope="session")
def app_with_api():
    """
    Fixture that verifies app is running.
    
    When using ./tests/run_e2e_tests.sh, the app is started automatically.
    This fixture just verifies it's running and ready.
    """
    print("\n🔍 Verifying app is running...")
    
    # Check if app is running
    for attempt in range(10):
        try:
            response = requests.get("http://127.0.0.1:8080/", timeout=2)
            if response.status_code == 200:
                # Check API
                api_response = requests.get("http://127.0.0.1:8080/api/projects", timeout=2)
                if api_response.status_code == 200:
                    print("✅ App and API are running and ready!")
                    yield None
                    return
                print(f"⏳ API not ready yet (status: {api_response.status_code})")
        except Exception as e:
            print(f"⏳ App not ready yet: {e}")
        import time
        time.sleep(2)
    
    # App not running
    pytest.fail(
        "App is not running! Use the automated test runner:\n"
        "  ./tests/run_e2e_tests.sh\n"
        "\nOr start app manually:\n"
        "  python src/opendata/main.py --headless --api --port 8080 &"
    )


@pytest.fixture(scope="session")
def api_base_url():
    return "http://127.0.0.1:8080/api"


@pytest.fixture(scope="session")
def app_base_url():
    return "http://127.0.0.1:8080"


@pytest.fixture(scope="function")
def api_session():
    session = requests.Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def real_project_paths():
    paths = {
        "3C-SiC": Path.home() / "calc" / "3C-SiC" / "Project",
        "fesi": Path.home() / "calc" / "fesi" / "Project",
    }
    return {name: (path if path.exists() else None) for name, path in paths.items()}


def pytest_configure(config):
    config.addinivalue_line("markers", "local_only: Tests that require local environment")
    config.addinivalue_line("markers", "ai_interaction: Tests that use AI services")
    config.addinivalue_line("markers", "requires_app: Tests that require the app running")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.local_only)
        if "app_with_api" in item.fixturenames:
            item.add_marker(pytest.mark.requires_app)
            item.add_marker(pytest.mark.local_only)
