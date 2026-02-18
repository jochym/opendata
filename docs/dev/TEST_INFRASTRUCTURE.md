# Test Infrastructure - Developer Guide

**For:** Developers working on OpenData Tool  
**Last Updated:** February 18, 2026

---

## Architecture Overview

### Test Layers

```
┌─────────────────────────────────────┐
│         E2E Tests (1 test)          │
│  Complete workflow with real AI     │
│  ~62 seconds                        │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│       AI Integration (4 tests)      │
│  Provider, telemetry, parsing       │
│  ~3 seconds                         │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│      Integration (5 tests)          │
│  Component interactions             │
│  ~1 second                          │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│         Unit (42 tests)             │
│  Isolated component tests           │
│  ~1 second                          │
└─────────────────────────────────────┘
```

### File Structure

```
tests/
├── conftest.py              # Pytest fixtures
├── run_all_tests.sh         # Automated test runner
├── run_e2e_tests.sh         # E2E test runner
├── start_app_for_tests.sh   # Manual app start helper
├── stop_app_for_tests.sh    # Manual app stop helper
│
├── unit/                    # Unit tests
│   ├── agents/              # Agent logic tests
│   ├── ai/                  # AI provider tests
│   ├── models/              # Model validation tests
│   └── protocols/           # Protocol manager tests
│
├── integration/             # Integration tests
│   ├── test_workspace_io.py
│   └── test_realistic_projects.py
│
└── end_to_end/              # E2E tests
    └── test_full_workflow.py
```

---

## Key Components

### 1. Pytest Fixtures (`tests/conftest.py`)

**`app_with_api`** - Verifies app is running
```python
@pytest.fixture(scope="session")
def app_with_api():
    """Verifies app is running and ready."""
    # Checks if app responds
    # Checks if API endpoints work
    # Yields control to tests
```

**Usage:**
```python
def test_something(app_with_api, api_session, api_base_url):
    response = api_session.get(f"{api_base_url}/projects")
    assert response.status_code == 200
```

### 2. API Routes (`src/opendata/api/projects.py`)

**Registration:**
```python
def register_project_api(ctx):
    app.add_api_route("/api/projects", list_projects, methods=["GET"])
    app.add_api_route("/api/projects/load", load_project, methods=["POST"])
    # ... 5 more endpoints
```

**Endpoints:**
- `GET /api/projects` - List projects
- `POST /api/projects/load` - Load project
- `GET /api/projects/{id}` - Get project
- `GET/PUT /api/projects/{id}/config` - Config
- `POST /api/projects/{id}/field-protocol` - Set field
- `DELETE /api/projects/{id}` - Delete project

### 3. Test Runners

**`tests/run_all_tests.sh`:**
```bash
#!/bin/bash
# 1. Kill existing instances
# 2. Start Xvfb
# 3. Start app with --api
# 4. Wait for app ready
# 5. Run pytest (CI/CD + AI tests)
# 6. Cleanup
```

**`tests/run_e2e_tests.sh`:**
```bash
#!/bin/bash
# 1. Kill existing instances
# 2. Start Xvfb
# 3. Start app with --api
# 4. Wait for app ready
# 5. Run pytest (E2E tests only)
# 6. Cleanup
```

---

## Implementation Details

### Field Protocol System

**Test File:** `tests/unit/agents/test_field_protocol_persistence.py`

**What's Tested:**
1. Field protocol loads from `project_config.json`
2. Field protocol persists to disk
3. Field protocol survives rescans
4. Field protocol affects scan exclusions
5. Field protocol independent from RODBUK metadata
6. NO automatic heuristics (100% user-controlled)
7. User selection persists
8. Field protocol loaded on agent init
9. Empty config returns None

**Key Test:**
```python
def test_field_protocol_no_heuristics_fully_user_controlled():
    """NO automatic heuristics - field protocol is 100% user controlled."""
    # Create fingerprint with obvious physics files
    agent.current_fingerprint = ProjectFingerprint(
        extensions=[".tex", ".born", ".kappa"],  # Physics indicators
    )
    
    # Get effective field (no user selection)
    field = agent._get_effective_field()
    
    # Assert: Returns None - NO automatic detection
    assert field is None
```

### Parsing System

**Test Files:**
- `tests/unit/agents/test_parsing.py` - Basic parsing
- `tests/unit/agents/test_parsing_correctness.py` - Correctness tests
- `tests/unit/agents/test_parsing_robustness.py` - Edge cases

**What's Tested:**
- Funding normalization (string → dict)
- Contributors mapping to notes
- Non-compliant dict normalization
- Related publications authors list → string
- Author string → PersonOrOrg conversion
- Contact normalization
- Locked fields handling
- Edge cases (nested braces, malformed JSON)

**Key Test:**
```python
def test_funding_normalization_string():
    """AI sending funding as string should be normalized to dict."""
    ai_response = """
    METADATA: {
      "funding": ["National Science Centre UMO-2014/13/B/ST3/04393"]
    }
    """
    
    _, _, metadata = extract_metadata_from_ai_response(ai_response, Metadata())
    
    assert metadata.funding[0]["agency"] == "National Science Centre..."
```

### Telemetry System

**Test File:** `tests/unit/ai/test_telemetry.py`

**What's Tested:**
- Unique ID generation
- Prompt sanitization (truncation >500 chars)
- Structured JSONL logging
- ID tag injection (`<!-- OPENDATA_AI_ID: {uuid} -->`)
- ID tag extraction and stripping

**Key Test:**
```python
def test_sanitize_prompt_with_truncation(telemetry):
    """Large file content should be truncated in logs."""
    large_content = "A" * 1000
    prompt = f"--- FILE CONTENT: test.txt ---\n{large_content}\n---"
    
    sanitized = telemetry.sanitize_prompt(prompt)
    
    assert "truncated" in sanitized
    assert "1000 chars" in sanitized
```

---

## Test Markers

### Definition (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
markers = [
    "local_only: Tests that require local environment",
    "ai_interaction: Tests that use AI services",
    "requires_app: Tests that require the app running",
]
```

### Application

**In Test Files:**
```python
# Mark entire file
pytestmark = [pytest.mark.local_only, pytest.mark.ai_interaction]

# Mark individual test
@pytest.mark.ai_interaction
def test_ai_feature():
    pass
```

**Auto-Marking (`tests/conftest.py`):**
```python
def pytest_collection_modifyitems(config, items):
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.local_only)
        if "app_with_api" in item.fixturenames:
            item.add_marker(pytest.mark.requires_app)
            item.add_marker(pytest.mark.local_only)
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install dependencies
        run: pip install -e .[dev]
      
      - name: Run tests (CI/CD safe)
        run: pytest -v
        # Runs 55 tests in ~2 seconds
        # Excludes AI and local tests
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Local CI/CD Simulation

```bash
# Run exactly what CI/CD runs
pytest -v

# Result: 55 tests, ~2 seconds, no AI calls
```

---

## Adding New Tests

### Unit Test Template

```python
import pytest
from opendata.module import function

def test_feature():
    """Test description should specify CORRECT behavior."""
    # Arrange: Set up the scenario
    input_data = {...}
    
    # Act: Perform the action
    result = function(input_data)
    
    # Assert: Verify CORRECT outcome
    assert result == expected_value
```

### AI Test Template

```python
import pytest
from opendata.ai import provider

@pytest.mark.ai_interaction
def test_ai_feature(ai_service):
    """Test AI feature with real AI."""
    # Arrange
    prompt = "Test prompt"
    
    # Act
    response = ai_service.ask_agent(prompt)
    
    # Assert
    assert response is not None
    assert "expected content" in response
```

### E2E Test Template

```python
import pytest
from playwright.sync_api import Page

@pytest.mark.local_only
@pytest.mark.ai_interaction
def test_e2e_feature(page, app_with_api):
    """Test complete user workflow."""
    # Navigate
    page.goto("http://127.0.0.1:8080/")
    
    # Interact
    page.click("text=Button")
    page.fill("input", "value")
    
    # Verify
    expect(page).to_have_text("Expected text")
```

---

## Best Practices

### TDD Principles

1. **Tests Define CORRECT Behavior**
   - Tests specify what SHOULD happen
   - Tests written BEFORE implementation
   - Tests verify user-facing behavior

2. **Bug Fixes Include Tests**
   - Every bug fix has a test
   - Tests target ROOT CAUSE
   - Tests prevent regression

3. **Test Quality**
   - Fast (< 1s for unit tests)
   - Independent (no cross-test contamination)
   - Deterministic (same results every time)
   - Clear docstrings

### What to Test

**DO Test:**
- ✅ Public APIs
- ✅ Edge cases
- ✅ Error handling
- ✅ User-facing behavior
- ✅ Bug fixes

**DON'T Test:**
- ❌ Private methods (test via public API)
- ✅ Current implementation (test CORRECT behavior)
- ❌ Third-party libraries (test our usage)

### Test Naming

```python
# Good: Describes behavior
def test_field_protocol_persists_to_disk():
    pass

# Bad: Describes implementation
def test_save_config():
    pass

# Good: Includes expected outcome
def test_funding_normalization_string_to_dict():
    pass

# Bad: Vague
def test_funding():
    pass
```

---

## Debugging Tests

### Verbose Output

```bash
# Show all output
pytest -v -s

# Show local variables on failure
pytest -l

# Print statements
pytest -s
```

### Specific Tests

```bash
# Run single test
pytest tests/unit/test_file.py::test_function -v

# Run single file
pytest tests/unit/test_file.py -v

# Run by pattern
pytest -k "field_protocol" -v
```

### Coverage

```bash
# Run with coverage
pytest --cov=src/opendata --cov-report=html

# View coverage report
open htmlcov/index.html
```

---

## Performance

### Current Metrics

| Category | Target | Actual | Status |
|----------|--------|--------|--------|
| Unit Tests | < 0.1s each | ~0.02s | ✅ |
| Integration | < 1s each | ~0.2s | ✅ |
| AI Tests | < 5s each | ~0.75s | ✅ |
| E2E | < 120s | ~62s | ✅ |
| CI/CD Total | < 60s | ~2s | ✅ |

### Optimization Tips

1. **Use Mocks for Fast Tests**
   ```python
   def test_with_mock(mocker):
       mock_ai = mocker.patch('opendata.ai.ask_agent')
       mock_ai.return_value = "mocked response"
   ```

2. **Session-Scoped Fixtures**
   ```python
   @pytest.fixture(scope="session")
   def expensive_resource():
       # Created once per test session
       pass
   ```

3. **Parallel Execution** (future)
   ```bash
   pytest -n auto  # Requires pytest-xdist
   ```

---

## Troubleshooting

### Common Issues

**Issue:** Tests hang
```bash
# Solution: Kill processes
pkill -9 -f "main.py"
pkill -9 pytest
pkill -9 Xvfb
```

**Issue:** Port 8080 in use
```bash
# Solution: Find and kill
lsof -i :8080
kill -9 <PID>
```

**Issue:** AI tests fail
```bash
# Solution: Check AI config
cat ~/.opendata_tool/settings.yaml

# Test endpoint
curl http://your-proxy:8317/v1/chat/completions ...
```

**Issue:** Import errors
```bash
# Solution: Install in dev mode
pip install -e .[dev]
```

---

## Documentation

**For Users:**
- `docs/TESTING.md` - Complete testing guide

**For Developers:**
- This document (`docs/TEST_INFRASTRUCTURE.md`)
- `docs/TEST_RESULTS.md` - Test results and coverage

---

**Last Updated:** February 18, 2026  
**Status:** ✅ Production Ready  
**Total Tests:** 60 (all passing)
