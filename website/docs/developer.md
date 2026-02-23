# OpenData Tool - Developer Manual

**Version:** v0.22.22
**Maintained By:** Pawel T. Jochym & AI Agents
**License:** MIT

---

## 1. Architecture Overview

The OpenData Tool is a **hybrid desktop-web application** designed to provide a modern, browser-based interface for local file system operations, backed by agentic AI.

### Core Stack
- **Frontend/UI:** [NiceGUI](https://nicegui.io/) (Vue.js wrapper for Python).
- **Backend/Agent:** Python 3.10+, Google Gemini API (`google-genai`).
- **Desktop Anchor:** `pystray` (System Tray icon) + `NiceGUI` (Local server).
- **State Management:** `Pydantic` models + SQLite + YAML persistence.

### Directory Structure
```
src/opendata/
├── ui/                 # NiceGUI Components
│   ├── components/     # Widgets (Chat, Package, Metadata, etc.)
│   └── app_context.py  # Session & State Injection (Dependency Injection)
├── agents/             # AI Logic
│   ├── analysis.py     # Main Analysis Loop
│   ├── parsing.py      # JSON Extraction from LLM output
│   └── tools.py        # External APIs (arXiv, DOI, ORCID)
├── extractors/         # Heuristic File Parsers
│   ├── latex.py        # .tex parsing
│   ├── docx.py         # .docx parsing
│   └── science/        # VASP, DICOM, HDF5 specific logic
├── models.py           # Pydantic Schemas (RODBUK & App State)
└── main.py             # Entry Point
```

---

## 2. Key Design Patterns

### 2.1. The "Stateless Model, Stateful Agent"
The AI (Gemini) is stateless. We must reconstruct the context for *every* turn of the conversation.
- **Context Construction:**
  1. **System Prompt:** Base persona and strict JSON formatting rules.
  2. **Field Protocols:** User-defined rules (injected dynamically).
  3. **Current Metadata State:** The *entire* current draft of the metadata (YAML).
  4. **Chat History:** Last ~10 messages for conversational continuity.
  
*Crucial:* Never rely on the LLM to "remember" the metadata. Always feed it back in.

### 2.2. AppContext (Dependency Injection)
We avoid global variables for user state. `AppContext` is a singleton-per-session that holds:
- `workspace`: The project manager.
- `ui_state`: Reactive UI flags (e.g., `is_scanning`, `current_tab`).
- `agent`: The active AI agent instance.

### 2.3. Heuristics First, AI Second
We do not send all files to the AI (too expensive/slow).
1. **Scanner:** Quickly walks the directory (using `os.scandir` for speed).
2. **Heuristics:** Extractors (`extractors/*.py`) identify candidates (e.g., "This looks like a VASP OUTCAR").
3. **AI:** We only send the *text content* of the most relevant files (e.g., the abstract from `main.tex`) to Gemini for semantic processing.

---

## 3. The "Package Tab" & File Explorer
- **Problem:** Browsers freeze if you try to render a DOM node for every file in a 100,000-file project.
- **Solution (v0.12.0):** 
  - We use a **Virtual Scroller** (NiceGUI `ui.list`).
  - We only render the *visible* items.
  - We use a **Breadcrumb** navigation model instead of a deep tree.
  - **SQLite Inventory:** File stats are cached in a local SQLite DB (`inventory.db` in the project `.opendata` folder) to allow instant searching and filtering without re-scanning the disk.

---

## 4. Meta-Learning (Protocols)
The "Field Protocols" system allows the AI to learn.
- **Storage:** `~/.opendata_tool/protocols.yaml`
- **Mechanism:**
  - Agent detects a rule in user input (e.g., "Ignore folder X").
  - Agent asks confirmation.
  - Rule is saved to the global YAML.
  - On the next project analysis, this YAML is injected into the System Prompt.

---

## 5. Installation & Development

### Quick Start (PyPI)
```bash
# Install with uv (recommended)
uv tool install opendata-tool

# Or with pipx
pipx install opendata-tool

# Run
opendata-tool
```

### Development Installation
```bash
# Clone repository
git clone https://github.com/jochym/opendata.git
cd opendata

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Run
python src/opendata/main.py
```

### Build & Release

#### Requirements
- `pyinstaller`
- `python -m build` (for PyPI packages)

#### Build Commands
```bash
# Build PyPI package
python -m build --sdist --wheel

# Build standalone binary
pyinstaller --noconsole --onefile --name opendata src/opendata/main.py
```

#### CI/CD
GitHub Actions automatically build binaries for Win/Mac/Linux and publish to PyPI on every tagged release.

---

## 6. Testing Strategy

### Test Categories
- **Unit Tests** (`tests/unit/`): Fast, isolated component tests (~2s)
- **Integration Tests** (`tests/integration/`): Component interaction tests (~2s)
- **E2E Tests** (`tests/e2e/`): Complete workflow tests with Playwright (~90s)
- **AI Tests** (`tests/end_to_end/`): AI interaction tests (local only, requires API keys)

### Running Tests
```bash
# Run all CI/CD safe tests (default)
pytest

# Run all tests including AI (requires app running)
pytest -m ""

# Run specific category
pytest -m unit
pytest -m e2e
pytest -m ai_interaction  # Local only

# Run with coverage
pytest --cov=opendata
```

### Test Coverage
- **Total Tests:** 110+ tests
- **CI/CD Time:** ~5 seconds
- **Coverage:** See `docs/dev/TEST_RESULTS.md`

---

## 7. Future Architecture Goals
- **Plugin System:** Allow users to write Python scripts for custom extractors.
- **Local LLM Support:** Abstraction layer to support Ollama/Llama.cpp for offline-only labs.
- **Direct Submission:** Integration with the InvenioRDM API for 1-click publishing.
