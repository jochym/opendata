# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-01-31
### Added
- Initial project scaffolding with `src/opendata` structure.
- **Browser-Centric UI:** Integrated NiceGUI for the primary user interface.
- **Desktop Anchor:** Integrated `pywebview` for a terminal-free "Control Window" with status lights.
- **Iterative Chat Loop:** Scaffolded the agentic reasoning loop for project analysis.
- **RODBUK Compliance:** Implemented Pydantic models for the Cracow Open Research Data Repository schema.
- **Meta-Learning:** Added `ProtocolLearner` logic to extract and store domain-specific "Field Protocols".
- **Mobile-Ready:** Added responsive UI with a secure, opt-in QR code for local network access.
- **Developer Guidelines:** Created a 150-line `AGENTS.md` for coding standards and agentic principles.
- **Frictionless AI:** Integrated Google Gemini support via the `google-genai` package with OAuth2 readiness.
- **Multi-Platform:** Standardized on `pathlib` and UTF-8 encoding for Win/Mac/Linux compatibility.
