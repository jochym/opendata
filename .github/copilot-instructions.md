# Copilot Instructions for OpenData Tool

## What This Repository Does
OpenData Tool is a browser-centric, AI-assisted desktop application for preparing scientific metadata and packaging research projects for the **RODBUK** repository. It uses NiceGUI for its web UI, an agentic reasoning backend, and OAuth2 (Google Sign-In) for AI access. The tool is strictly read-only with respect to the user's research data.

## Repository at a Glance
- **Language:** Python 3.11+  
- **Package name:** `opendata-tool` (PyPI); entry point: `opendata`  
- **Version:** `src/opendata/VERSION` (single source of truth)  
- **UI Framework:** NiceGUI (browser-based)  
- **Data validation:** Pydantic v2  
- **Config format:** YAML (preferred over JSON for human-facing files)  
- **i18n:** `gettext` — all user-visible strings must use `_()`  
- **Paths:** Always use `pathlib.Path`; prefer passing `encoding="utf-8"` to text file operations for consistency  

## Key Source Layout
```
src/opendata/
  main.py               # Entry point; --headless/--port/--api/--version flags
  models.py             # Pydantic models — source of truth for data shapes
  utils.py              # Cross-platform read-only file utilities
  workspace.py          # Persistent workspace at ~/.opendata_tool/
  packager.py           # RODBUK metadata packaging
  agents/               # Agentic reasoning loop (engine, parsing, learning, tools)
  ai/                   # AI provider abstractions (Google GenAI, OpenAI)
  extractors/           # File-type metadata extractors (LaTeX, DOCX, etc.)
  protocols/            # Field Protocol YAML storage and manager
  ui/app.py             # NiceGUI app startup
  ui/components/        # Decoupled UI components (chat, metadata, package, …)
  i18n/                 # Translation files (PL; EN uses gettext default)
  prompts/              # Markdown prompt templates for agents
tests/
  conftest.py           # Session fixtures; app_with_api requires running server
  unit/                 # Fast isolated tests (~2 s)
  integration/          # Component interaction tests
  e2e/                  # End-to-end tests (require Xvfb + running app)
  end_to_end/           # Full AI workflow tests
  fixtures/             # Minimal viable project directories for tests
```
Configuration files: `pyproject.toml` (build, pytest, ruff), `.gitignore`.

## Bootstrap & Install (always do this first)
```bash
# Development install — always run before building or testing
pip install -e ".[dev]"
```
Requires Python 3.11+. On Linux, CI installs system packages `xvfb python3-tk libxcb-xinerama0 libxcb-cursor0` for both logic and GUI jobs; they are strictly required for GUI/e2e tests, and recommended locally if you want to replicate CI behavior even when running only unit/integration tests.

## Running the App
```bash
python src/opendata/main.py                          # Normal mode (opens browser)
python src/opendata/main.py --headless --port 8080   # Headless / CI mode
python src/opendata/main.py --headless --port 8080 --api  # + REST API at /api/
python src/opendata/main.py --version                # Print version and exit
```

## Testing (CI-Safe)
Always run the CI-safe suite after making changes:
```bash
pytest   # Runs the CI-safe test suite; excludes ai_interaction and local_only markers
```
This is exactly what CI runs. The `pyproject.toml` sets `addopts = "-m 'not ai_interaction and not local_only'"` by default.

Targeted test commands:
```bash
pytest tests/unit/                          # Unit tests only
pytest tests/integration/                  # Integration tests only
pytest tests/test_main.py -k test_version  # Single test
pytest -m ""                               # ALL tests (requires running app + AI)
```
E2E tests require the app running:
```bash
./tests/run_e2e_tests.sh   # Starts app, runs e2e suite, cleans up
```

## Linting
```bash
ruff check src/ tests/     # Lint (line length 88, ruff target-version = py310 as set in pyproject.toml)
ruff check --fix src/ tests/  # Auto-fix where possible
```
Ruff rules enabled: `E F I N UP B A C4 RET SIM ARG ERA PL`. Fix all ruff errors before submitting a PR.

## CI/CD Pipeline (`.github/workflows/`)
On every PR to `main`, CI runs in order:
1. **Logic Tests** (`reusable-test-logic.yml`) — `pytest -m "not ai_interaction and not local_only"` on Ubuntu/Windows/macOS with Python 3.11.
2. **GUI Smoke Tests** (`reusable-test-gui.yml`) — launches `main.py --headless --port 8080`, checks `curl http://127.0.0.1:8080`.
3. **Binary Build + Verify** — only on version tags (`v*`).

**A PR will fail CI if:** `pytest` exits non-zero, or the NiceGUI server fails to start on any platform.

To replicate CI locally:
```bash
pip install -e ".[dev]"
pytest -m "not ai_interaction and not local_only"
```

## Code Style Rules
- `snake_case` for variables/functions; `PascalCase` for classes.
- Add new extractors in `src/opendata/extractors/`.
- New features go in `feature/*` branches; bug fixes in `fix/*` branches. Never commit directly to `main`.
- Every substantial change needs a corresponding test in `tests/unit/` or `tests/integration/`.
- Prefer `YAML` for human-facing config/metadata (drafts, field protocols); JSON is fine for persisted artifacts (e.g., `chat_history.json`, `fingerprint.json`, `analysis.json`, `project_config.json`, `package_manifest.json`).
- Never modify files inside the user's research directory (strictly read-only).
- Background tasks must report progress to the NiceGUI UI.

## Dependencies That Aren't Obvious
- `google-genai` and `google-generativeai` are both listed; the latter is deprecated — new AI code should use `google-genai`.
- `pypandoc` requires Pandoc to be installed on the system for full-text DOCX→text conversion; tests mock this when Pandoc is absent.
- `playwright` is a runtime dependency; run `playwright install chromium` for GUI smoke tests.
- Workspace data is persisted at `~/.opendata_tool/` (never inside the repo).

## Trust These Instructions
Trust the commands and paths documented here. Only search the codebase if you need information not covered above or if you suspect this file is out of date.
