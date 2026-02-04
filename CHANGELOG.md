# Changelog

All notable changes to this project will be documented in this file.

## [0.5.0] - 2026-02-04
### Added
- **Advanced Grounding & Analysis:**
  - **Mega-Prompt Refactor:** Aligned one-shot extraction prompt with RODBUK Pydantic models (added `related_publications` and detailed author schema).
  - **Auxiliary Context:** Automated injection of `README.md` and `*.yaml` files from project root into AI analysis.
  - **Google Search Grounding:** Mandated web search for ORCID and DOI discovery within the extraction chain-of-thought.
  - **@File Context Expansion:** Implemented `@filename` syntax in chat for user-driven context inclusion.
- **Improved Data Extraction:**
  - Enhanced author merging logic with automated ORCID scheme detection.
  - Refined JSON parser to handle mandatory schema fields for related publications.

## [0.4.3] - 2026-02-04
### Added
- **UI Refinements:**
  - Redesigned metadata text boxes with clean "magazine-style" truncation (1.5 line-height, 110px height).
  - Implemented "more..." / "less..." toggle for long text fields with zero vertical padding.
  - Centralized UI state management to resolve `NameError` and `UnboundLocalError` issues.
- **Persistence:**
  - Added per-project AI model persistence (`ai_model` in metadata).
  - Added global AI model defaults (`google_model` in settings).
  - Reactive header updates when restoring project-specific models.
- **Project Sync:**
  - Fixed project selector state to correctly display the active project name after switching.

## [0.4.2] - 2026-02-04
### Added
- **Chat UI Overhaul:**
  - Modern, compact card-based design for chat messages.
  - Aligned user/agent message widths with consistent right margins and left indentation for user prompts.
  - Multiline `textarea` input with Ctrl+Enter submission.
  - Agent messages use light grey background for clear distinction.
- **Layout Coordination:**
  - Dashboard panels now use 100% viewport height (`h-[calc(100vh-120px)]`).
  - Synced vertical scrolling between chat and metadata preview panels.

## [0.4.1] - 2026-02-04
### Added
- **Enhanced Metadata Preview:**
  - Redesigned authors display with inline-icons and tooltip overlays for ORCID/affiliation details.
  - Keywords now displayed as compact, wrapped badges matching authors' styling.
  - Improved space utilization with labels positioned above content.
  - Streamlined author/keyword blocks to flow like normal text with wrapping.

## [0.4.0] - 2026-02-03
### Added
- **Deep Analysis:**
  - Implemented `FullTextReader` with recursive LaTeX `\input{}` resolution and Docx paragraph/table support.
  - Added "One-Shot Extraction" using a specialized Mega-Prompt for single-pass metadata harvesting from principal publications.
- **Enhanced UX:**
  - Added "Cancel Scan" capability with threading support for safe interruption of directory crawlers.
  - Reactive Project Path binding for seamless state synchronization.
  - "Guarded Load" logic for project switching (prevents redundant expensive scans).
- **Security:**
  - Directory scanner now strictly ignores all hidden files and directories (`.*`).

### Fixed
- UI NameError when selecting projects from the top-bar dropdown.
- Metadata pane synchronization issues during project switching.
- Improved author list parsing in metadata updates.

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
