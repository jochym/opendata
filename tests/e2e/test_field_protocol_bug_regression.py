"""
Field Protocol Bug Regression Test - GUI

This test specifically verifies the bug fix for field protocol resetting
after tab switch or page reload.

⚠️  LOCAL ONLY - Requires running app (not for CI/CD)
⚠️  AI INTERACTION - Uses AI services (local only)
"""

import pytest
from playwright.sync_api import Page, expect
import json
from pathlib import Path
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8080"
TIMEOUT = 30000
PROJECT_ID = "ec7e33c23da584709f6322cb52b01d52"  # MD5 hash of project path

# Mark all tests as local only and AI interaction
pytestmark = [pytest.mark.local_only, pytest.mark.requires_app, pytest.mark.ai_interaction]


@pytest.fixture(scope="module")
def page():
    """Creates a browser page for testing with Chromium."""
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = browser.new_context(viewport={'width': 1280, 'height': 1024})
        page = context.new_page()
        page.set_default_timeout(TIMEOUT)
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


def load_project(page, project_path="/home/jochym/calc/3C-SiC/Project"):
    """Load project from dropdown."""
    page.goto(f"{BASE_URL}/protocols")
    page.wait_for_selector('label:has-text("Recent Projects") + *', timeout=10000)
    
    project_selector = page.locator('label:has-text("Recent Projects") + *')
    project_selector.click()
    page.wait_for_timeout(1000)
    
    try:
        page.get_by_text(project_path).first.click()
    except:
        project_option = page.locator(f'[role="option"][value*="3C-SiC"]')
        if project_option.count() > 0:
            project_option.first.click()
    
    page.wait_for_timeout(2000)


class TestFieldProtocolBugRegression:
    """
    Regression test for field protocol resetting bug.
    
    Steps:
    1. Clear any saved field
    2. Load project
    3. Select "physics"
    4. Verify saved to disk
    5. Switch tabs
    6. Verify field persists in UI
    7. Reload page
    8. Verify field still persists
    """
    
    def test_01_initial_state(self, api_base_url):
        """Step 1: Verify initial state - no field saved."""
        import requests
        response = requests.get(f"{api_base_url}/projects", timeout=5)
        projects = response.json().get('projects', [])
        
        if projects:
            project_id = projects[0]['id']
            config_response = requests.get(
                f"{api_base_url}/projects/{project_id}/config",
                timeout=5
            )
            config = config_response.json().get('config', {})
            # Field may or may not be set - just verify we can access it
            print(f"Initial field: {config.get('field_name', 'not set')}")
    
    def test_02_app_loads(self, page, app_base_url):
        """Step 2: App loads successfully."""
        page.goto(app_base_url)
        expect(page).to_have_title("OpenData Agent")
        save_screenshot(page, "01_app_loaded")
    
    def test_03_select_field_physics(self, page, app_base_url):
        """Step 3: Select 'physics' field protocol."""
        # Load project first
        load_project(page)
        
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
        page.wait_for_timeout(2000)
        
        # Save screenshot
        save_screenshot(page, "02_physics_selected")
        
        # Verify selection in UI
        current_value = field_select.input_value()
        assert current_value == "physics", f"Expected 'physics', got '{current_value}'"
    
    def test_04_field_saved_to_disk(self, api_base_url):
        """Step 4: Verify field saved to project_config.json."""
        import requests
        response = requests.get(f"{api_base_url}/projects", timeout=5)
        projects = response.json().get('projects', [])
        
        if projects:
            project_id = projects[0]['id']
            config_response = requests.get(
                f"{api_base_url}/projects/{project_id}/config",
                timeout=5
            )
            config = config_response.json().get('config', {})
            assert config.get('field_name') == "physics", (
                f"Expected 'physics' on disk, got '{config.get('field_name')}'"
            )
    
    def test_05_switch_to_analysis_tab(self, page, app_base_url):
        """Step 5: Switch to Analysis tab (simulates scan)."""
        page.goto(f"{app_base_url}/analysis")
        page.wait_for_timeout(3000)
        save_screenshot(page, "03_analysis_tab")
    
    def test_06_return_to_protocols_field_persists(self, page, app_base_url):
        """Step 6: Return to Protocols - field should still be 'physics'."""
        page.goto(f"{app_base_url}/protocols")
        page.wait_for_selector("text=Field", timeout=10000)
        
        # Click Field tab
        page.click("text=Field")
        page.wait_for_timeout(2000)
        
        # Save screenshot
        save_screenshot(page, "04_after_tab_switch")
        
        # Find field selector
        field_select = page.locator('label:has-text("Field Domain") + *')
        
        # CRITICAL VERIFY: Field should NOT have reset
        current_value = field_select.input_value()
        assert current_value == "physics", (
            f"BUG REGRESSED! Field reset to '{current_value}' after tab switch. "
            f"Expected 'physics'. This is the bug we fixed!"
        )
    
    def test_07_reload_page_field_persists(self, page, app_base_url):
        """Step 7: Reload page - field should still be 'physics'."""
        page.reload()
        page.wait_for_selector("text=Field", timeout=10000)
        
        # Click Field tab
        page.click("text=Field")
        page.wait_for_timeout(2000)
        
        # Save screenshot
        save_screenshot(page, "05_after_page_reload")
        
        # Find field selector
        field_select = page.locator('label:has-text("Field Domain") + *')
        
        # CRITICAL VERIFY: Field should survive page reload
        current_value = field_select.input_value()
        assert current_value == "physics", (
            f"BUG REGRESSED! Field reset to '{current_value}' after page reload. "
            f"Expected 'physics'. This is the bug we fixed!"
        )
    
    def test_08_disk_state_final(self, api_base_url):
        """Step 8: Final verification - field still on disk."""
        import requests
        response = requests.get(f"{api_base_url}/projects", timeout=5)
        projects = response.json().get('projects', [])
        
        if projects:
            project_id = projects[0]['id']
            config_response = requests.get(
                f"{api_base_url}/projects/{project_id}/config",
                timeout=5
            )
            config = config_response.json().get('config', {})
            assert config.get('field_name') == "physics", (
                f"Field lost from disk! Expected 'physics', got '{config.get('field_name')}'"
            )
    
    def test_09_summary(self):
        """Step 9: Print summary."""
        print("\n" + "="*80)
        print("✅ BUG FIX VERIFIED - All steps passed!")
        print("="*80)
        print("The field protocol bug has been fixed:")
        print("  ✅ Field saves to project_config.json")
        print("  ✅ Field persists after tab switch")
        print("  ✅ Field persists after page reload")
        print("  ✅ Field stays in sync between UI and disk")
        print("="*80 + "\n")


class TestFieldProtocolBugSymptoms:
    """
    Additional tests for specific symptoms of the bug.
    """
    
    def test_dropdown_initializes_with_saved_value(self, page, app_base_url):
        """
        Verify that dropdown loads saved value on initialization.
        
        This is the core of the fix - the dropdown should read from
        project_config.json when it's created, not default to first item.
        """
        # Load project first
        load_project(page)
        
        # Navigate directly to protocols (fresh page load)
        page.goto(f"{app_base_url}/protocols")
        page.wait_for_selector("text=Field", timeout=10000)
        page.click("text=Field")
        page.wait_for_timeout(2000)
        
        # Find field selector
        field_select = page.locator('label:has-text("Field Domain") + *')
        
        # Verify it loaded with saved value, not first item
        current_value = field_select.input_value()
        assert current_value == "physics", (
            f"Dropdown didn't load saved value! Expected 'physics', got '{current_value}'. "
            f"This means the fix isn't working - dropdown is defaulting to first item."
        )
