# Agent Guidelines for OpenData Tool

This repository contains the OpenData Tool, designed for preparing metadata and packaging scientific projects for the RODBUK repository. This document provides essential information for AI agents to maintain consistency and quality while ensuring a **friction-free, browser-centric, multi-platform user experience** for researchers.

## Core Principles
1. **Browser-Centric UI with Desktop Anchor:** The primary user interaction happens in the browser (NiceGUI). However, the app must launch a small, simple **Desktop Control Window** (placeholder) as a "Kill Switch".
2. **Dashboard-First Transparency:** The Desktop Control Window should include "idiot lights" (red/green) and a button to "Open Dashboard".
3. **Mobile-Ready (Optional/Secure):** The UI includes an "Open on Mobile" feature. **Security Note:** By default, the server must only bind to `localhost` (127.0.0.1). Remote access (0.0.0.0) must be explicitly enabled by the user when they request mobile access.
4. **No-Terminal Experience:** When launched as an executable, **no terminal/console must be shown**.
5. **Strictly Read-Only Analysis:** The tool must NEVER modify the contents of the user's research directory.
6. **Domain Knowledge Accumulation:** The tool must support "Meta-Learning". As users refine analysis rules (e.g., "In this lab, .dat files are always pressure logs"), the agent should extract these as permanent **Field Protocols** (instructions). These protocols must be stored in the global workspace and transferable between projects.

## Project Workflow
1. **Guided Setup (Once per user):** 
   - Language selection.
   - AI capability configuration (Consent-based OAuth2/Google Account).
   - Persistence of settings (changeable at any time).
2. **Interactive Project Analysis (The "Chat" Loop):**
   - User points to a directory.
   - **Protocol Injection:** The agent reads both global instructions and the user's custom **Field Protocols**.
   - **Iterative Interaction:** The tool enters a specialized chat-like loop where the agent proposes metadata and asks for clarifications.
   - **Knowledge Capture:** If the user provides a repeatable rule, the agent asks: "Should I remember this rule for future projects in this field?"
3. **Metadata Refinement & Packaging:**
   - User reviews the final proposed RODBUK metadata and generates the package in the workspace.

## Directory Structure
- `src/opendata/ui/`: NiceGUI components for the Dashboard, Wizard, and Chat Loop.
- `src/opendata/agents/`: Specialized agent logic for project interpretation and **Protocol Learning**.
- `src/opendata/protocols/`: Storage for user-defined, field-specific instruction sets.
- `src/opendata/ai/`: Provider abstractions and configuration management.
- `src/opendata/models.py`: Pydantic models for RODBUK metadata and persistent user settings.
- `src/opendata/utils.py`: Cross-platform, read-only file utilities.


## Context Consistency & Chat Loop Best Practices (CRITICAL)
- **Stateless Model, Stateful Agent:** Models are stateless. The agent must rebuild the full context (System Prompt + Field Protocols + Current Metadata Draft + History) for every request.
- **Anchor Context with YAML:** The `current_metadata` draft (in YAML) is the "Source of Truth". Always inject it into the prompt. Never rely on the chat history for factual state.
- **Prompt Ordering:** System Prompt -> Field Protocols -> Current State (Metadata) -> Recent History -> User Input.
- **Immediate Extraction:** As soon as metadata is found or confirmed by the user, update the internal `Metadata` model. Do not leave it buried in the chat log.
- **Text-First Approximation:** For scientific projects, the primary text (LaTeX/Docx/PDF-converted-text) is the richest source of metadata. 
  - **First Prompt Strategy:** The first agent response should summarize gathered heuristics and propose the most likely "main paper" file. 
  - **The Ask:** "I've gathered these initial details. Is it okay to use [file_name] as the primary source for a first approximation of the metadata?"

## Build, Lint, and Test Commands

### Setup & Build
- Development: `pip install -e .`
- **Build Binary (All Platforms):** `python build.py` or `python build.py --platform PLATFORM`
  - Automatically detects platform (linux, windows, macos-intel, macos-arm)
  - Includes all required resources (ui, prompts, VERSION)
  - Creates no-console GUI executable
  - See `docs/BUILDING.md` for details
- Running Tests: `pytest` (Must pass on Win/Mac/Linux)

### Vibe-Coding Verification (CRITICAL)
Every substantial step must have an accompanying automated test. Before completing a task, run the relevant test to verify the "vibe":
- **Run all tests:** `pytest`
- **Run specific test file:** `pytest tests/test_name.py`
- **Run single test case:** `pytest tests/test_name.py -k "test_function_name"`

## Registry of Accomplishments (Stage Log)
> **Moved to `docs/ACCOMPLISHMENTS.md`** - Please refer to that file for the full historical log of development phases.

## Code Style Guidelines



### 1. Multi-Platform Compatibility & i18n
- **Python-Centric:** All core logic must be written in Python 3.10+.
- **Internationalization:** All user-facing strings must be wrapped in `_()` using the `gettext` framework. The app must remain multilingual (PL/EN) during development.
- **YAML-First:** Use **YAML** instead of JSON for all human-facing configuration files, metadata drafts, and Field Protocols to ensure high readability and error-forgiveness.
- **Paths:** ALWAYS use `pathlib.Path`.
- **Encoding:** Explicitly use `encoding="utf-8"` for all file operations.

### 2. Frictionless AI & Authentication
- **No API Keys:** Implement OAuth2 flows.
- **Graceful Degradation:** If AI is unavailable, remain functional using heuristic extractors.

### 3. Interactive UI & Dashboard
- Use `NiceGUI` for all workflows. 
- Ensure background tasks report progress to the dashboard UI.
- Use clear, non-technical language for status messages.

### 4. Naming & Structure
- Follow `snake_case` for variables/functions and `PascalCase` for classes.
- `src/opendata/models.py` is the "Source of Truth".

## Metadata Standards (RODBOK)
- Strictly follow the RODBOK schema.
- Mandatory: `title`, `authors`, `abstract`, `license`, `keywords`.

## Agent Specific Instructions
- **Proactiveness:** Implement new extractors in `src/opendata/extractors/`.
- **Testing:** Include a "minimal viable project" fixture in `tests/fixtures/`.
- **Transparency:** Every background step should have a corresponding UI status update.

## Release & Versioning Procedure (CRITICAL)
Strictly adhere to **Semantic Versioning** (major.minor.patch) and the following release sequence:

1. **Verification & QA**:
   - Run the full test suite (`pytest`).
   - For **Minor (x.y.0)** or **Major (x.0.0)** releases: Perform a comprehensive review of all documentation (docs, tutorials, references) and the website to ensure a consistent and updated project state.
2. **State Synchronization**:
   - Update `CHANGELOG.md` with all changes since the last release.
   - Update `src/opendata/VERSION` (Single Source of Truth).
   - Ensure the documentation website reflects the new version's features and changes.
3. **Git Commit**: Commit all changes (VERSION, CHANGELOG, docs) *before* tagging the release.
4. **GitHub Release**:
   - Create a tag (e.g., `v1.2.3`).
   - Use `gh release create` with the current version's changelog section.
   - **Formatting Mandate**: ALWAYS use a `heredoc` (e.g., `cat << 'EOF' | gh release create ... --notes-file -`) to pass release notes. This prevents Markdown escaping issues and ensures proper rendering on GitHub.

---
*This file is intended for AI agents. Please update it as the project evolves.*

---

## Testing Philosophy & Principles

### Core Testing Principles

1. **Tests Define CORRECT Behavior**
   - Tests specify what SHOULD happen, not what currently happens
   - Tests are written BEFORE implementation (TDD)
   - Tests verify meaningful, user-facing behavior
   - Tests are independent of current implementation details

2. **Bug Fixes Include Tests**
   - Every bug fix has a corresponding test
   - Tests target the ROOT CAUSE, not symptoms
   - Tests prevent regression
   - Tests are added BEFORE the fix (to verify the bug exists)

3. **Test Categories**
   - **Unit tests**: Test individual components in isolation
   - **Integration tests**: Test component interactions
   - **E2E tests**: Test complete user workflows
   - **AI tests**: Marked with `@pytest.mark.ai_interaction`, excluded from CI/CD
   - **Local tests**: Marked with `@pytest.mark.local_only`, excluded from CI/CD

4. **Test Quality Requirements**
   - Tests must verify CORRECT behavior, not current behavior
   - Tests must be independent and isolated
   - Tests must be fast (< 1 second for unit tests)
   - Tests must be deterministic (no flaky tests)
   - Tests must have clear docstrings explaining what they test

### Test Structure

```python
def test_correct_behavior():
    """Test description should specify CORRECT behavior, not implementation."""
    # Arrange: Set up the scenario
    # Act: Perform the action
    # Assert: Verify CORRECT outcome (not implementation details)
```

### Example: Good vs Bad Tests

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

### Running Tests

```bash
# CI/CD safe (default - excludes AI and local tests)
pytest
# Result: 79 tests, ~4 seconds

# All tests (local with AI configured)
pytest -m ""
# Result: 116 tests (requires app running)

# Only AI tests (local only)
pytest -m ai_interaction
# Result: 16 tests (uses your OpenAI endpoint)

# Only local tests (requires app running)
pytest -m local_only
# Result: 20 tests
```

### Test Files

- `tests/unit/` - Unit tests (fast, isolated)
- `tests/integration/` - Integration tests (component interactions)
- `tests/e2e/` - End-to-end tests (complete workflows)
- `tests/end_to_end/` - Full workflow tests (with AI)

### Documentation

- `docs/TEST_INFRASTRUCTURE_REVIEW.md` - Complete test review
- `docs/AI_TESTING_GUIDE.md` - AI testing instructions
- `docs/OPENAI_TESTING_COMPLETE.md` - OpenAI endpoint configuration

