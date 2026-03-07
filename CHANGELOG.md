# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.22.42] - 2026-03-07
### Added
- **GitHub Bug Reporting (#50)**: Integrated a direct bug reporting system via the `/bug` command.
  - Supports automatic submission to GitHub using a personal access token (configurable in Settings).
  - Includes an issue type selector with 6 standard GitHub categories (Bug, Enhancement, Documentation, Question, Feature, Performance) with corresponding emojis.
  - Automatically attaches diagnostic YAML files to the report.
  - Allows users to attach additional files to the bug report.
- **UI Enhancements**:
  - Resized and refined the bug report dialog for better visibility and usability (650px wide, 85vh tall).
  - Improved the description field height (8 rows) to prevent cut-off text.
  - Refined the "Active AI Connection" card in Settings with a framed, spaced Logout button.
  - Removed redundant "AI Session" line from the bottom of the Settings tab.
  - Synchronized "above/below" instructions across all input forms for consistency.

## [0.22.41] - 2026-03-05
### Fixed
- **Non-editable Metadata Fields (#48)**: Fixed critical bug where empty metadata fields were not visible or editable in the UI.
  - Changed `model_dump(exclude_unset=True)` to `model_dump()` to display ALL RODBUK fields, including empty ones
  - Added visual indicators: mandatory fields (title, authors, abstract, license, keywords) show in **red** when empty
  - Added "Empty (click to add)" placeholders with dashed borders for all empty fields
  - Fixed duplicate rendering bug causing field values to appear twice
  - Restored special formatting for Title field (large font, white card background)
  - Formatted keywords as horizontal badges (similar to software field)
  - Added 12 unit tests to verify empty field handling and editing

## [0.22.40] - 2026-03-05
### Fixed
- **Welcome Message Persistence**: Welcome instruction in chat now stays visible until explicitly dismissed with X button, instead of disappearing after first system interaction (scan/AI analysis).
- **Session State Management**: Added `welcome_dismissed` flag to session state that resets when loading new projects, ensuring welcome message appears for each new project.

## [0.22.39] - 2026-03-04
### Added
- **AI Progress Messages**: Detailed real-time status updates in the progress modal (e.g., "Sending prompt...", "Waiting for reply...", "Parsing response...").
- **File Explorer Pagination**: Added a "Load More" button in the file selector to handle large directories and prevent WebSocket "Message too long" errors.
- **AI Analysis Guard**: The "AI Analyze" button now requires at least one significant file to be selected and shows a helpful tooltip if disabled.
- **Default Selection Category**: The first selected important file now defaults to "Article", while subsequent ones default to "other".

### Fixed
- **YAML-First Parsing**: Refactored the metadata parser to prioritize YAML and added support for list-based structures often returned by newer models (e.g., gemini-3.1-flash-lite).
- **Status Modal Stability**: Completely refactored the progress dialog to use pure reactive bindings with timer-based updates, eliminating all flickering and "client deleted" errors.
- **Scanner Performance & OOM Prevention**: Optimized file scanning using fast string operations and a 0.5s UI update throttle to reduce CPU/memory pressure.
- **Metadata Models**: Restored default mandatory fields while maintaining flexibility for AI drafting states.
- **Chat Experience**: Implemented intelligent auto-scrolling (only triggers on new messages) and fixed horizontal overflow for code/YAML blocks.
- **File Selection UI Sync**: Fixed the bug where the selection bar didn't update after using the editor.
- **Project Switch Cleanup**: Opening a new project now correctly resets all internal agent and UI states.
- **File Role Persistence**: Fixed critical bug where `AIAnalysis` model was missing `model_config = {"populate_by_name": True}`, causing file roles (Article/Other) to be lost when switching projects.

## [0.22.38] - 2026-03-04

### Added
- **AI Progress Messages**: Detailed real-time status updates in the progress modal (e.g., "Sending prompt...", "Waiting for reply...").
- **File Explorer Pagination**: Added a "Load More" button in the file selector to handle large directories and prevent WebSocket "Message too long" errors.
- **AI Analysis Guard**: The "AI Analyze" button now requires at least one significant file to be selected and shows a helpful tooltip if disabled.
- **Default Selection Category**: The first selected important file now defaults to "Article", while subsequent ones default to "other".

### Fixed
- **YAML-First Parsing**: Refactored the metadata parser to prioritize YAML and added support for list-based structures often returned by newer models (e.g., gemini-3.1-flash-lite).
- **Status Modal Stability**: Completely refactored the progress dialog to use pure reactive bindings, eliminating all flickering and "client deleted" errors.
- **Scanner Performance & OOM Prevention**: Optimized file scanning using fast string operations and a 0.5s UI update throttle to reduce CPU/memory pressure.
- **Metadata Models**: Restored default mandatory fields while maintaining flexibility for AI drafting states.
- **Chat Experience**: Implemented intelligent auto-scrolling and fixed horizontal overflow for code/YAML blocks.
- **File Selection UI Sync**: Fixed the bug where the selection bar didn't update after using the editor.
- **Project Switch Cleanup**: Opening a new project now correctly resets all internal agent and UI states.
- **File Role Persistence**: Fixed critical bug where `AIAnalysis` model was missing `model_config = {"populate_by_name": True}`, causing file roles (Article/Other) to be lost when switching projects.

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
