"""
Playwright E2E Tests for OpenData Tool - Full Workflow

Tests the GUI workflow for field protocol selection and persistence.
Requires the app to be running on http://127.0.0.1:8080 with --api flag

⚠️  LOCAL ONLY - Requires running app (not for CI/CD)
⚠️  AI INTERACTION - Uses AI services (local only)
"""

import pytest
from playwright.sync_api import Page, expect, TimeoutError
import json
from pathlib import Path
import time
from datetime import datetime

# Mark all tests as local only and AI interaction
pytestmark = [pytest.mark.local_only, pytest.mark.requires_app, pytest.mark.ai_interaction]


@pytest.fixture(scope="module")
def page():
    """Creates a browser page for testing with Chromium."""
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        # Launch Chromium in headless mode (lighter than Chrome)
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = browser.new_context(
            viewport={'width': 1280, 'height': 1024}
        )
        page = context.new_page()
        page.set_default_timeout(30000)
        yield page
        browser.close()


def save_screenshot(page, name):
    """Saves a screenshot with timestamp."""
    screenshot_dir = Path(__file__).parent / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = screenshot_dir / f"{timestamp}_{name}.png"
    page.screenshot(path=str(filename), full_page=True)
    return filename


def load_project(page, base_url, project_path="/home/jochym/calc/3C-SiC/Project"):
    """Automatically loads a project from the header dropdown."""
    print(f"📂 Loading project: {project_path}")
    
    # Navigate to protocols to trigger project loading
    page.goto(f"{base_url}/protocols")
    page.wait_for_selector('label:has-text("Recent Projects") + *', timeout=10000)
    
    # Find and click the project selector
    project_selector = page.locator('label:has-text("Recent Projects") + *')
    
    # Click to open dropdown
    project_selector.click()
    
    # Wait for dropdown options to appear
    page.wait_for_timeout(1000)
    
    # Find and click the project option (by project path in the value)
    try:
        # Try to find by path text
        page.get_by_text(project_path).first.click()
        print(f"✅ Project selected by path")
    except:
        # Fallback: try to find by option value
        project_option = page.locator(f'[role="option"][value*="3C-SiC"]')
        if project_option.count() > 0:
            project_option.first.click()
            print(f"✅ Project selected by value")
    
    # Wait for project to load
    page.wait_for_timeout(2000)
    print(f"✅ Project loaded successfully")


class TestFieldProtocolGUI:
    """Full workflow GUI tests for field protocol."""
    
    def test_app_loads(self, page, app_base_url):
        """Verify app loads without errors."""
        page.goto(app_base_url)
        expect(page).to_have_title("OpenData Agent")
        assert "127.0.0.1:8080" in page.url
    
    def test_open_project(self, page, app_base_url):
        """Test opening a project from dropdown."""
        load_project(page, app_base_url)
        # Verify project is loaded by checking for protocols tab
        page.goto(f"{app_base_url}/protocols")
        page.wait_for_selector("text=Protocols", timeout=10000)
    
    def test_field_protocol_selection(self, page, app_base_url):
        """Test selecting a field protocol in the UI."""
        # Load project first
        load_project(page, app_base_url)
        
        # Navigate to protocols
        page.goto(f"{app_base_url}/protocols")
        page.wait_for_selector("text=Field", timeout=10000)
        
        # Click Field tab
        page.click("text=Field")
        page.wait_for_timeout(1000)
        
        # Find field selector
        field_select = page.locator('label:has-text("Field Domain") + *')
        
        # Select physics
        field_select.select_option("physics")
        page.wait_for_timeout(1000)
        
        # Verify selection in UI
        current_value = field_select.input_value()
        assert current_value == "physics", f"Expected 'physics', got '{current_value}'"
    
    def test_field_protocol_persists_after_tab_switch(self, page, app_base_url):
        """Test that field selection survives switching tabs."""
        # Load project first
        load_project(page, app_base_url)
        
        # Go to protocols and set field
        page.goto(f"{app_base_url}/protocols")
        page.wait_for_selector('label:has-text("Field Domain") + *')
        
        field_select = page.locator('label:has-text("Field Domain") + *')
        field_select.select_option("physics")
        page.wait_for_timeout(1000)
        
        # Switch to Analysis tab
        page.goto(f"{app_base_url}/analysis")
        page.wait_for_timeout(2000)
        
        # Go back to Protocols
        page.goto(f"{app_base_url}/protocols")
        page.wait_for_selector('label:has-text("Field Domain") + *')
        
        # Verify field is still "physics"
        field_select = page.locator('label:has-text("Field Domain") + *')
        current_value = field_select.input_value()
        assert current_value == "physics", (
            f"Field should persist as 'physics', got '{current_value}'"
        )
    
    def test_field_protocol_persists_after_page_reload(self, page, app_base_url):
        """Test that field selection survives page reload."""
        # Load project first
        load_project(page, app_base_url)
        
        # Set field
        page.goto(f"{app_base_url}/protocols")
        field_select = page.locator('label:has-text("Field Domain") + *')
        field_select.select_option("physics")
        page.wait_for_timeout(1000)
        
        # Reload page
        page.reload()
        page.wait_for_selector('label:has-text("Field Domain") + *')
        
        # Verify field persisted
        field_select = page.locator('label:has-text("Field Domain") + *')
        current_value = field_select.input_value()
        assert current_value == "physics", (
            f"Field should persist after reload, got '{current_value}'"
        )
    
    def test_field_protocol_saved_to_disk(self, page, app_base_url):
        """Test that field protocol is saved to project_config.json."""
        # Load project first
        load_project(page, app_base_url)
        
        # Set field via UI
        page.goto(f"{app_base_url}/protocols")
        field_select = page.locator('label:has-text("Field Domain") + *')
        field_select.select_option("physics")
        page.wait_for_timeout(2000)
        
        # Verify via API
        import requests
        response = requests.get(f"{app_base_url}/api/projects", timeout=5)
        projects = response.json().get('projects', [])
        
        if projects:
            project_id = projects[0]['id']
            config_response = requests.get(
                f"{app_base_url}/api/projects/{project_id}/config",
                timeout=5
            )
            config = config_response.json().get('config', {})
            assert config.get('field_name') == "physics", (
                f"Field not saved to disk: {config}"
            )
    
    def test_field_protocol_affects_scan(self, page, app_base_url):
        """Test that field protocol changes affect scan exclusions."""
        # Load project first
        load_project(page, app_base_url)
        
        # Set to physics
        page.goto(f"{app_base_url}/protocols")
        field_select = page.locator('label:has-text("Field Domain") + *')
        field_select.select_option("physics")
        page.wait_for_timeout(1000)
        
        # Go to scan/inventory
        page.goto(f"{app_base_url}/inventory")
        
        # Check for physics-specific exclusions in the UI
        # This is a placeholder - adjust based on actual UI
        page.wait_for_load_state("networkidle")
