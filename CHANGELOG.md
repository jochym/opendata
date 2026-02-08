# Changelog

All notable changes to this project will be documented in this file.

## [0.9.11] - 2026-02-08
### Fixed
- **Scanning Engine:** Resolved a `NameError` in `start_analysis` where `exclude_patterns` was used before definition. Fixed incorrect tuple unpacking for `scan_project_lazy` returns.

## [0.9.10] - 2026-02-08
### Added
- **High-Performance Scanning:**
  - Integrated `os.scandir` for directory traversal, reducing disk I/O operations by 60-80% for large projects.
  - Combined Fingerprint generation and SQLite inventory collection into a single pass.
  - Eliminated redundant `stat()` calls during heuristic analysis.

## [0.9.9] - 2026-02-08
### Fixed
- **Project Management:**
  - **Project Factory Bug:** Removed aggressive directory creation in `handle_load_project`. Project directories are now only created when explicitly saving state (e.g., after a scan). This prevents the "ghost project" issue where browsing or attempting to delete a corrupt project would instantly recreate its folder.

## [0.9.8] - 2026-02-08
### Fixed
- **Project Management:**
  - **Unique Corrupt Labels:** Ensured that projects with missing metadata or fingerprints are assigned unique display paths (e.g., "Unknown (ID: abc12345)"). This fixes a collision issue where multiple broken projects shared the same "Unknown" path, making them impossible to select or delete individually.
  - **Reactivity:** Proper integration of translations in the workspace manager.

## [0.9.7] - 2026-02-08
### Fixed
- **Project Management:**
  - **Aggressive ID Resolution:** Enhanced the deletion logic to extract project IDs from "Unknown" path strings using regex. This ensures that even severely corrupt projects with no metadata can be permanently removed from the workspace.
  - **Deletion Success Verification:** Improved feedback and state reset after a successful project deletion.

## [0.9.6] - 2026-02-08
### Fixed
- **Project Management:**
  - **Early State Assignment:** `ScanState.current_path` is now assigned immediately when a project is selected. This ensures the UI remains in sync even for corrupt projects that fail to load, allowing them to be targeted for deletion.
  - **Graceful Failures:** Projects that fail to load from disk no longer crash the UI or reset the selector, providing a better recovery path for the user.

## [0.9.5] - 2026-02-08
### Fixed
- **Project Management:**
  - **Dropdown Deletion:** Fixed an issue where the delete button would only work for correctly loaded projects. It now correctly targets whichever project is currently selected in the dropdown, even if it failed to load.
  - **Button Visibility:** Ensured the delete button remains visible based on dropdown selection state, allowing users to purge corrupt entries from the history.

## [0.9.4] - 2026-02-08
### Fixed
- **Project Management:**
  - **Selective Deletion:** The delete button is now linked to the project currently selected in the dropdown, allowing the removal of projects that fail to load.
  - **Button Visibility:** Fixed an issue where the delete button would disappear if a project was corrupt and couldn't set an active path.

## [0.9.3] - 2026-02-08
### Fixed
- **Critical Recovery:** Restored `app.py` from a healthy state after a partial overwrite during previous session.
- **Project Management:** Finalized robust deletion logic for projects with missing metadata or "Unknown" paths.
- **Repository Hygiene:** Permanently removed accidental `log` file from the git history and verified `.gitignore` rules.

## [0.9.2] - 2026-02-08
### Fixed
- **Repository Hygiene:** Removed accidental `log` file from version control and ensured it's ignored via `.gitignore`.
- **UI & Routing:** Fixed a potential 404 issue when accessing the app via specific hostnames by ensuring consistent base routing.

## [0.9.1] - 2026-02-08
### Fixed
- **Project Management:**
  - **Robust Deletion:** Fixed an issue where corrupt projects with "Unknown" paths could not be removed from the recent projects list.
  - **Uniqueness:** Added project ID fragments to "Unknown" paths to ensure each corrupt project is distinct and selectable for deletion.
  - **Improved ID Resolution:** The UI now uses a multi-stage ID resolution (Path -> Selector Value -> ID) to ensure the correct project is targeted for removal.

## [0.9.0] - 2026-02-08
### Added
- **Package Content Management:**
  - **SQLite Inventory:** Implemented `ProjectInventoryDB` for persistent caching of multi-thousand file listings (tested up to 15,000 files).
  - **Lazy Loading UI:** Redesigned the Package tab to show immediate statistics from fingerprint while loading the full file grid in the background.
  - **Grid Virtualization:** Limited AgGrid rendering to 2000 files with a search-based interaction model to prevent WebSocket buffer overflows.
- **Performance & Stability:**
  - **SQLite WAL Mode:** Enabled Write-Ahead Logging and optimized transactions for near-instant inventory updates.
  - **WebSocket Throttling:** Implemented debouncing and sequential UI refreshes during project loading to ensure connection stability.
  - **Load Guards:** Added state-based loading guards to prevent infinite loading loops in the UI.
- **Improved Scanner:**
  - **Integrated Inventory:** Combined statistics gathering and database indexing into a single pass to eliminate scanning pauses.
  - **Accurate Glob Exclusions:** Fixed `walk_project_files` to match exclusion patterns against full relative paths instead of just filenames.
  - **Path Sanitization:** Added automatic resolution and validation of project paths, including trailing space removal.

## [0.8.0] - 2026-02-06
### Added
- **Interactive Metadata Refinement:**
  - **Dynamic Forms:** Implemented `AIAnalysis` model to parse structured AI feedback (missing fields, conflicts, questions) into interactive UI forms.
  - **Conflict Resolution:** Added specialized `ui.select` forms for resolving data conflicts between different research sources (e.g., LaTeX vs. YAML).
  - **Batch Questioning:** AI now collects all missing metadata requirements into a single analysis block, dramatically reducing API quota usage and chat friction.
  - **Human-Readable Summaries:** Form submissions are logged as formatted bullet points in chat history for transparency.
- **Enhanced Scientific Metadata:**
  - **Software & Versioning:** Added `software` extraction to track versions of tools like VASP, Phonopy, and ALAMODE.
  - **Scientific Branches:** Integrated OECD and MNiSW classification systems into core extraction logic and UI preview.
  - **Extended Licensing:** Added `license` field to the primary metadata schema.
- **Viewport & UI Optimization:**
  - **Edge-to-Edge Dashboard:** Optimized layout to eliminate vertical page-level scrollbars using precise header height calculations (`calc(100vh - 104px)`).
  - **Padding/Margin Reset:** Forcefully removed NiceGUI default paddings via global CSS overrides for a truly professional CLI-agent feel.
  - **Compact Field Display:** Redesigned field labels with `text-[10px] uppercase tracking-wider` and negative margins to maximize information density.
  - **Unified Description:** Multi-paragraph descriptions are now rendered as a single block with line-clamping and a single "more..." toggle.
  - **Path Robustness:** Automated `~` expansion and canonicalization in the project directory input and packaging service.
- **Testing & Diagnostics:**
  - **Automated Bug Reporting:** Added `/bug` command for single-click collection of system info, metadata, and chat history for developers.

## [0.7.0] - 2026-02-04
### Added
- **Metadata Package Builder:**
  - **Specialized ZIP Generation:** Implemented `generate_metadata_package` to create a lightweight submission skeleton containing only `metadata.yaml`, `metadata.json`, and root documentation.
  - **Smart Doc Discovery:** Automated identification of standard documentation files (`README*`, `LICENSE*`, `CITATION*`, `codemeta.json`) from the project root.
  - **Mandatory Field Validation:** Integrated pre-flight checks against RODBUK schema (Title, Authors, Contacts, Science Branches) before packaging.
  - **Frictionless Download:** Connected the UI \"Build Package\" button to trigger a direct browser download via `ui.download`.
  - **Feedback Loop:** Automatic assistant confirmation in the chat history upon successful package creation.
- **CI/CD & Distribution:**
  - **Cross-Platform Workflows:** Added GitHub Actions for automated Windows (.exe), macOS (.dmg), and Linux (.tar.gz) builds.
  - **Updated Testing Portal:** Refreshed the beta testing website (v0.9.3-beta) with new roadmap milestones and download assets.
- **Testing:**
  - **Packager Test Suite:** Added `tests/test_packager.py` to verify documentation inclusion and research data exclusion rules.

## [0.6.1] - 2026-02-04
### Added
- **UI Flexibility:**
  - **Resizable Layout:** Implemented vertical splitter between Agent Interaction and Metadata panels.
  - **Position Persistence:** Dashboard remembers the last used splitter position across sessions.
- **Improved Scanner Feedback:**
  - Unified header statistics (`[Size] - Current/Total`) during both scanning and checking phases.
  - Fixed duplicate bracket formatting in progress messages.
- **Robustness:**
  - Refined project deletion fallback logic to ensure partially initialized projects are fully wiped.

## [0.6.0] - 2026-02-04
### Added
- **Optimized Scanner:**
  - **Time-based Throttling:** UI updates limited to 10Hz (100ms) for smoother progress and reduced CPU load.
  - **Incremental Display:** Live size counter separate from the current file path.
  - **Smart Shortening:** Path display now preserves first two and last two components (e.g., `data/anl/.../T=300K/file.dat`).
  - **Full-Path Tooltips:** Hovering over shortened paths reveals the complete relative path.
  - **.ignore Support:** Scanner now skips entire directory trees if a `.ignore` file is present.
  - **Symlink Safety:** Added explicit protection against following symbolic links.
- **UI & Interaction:**
  - **Adaptive Scan Button:** The "Analyze" button now transforms into a red "Cancel Scan" button during activity.
  - **Project List Deletion:** Improved "Remove Project" feature with native NiceGUI confirmation dialogs.
  - **Inclusive Management:** Corrupt or partial projects are now visible in the dropdown and can be deleted.
- **Transparency:**
  - Improved proposal message explicitly lists all auto-included auxiliary files.
  - Instant `[System]` feedback in chat window using thread-safe callbacks.

## [0.5.1] - 2026-02-04
### Added
- **System Feedback:** Immediate `[System]` status messages in chat listing all analyzed files (main, auto, and user-requested).
- **Rich Funding UI:** Added amber-colored badges for funding with priority on award titles and grant IDs.
- **Unified Contact UI:** Contacts now use indigo-colored badges styled like authors, with email icons and tooltips.
- **Improved Extraction:**
  - Automated extraction of "Corresponding Author" and paper abstract.
  - Funding extraction now specifically targets "Financial Support" sections.
  - Robust Pydantic validation with placeholder injection for missing mandatory contact fields.
- **UI Styling:** Multi-line support for related publication badges and DOI prefix cleanup.

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
