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
