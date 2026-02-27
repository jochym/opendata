# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
