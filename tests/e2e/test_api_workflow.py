#!/usr/bin/env python3
"""API Test Script for Field Protocol Workflow"""

import pytest
import requests
import time
from pathlib import Path

pytestmark = [pytest.mark.local_only, pytest.mark.requires_app]

BASE_URL = "http://127.0.0.1:8080/api"
PROJECT_PATH = "/home/jochym/calc/3C-SiC/Project"


def test_api_available(app_with_api, api_base_url, app_base_url):
    """Test 1: Verify API is available"""
    print("\n=== Test 1: API Availability ===")
    print(f"App base URL: {app_base_url}")
    print(f"API base URL: {api_base_url}")
    
    # First check main page
    main_response = requests.get(app_base_url, timeout=5)
    print(f"Main page status: {main_response.status_code}")
    
    # Check API with retries
    for i in range(5):
        try:
            response = requests.get(f"{api_base_url}/projects", timeout=5)
            print(f"Attempt {i+1}: API status {response.status_code}")
            if response.status_code == 200:
                print(f"✅ API is available! Response: {response.json()}")
                return
            elif response.status_code == 404:
                print(f"⏳ Attempt {i+1}: 404 - API routes not ready, waiting...")
                time.sleep(3)
        except Exception as e:
            print(f"⏳ Attempt {i+1}: Error - {e}")
            time.sleep(3)
    
    pytest.fail(f"API not available after 5 attempts")
