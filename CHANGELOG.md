# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-02-03
### Added
- **Project Persistence & Management:**
  - Automated project state saving (metadata, history, fingerprint) to `~/.opendata_tool/projects/`.
  - Unique project identification via path hashing.
  - Top-bar project selector for seamless switching between research directories.
- **Prompt Factorization & Management:**
  - Moved hardcoded AI prompts to external Markdown templates in `src/opendata/prompts/`.
  - Implemented `PromptManager` for dynamic rendering of system prompts and chat wrappers.
  - Decoupled AI logic from Python code for easier behavioral tweaking.

## [0.2.0] - 2026-02-02
### Added
- **First Semi-Working Demo:**
  - Stable Gemini interaction using `google-generativeai` (v1).
  - External Tools: Integrated arXiv API, DOI resolver, and ORCID search/profile lookup.
  - Google Search Grounding: Agent can now verify facts via live web search.
  - Multi-Author Extraction: Improved `LatexExtractor` to detect full author lists.
  - Interactive Model Selector: Users can switch Gemini models in real-time.
  - Advanced i18n: Polish/English support across all UI elements using GNU gettext.
  - Physics Toolchain: Specialized detection for VASP, Phonopy, and ALAMODE.
  - Reactive Dashboard: No-reload UI with smooth chat scrolling and metadata preview.
  - Security: Force binding to 0.0.0.0 for VPN access (toggleable) and OAuth2 scope refinement.

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
