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

## Quick Start (For Developers)
1. **Clone and Setup:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```
2. **Run the Dashboard:**
   ```bash
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
