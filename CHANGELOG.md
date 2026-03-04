# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.22.38] - 2026-03-04
### Fixed
- **Status Modal Stability**: Completely refactored the progress dialog to use pure reactive bindings, eliminating all flickering, "client deleted" errors, and the "disappearing" behavior during long scans.
- **Scanner Performance & OOM Prevention**: Optimized file scanning by replacing heavy Path resolution with high-performance string operations and increasing the UI update interval to 1.0s. This significantly reduces CPU/memory load during large project indexing.
- **Metadata Models**: Restored default mandatory fields while maintaining flexibility for AI drafting states.
- **Chat Experience**: Implemented intelligent auto-scrolling and fixed horizontal overflow for code/YAML blocks.
- **UI Consistency**: Decoupled the main application layout from background process states, ensuring a stable and reliable user interface.

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
