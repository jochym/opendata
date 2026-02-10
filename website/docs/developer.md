# OpenData Tool - Developer Manual

**Version:** v0.12.0
**Maintained By:** Pawel T. Jochym & AI Agents

---

## 1. Architecture Overview

The OpenData Tool is a **hybrid desktop-web application** designed to provide a modern, browser-based interface for local file system operations, backed by agentic AI.

### Core Stack
- **Frontend/UI:** [NiceGUI](https://nicegui.io/) (Vue.js wrapper for Python).
- **Backend/Agent:** Python 3.10+, Google Gemini API (`google-genai`).
- **Desktop Anchor:** `pywebview` (creates the "Control Window" and system tray presence).
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

## 5. Build & Release

### Requirements
- `pyinstaller`
- `poetry` (recommended) or `pip`

### Build Command
```bash
# Windows
pyinstaller --noconsole --onefile --name opendata-win src/opendata/main.py

# Linux
pyinstaller --noconsole --onefile --name opendata-linux src/opendata/main.py
```

### CI/CD
GitHub Actions are configured in `.github/workflows/build.yml` to automatically build binaries for Win/Mac/Linux on every push to `main`.

---

## 6. Testing Strategy
We use `pytest`.
- **Unit Tests:** `tests/test_extractors.py` (verify regex/parsing).
- **Integration Tests:** `tests/test_workspace.py` (verify project persistence).
- **Vibe Checks:** Tests that mock the AI to ensure the "flow" of the conversation works.

**Run Tests:**
```bash
pytest
```

---

## 7. Future Architecture Goals
- **Plugin System:** Allow users to write Python scripts for custom extractors.
- **Local LLM Support:** Abstraction layer to support Ollama/Llama.cpp for offline-only labs.
- **Direct Submission:** Integration with the InvenioRDM API for 1-click publishing.
