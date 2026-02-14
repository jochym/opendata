# Testing Infrastructure

The OpenData tool employs a comprehensive testing strategy designed to ensure reliability, safety, and multi-platform compatibility. The suite is divided into unit and integration tests, leveraging realistic scientific project fixtures.

## Core Principles
1. **Test-Driven Refactoring:** All major architectural changes must be preceded by or accompanied by tests that guard against regressions.
2. **Realistic Fixtures:** Heuristic extraction and AI parsing are tested against semi-legitimate research data (LaTeX, VASP, BibTeX, etc.) located in `tests/fixtures/`.
3. **Isolation:** Unit tests must not touch the real filesystem or make network calls. Use `tmp_path` and mocks for these side effects.
4. **Safety First:** Explicit tests verify that the tool NEVER modifies the user's research directory.

## Directory Structure
- `tests/unit/`: Fast, isolated tests for logic, models, and parsing.
  - `models/`: Pydantic model validation and serialization.
  - `agents/`: AI response parsing and agent state machine logic.
- `tests/integration/`: Slower tests involving the filesystem and component wiring.
  - `test_workspace_io.py`: Persistence and directory management.
  - `test_realistic_projects.py`: End-to-end heuristic extraction on mock research projects.
- `tests/fixtures/`: Realistic project templates (Physics, Chemistry, Demo).

## Running Tests
To run the full suite with the correct environment:
```bash
PYTHONPATH=src pytest
```

## Requirements for AI Agents
**CRITICAL:** Every new functionality, bug fix, or structural change MUST be accompanied by corresponding tests in the appropriate directory. 
- If adding a new extractor, add a test case in `tests/integration/test_realistic_projects.py` or a new unit test.
- If modifying models, update `tests/unit/models/test_models.py`.
- Ensure all tests pass on Linux, Windows, and Mac.
