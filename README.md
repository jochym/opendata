# OpenData Tool (Prototype)

A browser-centric, AI-assisted tool for preparing scientific metadata and packaging research projects for the **RODBUK** repository.

## Key Features
- **Browser-Based UI:** Powered by NiceGUI for a modern, responsive experience.
- **Desktop Control Anchor:** A non-intimidating "Control Window" for process monitoring and simple shutdowns.
- **Iterative Chat Loop:** An agent-driven Q&A interface that helps researchers refine metadata.
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
The tool uses an **Agentic Backend** that performs heuristic extraction (regex/parsers) and AI-assisted interpretation. It follows a strictly **read-only** policy, storing all generated data in a separate workspace.

## Contributing
See `AGENTS.md` for detailed coding standards and the agentic workflow.
