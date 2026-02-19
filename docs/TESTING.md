# Testing Infrastructure for OpenData Tool

## Overview

The OpenData Tool testing infrastructure consists of multiple layers to ensure reliability across all supported platforms and use cases. The testing philosophy centers on verifying CORRECT behavior rather than just current implementation.

## Test Categories

### 1. Unit Tests (`tests/unit/`)
- Test individual components in isolation
- Fast execution (< 1 second per test)
- No external dependencies
- Located in `tests/unit/` directory

### 2. Integration Tests (`tests/integration/`)
- Test component interactions
- May require local services
- Located in `tests/integration/` directory

### 3. End-to-End Tests (`tests/e2e/`)
- Test complete user workflows
- May require application to be running
- Located in `tests/e2e/` directory

### 4. AI Interaction Tests (`tests/end_to_end/`)
- Test AI integration functionality
- Require valid API keys
- Located in `tests/end_to_end/` directory

## Test Markers

The test suite uses pytest markers to categorize tests:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests  
- `@pytest.mark.e2e`: End-to-end tests
- `@pytest.mark.ai_interaction`: Tests that use AI services (excluded from CI/CD)
- `@pytest.mark.local_only`: Tests that require local environment (excluded from CI/CD)

## Running Tests

### Basic Test Execution
```bash
# Run all CI/CD safe tests (excludes AI and local tests)
pytest

# Run all tests including AI and local (requires configuration)
pytest -m ""

# Run only unit tests
pytest -m "unit"

# Run only end-to-end tests
pytest -m "e2e"
```

### Test Configuration

The default pytest configuration excludes AI interaction and local-only tests:

```ini
# In pyproject.toml
addopts = "-m 'not ai_interaction and not local_only'"
```

This ensures CI/CD runs safely without requiring API keys or special local configurations.

## Test Writing Guidelines

### 1. Tests Define CORRECT Behavior
- Tests specify what SHOULD happen, not what currently happens
- Tests are written BEFORE implementation (TDD)
- Tests verify meaningful, user-facing behavior
- Tests are independent of current implementation details

### 2. Bug Fixes Include Tests
- Every bug fix has a corresponding test
- Tests target the ROOT CAUSE, not symptoms
- Tests prevent regression
- Tests are added BEFORE the fix (to verify the bug exists)

### 3. Test Quality Requirements
- Tests must verify CORRECT behavior, not current behavior
- Tests must be independent and isolated
- Tests must be fast (< 1 second for unit tests)
- Tests must be deterministic (no flaky tests)
- Tests must have clear docstrings explaining what they test

## Example: Good vs Bad Tests

**Good Test (Tests CORRECT Behavior):**
```python
def test_field_protocol_no_heuristics_fully_user_controlled():
    """NO automatic heuristics - field protocol is 100% user controlled."""
    # Arrange: Create fingerprint with obvious physics files
    agent.current_fingerprint = ProjectFingerprint(
        extensions=[".tex", ".born", ".kappa"],  # Physics indicators
    )

    # Act: Get effective field (no user selection)
    field = agent._get_effective_field()

    # Assert: Returns None - NO automatic detection
    assert field is None
```

**Bad Test (Tests Current Implementation):**
```python
def test_field_protocol_returns_none():
    """Test that _get_effective_field returns None."""
    # This is bad - it just tests what the code does now,
    # not what it SHOULD do
    field = agent._get_effective_field()
    assert field is None  # Why should it be None? What's the requirement?
```

## CI/CD Pipeline

### Test Execution Order
1. Unit tests
2. Integration tests  
3. End-to-end tests
4. GUI smoke tests
5. Binary builds (on tagged releases)

### Platform Matrix
- Ubuntu 22.04, 24.04 (primary)
- Debian 12 (container)
- Rocky Linux 9 (container)
- Windows-latest (Windows 10/11)
- macOS-13 (Intel Mac)

### Exclusions
- AI interaction tests are excluded from CI/CD
- Local-only tests are excluded from CI/CD
- GUI tests run with Xvfb on Linux
- Platform-specific tests run only on relevant platforms

## Supported Platforms

For the current list of supported platforms, see [SUPPORTED_PLATFORMS.md](./SUPPORTED_PLATFORMS.md).

## AI Testing Considerations

AI interaction tests require special handling:

- Marked with `@pytest.mark.ai_interaction`
- Excluded from CI/CD by default
- Require valid API keys in environment
- Should be run manually by developers
- May have rate limits affecting test reliability

## Documentation Standards

- Tests must have docstrings explaining the CORRECT behavior
- Test names should be descriptive of the expected outcome
- Edge cases should be tested separately
- Error conditions must be verified with appropriate exceptions
