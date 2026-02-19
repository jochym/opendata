# OpenData Tool (Alpha)

A browser-centric, AI-assisted tool for preparing scientific metadata and packaging research projects for the **RODBUK** repository.

## Key Features
- **Browser-Based UI:** Powered by NiceGUI for a modern, responsive experience.
- **Desktop Control Anchor:** A non-intimidating "Control Window" for process monitoring and simple shutdowns.
- **Interactive Chat Loop:** An agent-driven Q&A interface with **stop control** and **transparent status reporting**.
- **High-Performance Explorer:** A scalable File Explorer for managing massive datasets without UI lag.
- **Domain Meta-Learning:** Automatically learns and stores "Field Protocols" based on user interaction.
- **Secure & Read-Only:** Strictly analyzes project directories without modification.
- **Frictionless AI:** Uses OAuth2 (Sign-in with Google) for Gemini access; no manual API keys required.

## Installation

### Option 1: Download Pre-built Binaries (Recommended for Users)

Visit the [Releases page](https://github.com/jochym/opendata/releases) and download the binary for your platform:
- **Linux**: `opendata-linux`
- **Windows**: `opendata-win.exe`
- **macOS** (Apple Silicon): `opendata-macos-arm`

Simply run the binary - no installation required!

### Option 2: Install from PyPI (Lightweight, for Developers)

**Prerequisites:** Python 3.11+

#### Using `uvx` (Recommended - Fastest, Cross-Platform)

[`uv`](https://github.com/astral-sh/uv) is an extremely fast Python package manager written in Rust. It works on **Windows, macOS, and Linux**.

```bash
# Install uv (one-time setup)
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Run OpenData Tool instantly (no manual installation needed)
uvx opendata-tool

# Or install permanently
uv tool install opendata-tool
uvx opendata-tool
```

#### Using `pipx` (Alternative - Cross-Platform)

```bash
# Install pipx (one-time setup)
python -m pip install --user pipx
python -m pipx ensurepath

# Install and run OpenData Tool
pipx install opendata-tool
opendata-tool
```

#### Using `pip` (Traditional)

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install
pip install opendata-tool

# Run
opendata-tool
```

### Option 3: Development Installation

```bash
git clone https://github.com/jochym/opendata.git
cd opendata
pip install -e ".[dev]"
python src/opendata/main.py
```

## Architecture
The tool uses a modular **Agentic Backend** and a component-based **NiceGUI Frontend**.

- **Frontend (`src/opendata/ui/`)**: Decoupled into functional components (`components/`) and session-managed via `AppContext`.
- **Backend (`src/opendata/agents/`)**: Agentic reasoning loop with specialized modules for parsing and tool execution.
- **Data Safety**: Strictly **read-only** policy for research data. All persistence happens in `~/.opendata_tool/`.

## Contributing
See `AGENTS.md` for detailed coding standards and the agentic workflow.
See `docs/` for comprehensive manuals.

## Testing

### Quick Start
```bash
# Run all tests (automated)
./tests/run_all_tests.sh

# Or run specific categories
pytest                          # CI/CD safe tests (78 tests, ~4s)
pytest -m ai_interaction        # AI tests (needs app running)
./tests/run_e2e_tests.sh        # Full E2E suite (needs Xvfb)
```

### Documentation
- `docs/TESTING_QUICKSTART.md` - Quick start guide
- `docs/TESTING_GUIDE.md` - Complete testing guide
- `docs/AI_TESTING_GUIDE.md` - AI testing specifics

### Test Coverage
- **Unit Tests:** 53 tests (~2s)
- **Integration Tests:** 8 tests (~2s)
- **AI Tests:** 10 tests (~3s)
- **E2E Tests:** 30 tests (~90s)

**Total:** 101 tests, all automated

## Documentation

**For Users:**
- `docs/TESTING.md` - Complete testing guide

**For Developers:**
- `docs/TEST_INFRASTRUCTURE.md` - Technical implementation details
- `docs/TEST_RESULTS.md` - Test results and coverage

**Other Documentation:**
- `docs/ACCOMPLISHMENTS.md` - Historical development log
- `docs/DEVELOPER_MANUAL.md` - Developer guide
- `docs/TESTER_MANUAL.md` - Tester guide
