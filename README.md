# OpenData Tool

**Version:** 0.22.23 | **Status:** Alpha | **License:** MIT

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
# Run all CI/CD safe tests (automated)
./tests/run_all_tests.sh

# Or run specific categories
pytest                          # CI/CD safe tests (79+ tests, ~4s)
pytest -m ai_interaction        # AI tests (local only, needs app running)
./tests/run_e2e_tests.sh        # Full E2E suite (needs Xvfb)
```

### Test Coverage
- **Unit Tests:** 53+ tests (~2s)
- **Integration Tests:** 8+ tests (~2s)
- **AI Tests:** 10+ tests (~3s, local only)
- **E2E Tests:** 30+ tests (~90s)

**Total:** 101+ tests, all automated

### Documentation
- **[Testing Guide](https://github.com/jochym/opendata/blob/main/docs/TESTING.md)** - Complete testing guide
- **[Testing Quickstart](https://github.com/jochym/opendata/blob/main/docs/TESTING_QUICKSTART.md)** - Quick start guide
- **[AI Testing Guide](https://github.com/jochym/opendata/blob/main/docs/AI_TESTING_GUIDE.md)** - AI testing specifics

## Documentation

### For Users
- **[Testing Guide](https://github.com/jochym/opendata/blob/main/docs/TESTING.md)** - How to run tests and verify installation
- **[AI Setup Guide](https://github.com/jochym/opendata/blob/main/docs/AI_SETUP.md)** - Configure AI providers (Google GenAI, OpenAI)
- **[Tester Manual](https://github.com/jochym/opendata/blob/main/docs/TESTER_MANUAL.md)** - Complete QA and manual testing workflows
- **[Supported Platforms](https://github.com/jochym/opendata/blob/main/docs/SUPPORTED_PLATFORMS.md)** - OS and Python version compatibility

### For Developers
- **[Developer Manual](https://github.com/jochym/opendata/blob/main/docs/DEVELOPER_MANUAL.md)** - Core development guide
- **[API Reference](https://github.com/jochym/opendata/blob/main/docs/dev/API.md)** - Internal REST API documentation
- **[Test Infrastructure](https://github.com/jochym/opendata/blob/main/docs/dev/TEST_INFRASTRUCTURE.md)** - Testing architecture deep dive
- **[Test Results](https://github.com/jochym/opendata/blob/main/docs/dev/TEST_RESULTS.md)** - Coverage analysis and metrics
- **[Field Protocol Design](https://github.com/jochym/opendata/blob/main/docs/dev/FIELD_PROTOCOL_DECOUPLING.md)** - Hierarchical protocol system
- **[Prompt Architecture](https://github.com/jochym/opendata/blob/main/docs/dev/PROMPT_ARCHITECTURE.md)** - AI prompt system design

### Project Status
- **[Accomplishments](https://github.com/jochym/opendata/blob/main/docs/dev/ACCOMPLISHMENTS.md)** - Historical development log
- **[Roadmap](https://github.com/jochym/opendata/blob/main/docs/dev/ROADMAP.md)** - Future plans and upcoming features
- **[Changelog](https://github.com/jochym/opendata/blob/main/CHANGELOG.md)** - Version history and release notes

## Badges

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/opendata-tool.svg)](https://pypi.org/project/opendata-tool/)
