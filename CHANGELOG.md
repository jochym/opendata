# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.22.40] - 2026-03-04
### Added
- **Persistent Progress Modal**: All long-running processes (Scan, AI Analysis) now use a persistent modal dialog with live progress stats and a prominent "Stop" button, ensuring the main UI remains stable and interactive.

### Changed
- **UI Stability**: Decoupled the main application interface (buttons, metadata preview) from the background scan state, preventing disruptive layout changes and spinners during operations.

### Fixed
- **Live Status Updates**: Fixed a bug where modal progress information was not updating in real-time by properly registering the status dialog in the refresh cycle.
- **YAML Parsing**: Enhanced robustness against unquoted colons in LaTeX-style strings (e.g., in scientific titles), resolving common parsing failures.
- **Chat Layout**: Implemented comprehensive text wrapping for chat bubbles, eliminating horizontal scrolling for YAML and code blocks.

## [0.22.39] - 2026-03-04
### Added
- **Progress Modal Dialog**: Replaced in-chat status cards with a modal dialog for scanning and AI analysis, providing a clear "Kill Switch" and preventing intrusive auto-scrolling during updates.

### Fixed
- **YAML Parsing**: Improved parser robustness against unquoted colons in LaTeX-style strings (e.g., in scientific titles), resolving "mapping values are not allowed here" errors.
- **Chat Layout**: Implemented comprehensive text wrapping for chat bubbles, including preformatted blocks and code, eliminating horizontal scrolling.
- **Scroll Optimization**: Optimized chat auto-scrolling to only trigger when new messages are added, allowing users to scroll up during background processes without being forced back to the bottom.

## [0.22.38] - 2026-03-04
### Fixed
- **Chat Auto-Scrolling**: Implemented automatic scrolling to the latest message in the chat panel by correctly targeting the NiceGUI `scroll_area` instead of the document body.
- **UI State**: Added `chat_scroll_area` to `AppContext` to maintain a robust reference for scroll operations across re-renders.

## [0.22.37] - 2026-03-03
### Added
- **Persistent Logging**: Implemented automatic file logging to `~/.opendata_tool/opendata.log` with 1MB rotation, ensuring diagnostic data is available even when running in GUI mode without a terminal.
- **GUI-Only Mode**: Configured `pyApp` and `PyInstaller` to build binaries as native GUI applications, eliminating the unnecessary terminal window on startup.

### Changed
- **Logging Architecture**: Refactored `setup_logging` to gracefully handle environments without `stdout` (native GUI mode).
- **CI/CD Pipeline**: Updated pyApp build workflow to use `PYAPP_GUI="true"` and corrected PyInstaller spec to include `tkinter` for the Desktop Anchor window.
- **Local Configuration**: Added `gui = true` to `pyapp/config.toml` to ensure consistent behavior across all build methods.

### Testing
- All 168 tests pass.
- Verified logging fallback when `stdout` is redirected or unavailable.

## [0.22.36] - 2026-03-03
### Added
- **File Management Dialog**: Replaced the large file selection and explorer blocks in the Analysis tab with a dedicated modal dialog for a cleaner, focused interface.
- **Compact Summary**: Added a compact "Important Files" summary card to the metadata panel with an "Edit Selection" button to launch the new dialog.

### Changed
- **UI Layout**: Optimized vertical spacing in the metadata preview panel, reducing gaps and padding to maximize information density.
- **Layout Robustness**: Refactored the metadata panel to use a proper flexbox layout, eliminating the "double scroller" issue while ensuring elements stay tightly packed at the top.

### Fixed
- **UI Spacing**: Resolved issues where elements in the metadata panel were stretched or separated by excessive empty space on different screen sizes.

### Testing
- Added comprehensive unit and integration tests for the new File Management Dialog component.
- Verified UI responsiveness and layout behavior across various viewports.
- All 168 tests pass.

## [0.22.35] - 2026-03-02
### Added
- **Documentation**: Added comprehensive, step-by-step installation guides for beta testers in English and Polish (`website/docs/installation.md`, `website/docs/installation_pl.md`).
- **Website UI**: Enhanced the testing portal (`website/index.html`) with a new "Step-by-Step Installation" section and direct links to the new guides.

### Changed
- **Tester Manual**: Updated `docs/TESTER_MANUAL.md` (and the website version) to reflect the new PyApp-based installation workflow, including security bypass instructions for Windows and macOS.
- **Documentation**: Unified binary naming patterns across all guides to use version placeholders (e.g., `opendata-<system>-pyapp-<version>`).

### Fixed
- **Documentation**: Corrected the default application port from `8000` to `8080` in all manuals.
- **Documentation**: Fixed a typo in the Polish installation guide ("adreres" -> "adresem").
- **Cross-Platform Path Handling**: Fixed `test_lazy_scanner_no_reads` failure on macOS and Windows caused by `Path.relative_to()` errors with symlinks and short paths (e.g., `/var` vs `/private/var`, `runneradmin` vs `RUNNER~1`). Both file path and root are now resolved before computing relative paths in `scan_project_lazy` and `format_file_list`.

### Testing
- All 152 tests pass on all platforms (Ubuntu, macOS, Windows).
- CI/CD pipeline now passes on all platforms after symlink path resolution fix.

## [0.22.34] - 2026-02-28
### Fixed
- **AI Spinner State**: Fixed bug where "AI is thinking" spinner would not disappear after AI completion or cancellation. Added explicit `ctx.refresh("chat")` calls to ensure UI reflects current state.
- **Cancellation Handling**: Added explicit `asyncio.CancelledError` handling in chat to log cancellation messages, matching the scan cancellation pattern.
- **Parsing Robustness**: Updated parser guardrail to accept YAML list markers and increased check window from 200 to 500 characters, preventing crashes on prose-only AI responses.
- **Prompt-Parser Format Mismatch**: Updated all prompt templates to use YAML-first format (with JSON fallback), resolving inconsistencies between prompts and parser expectations.

### Changed
- **Prompts**: All system prompts now prefer YAML format for better readability while maintaining JSON compatibility.
- **E2E Tests**: Replaced hardcoded project paths with realistic fixtures from `tests/fixtures/realistic_projects/`, making tests portable across environments.

### Added
- **Test Coverage**: Added comprehensive test suite for AI cancellation state management (8 tests).
- **Test Coverage**: Added test for prose-only parsing guard to verify parser skips parsing when METADATA section contains only text.
- **Wheel Packaging**: Auto-build wheel for packaging tests, eliminating manual build step requirement.

### Removed
- **Redundant Tests**: Removed `tests/test_workspace.py` (duplicated integration tests in `tests/integration/test_workspace_io.py`).
- **Unnecessary Markers**: Removed `local_only` marker from `tests/test_utils.py` - tests now run in CI/CD.

### Testing
- Fixed `test_help_argument` to verify actual help text output and exit code.
- All 152 tests pass (10 wheel packaging tests now auto-build and run).
- E2E tests now use realistic project fixtures instead of hardcoded paths.

## [0.22.33] - 2026-02-26
### Fixed
- **AI Model Validation**: Prevented application crash when an invalid model name is configured.
- **Model Selection Dialog**: Added a UI dialog that appears when the configured AI model is unavailable, allowing users to select a valid one from the list.
- **NiceGUI Safety**: Fixed a `ValueError` in the settings tab caused by missing model options in the selection dropdown.
- **Startup Logic**: Improved startup sequence to ensure UI notifications and dialogs are called within the correct page context.

## [0.22.32] - 2026-02-25
### Fixed
- **Binary Build Pipeline**: Restored missing dependencies in CI/CD workflow that caused empty wheel filenames in pyApp builds.
- **CI Logic**: Decoupled wheel building from GUI tests to ensure binaries can be built even when GUI tests are skipped.
- **Release Assets**: Ensured all binary artifacts (Windows, Linux, macOS) are correctly attached to the GitHub release.

## [0.22.31] - 2026-02-25
### Added
- **macOS Intel Support**: Added support for macOS Intel (x86_64) pyApp binary builds.
- **System Documentation**: Created `docs/BINARY_SYSTEM.md` detailing the CI/CD build and verification architecture.
- **Smoke Testing**: Implemented a robust two-stage verification system (Smoke Test + Functional API Test) for all distributed binaries.
- **Agent Guidelines**: Updated `AGENTS.md` with a detailed, mandatory release procedure.

### Fixed
- **Windows pyApp**: Fixed critical `ModuleNotFoundError` on Windows by correcting POSIX-to-Windows path conversion in the build pipeline.
- **Linux Compatibility**: Enforced `v1` CPU variant for Linux x86_64 pyApp builds, ensuring compatibility with older CPUs (fixing "Illegal Instruction" crashes).
- **CI Stability**: Standardized temporary path usage across all runners and containers to prevent permission and availability issues.
- **macOS Verification**: Fixed script failures on macOS by removing the dependency on the non-existent `timeout` command.
- **Workflow Cleanup**: Removed duplicate code blocks and unreachable logic in CI/CD workflows identified during system audit.
- **Website Fixes**: Repaired HTML corruption and corrected installation instructions (uvx, pipx) on the portal.

### Changed
- **Dependencies**: Downgraded `bibtexparser` to `>=1.3.0` for better compatibility with older distributions.
- **CI Workflow**: Optimized main workflow to only build binaries on tags or the `develop-binaries` branch.
- **CI Workflow**: Restricted GUI smoke tests to `main` branch, PRs to `main`, and tags.

## [0.22.28] - 2026-02-25
### Fixed
- **PyApp Configuration**: Removed invalid `PYAPP_EXEC_FUNCTION` and ensured proper Python distribution embedding.
- **CI Testing**: Increased verification timeouts to accommodate first-run installation.
