# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.22.38] - 2026-03-04
### Fixed
- **Status Modal Flickering**: Refactored the progress dialog to create it once and only update its content, eliminating the disruptive hide/show behavior during updates.
- **Scan Performance & Stability**: Optimized path resolution in the file scanner to reduce CPU/memory usage and increased the UI update interval to prevent system overload (OOM).
- **Scan Guard**: Added a protection mechanism to prevent multiple simultaneous scans from being triggered.
- **Metadata Robustness**: Updated data models to better handle intermediate metadata states during the AI drafting process.
- **Chat Auto-Scrolling**: Implemented intelligent automatic scrolling to the latest message in the chat panel, only triggering when new messages are added.
- **UI Stability**: Decoupled the main application interface (buttons, metadata preview) from the background scan state, preventing disruptive layout changes and spinners during operations.
- **YAML Parsing**: Enhanced robustness against unquoted colons in LaTeX-style strings (e.g., in scientific titles), resolving common parsing failures.
- **Chat Layout**: Implemented comprehensive text wrapping for chat bubbles, eliminating horizontal scrolling for YAML and code blocks.

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
...
