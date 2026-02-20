# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.22.21] - 2026-02-20
### Fixed
- **UI**: Fixed a bug where the inventory window state was not updating after a scan triggered from the Analysis/Chat panel.
- **UI**: Removed broken experimental AI scan function that was causing LSP errors.

### Changed
- **UI**: Optimized inventory refresh logic by consolidating `load_inventory_background` calls.

## [0.22.20] - 2026-02-20
### Added
- **CLI**: Added `--version` argument to display the application version and exit.
- **UI**: Added inventory and selection statistics to the **Package** tab (total files, selected ratio, estimated size).
- **UI**: Statistics in the Package tab now include visual icons and bold formatting for better readability.
- **I18n**: Added Polish translations for the new package statistics labels.
- **Testing**: Added unit tests for CLI version display and package tab statistics.
- **Git**: Added "Iron Rule" for feature branches to `AGENTS.md`.

### Fixed
- **UI**: Fixed a bug where the scan progress box disappeared silently; scan statistics are now permanently added to the chat history.
- **Version**: Fixed `get_app_version()` to correctly locate the `VERSION` file in the package directory.

### Changed
- **Performance**: Optimized Package tab rendering by caching inventory statistics in the session state (O(1) rendering).
- **CI/CD**: Improved Linux binary verification by adding **Debian 13** (Trixie) to the test matrix.
- **CI/CD**: Unified build process using a new `build_binary.py` script for better cross-platform reliability.

## [0.22.1] - 2026-02-18
### Changed
- **CI/CD**: Simplified Linux distribution from 5 binaries to 2 universal builds (Ubuntu 20.04 and Rocky Linux 8)
- **CI/CD**: Added comprehensive GUI smoke tests on all supported platforms before build
- **CI/CD**: Added binary verification tests - each binary must launch and respond before release
- **CI/CD**: Build on oldest supported systems (Ubuntu 20.04, Rocky 8) for maximum compatibility
### Added
- **Documentation**: Added SUPPORTED_PLATFORMS.md with clear guidance on binary selection
- **Testing**: Test matrix now covers Ubuntu 22.04/24.04, Debian 12/13, Rocky Linux 8/9, Windows 10/11, macOS Intel/ARM

## [0.22.0] - 2026-02-18
### Added
- **Modern Google GenAI Provider**: Introduced a new AI provider based on the `google-genai` SDK, offering better performance and stability.
- **Structured AI Telemetry**: Implemented a comprehensive logging system for AI interactions with unique UUID tracking and automated prompt sanitization (blob truncation) for privacy and readability.
- **Project Management API**: Added a REST API (localhost-only, opt-in via `--api`) for programmatic project loading and configuration, enabling full test automation.
- **Automated E2E Testing**: Established a robust testing infrastructure using Playwright and Xvfb for fully automated GUI and workflow verification.
- **Enhanced Documentation**: Reorganized and consolidated documentation into dedicated User (`docs/`) and Developer (`docs/dev/`) sections.

### Fixed
- **Field Protocol Persistence**: Resolved a long-standing bug where field protocol selections were lost during rescans or tab switches. Settings are now reliably stored in `project_config.json`.
- **Protocol Decoupling**: Completely separated tool configuration (field protocols) from RODBUK repository metadata, preventing interference between classification and tool behavior.
- **Parser Robustness**: Improved AI response parsing to handle varied data structures (funding strings, contributor lists, affiliations) and prevent metadata corruption.
- **UI Event Handling**: Fixed a critical `AttributeError` in NiceGUI event processing during field protocol selection.

### Changed
- **User-Centric Protocols**: Removed automatic heuristics for field protocol detection to give users 100% control over exclusion patterns and prompts.
- **Large Dataset Optimization**: Improved test performance on multi-gigabyte datasets by automatically trimming file lists for AI analysis.
## [0.21.4] - 2026-02-14
### Fixed
- **CI/CD Build**: Fixed binary build failures on macOS and Linux by replacing `sed` with a cross-platform Python version injector and removing the `git` dependency in build containers.

## [0.21.3] - 2026-02-14
### Added
- **Build-time Versioning**: The application version now automatically includes the git commit SHA (e.g., `0.21.3+a3ffbb6`). This is baked into binaries during the CI/CD process and detected dynamically in development mode.

## [0.21.2] - 2026-02-14
### Fixed
- **Metadata Aliases**: Fixed critical issue where aliased fields (e.g., `kindof_data`) were not correctly populated during metadata updates.
- **Project State Integrity**: Added `significant_files` field to `ProjectFingerprint` model to prevent data loss during persistence.
- **Context Injection**: Fixed a bug where files matching glob patterns (e.g., `@src/*.py`) were listed in chat but not actually injected into the AI context.
- **Robustness**: Improved metadata validation to prevent complex objects (authors, contacts) from being overwritten by simple strings from UI forms.
- **Testing**: Expanded test suite to cover hierarchical protocol resolution, AI prompt generation, and edge cases in AI response parsing.

## [0.21.1] - 2026-02-14
### Added
- **Comprehensive Testing Suite**: Implemented a structured testing infrastructure with unit and integration tests.
- **Realistic Research Fixtures**: Added semi-legitimate physics and chemistry project fixtures for end-to-end testing of heuristic extraction.
- **Agent Mandate**: Updated `AGENTS.md` to strictly require that every new functionality and structural change must be accompanied by a complete testing suite.
### Fixed
- **Testability**: Refactored `ProjectAnalysisAgent` to support full Dependency Injection, enabling isolated unit testing.

## [0.21.0] - 2026-02-13
### Added
- **AI-Driven Heuristics**: Replaced traditional local parsers with a purely AI-driven file identification phase. The AI now analyzes the project structure to find the most significant files for metadata extraction.
- **Three-Phase Workflow**: Implemented a clear, linear analysis sequence: **Scan** (Inventory) -> **Heuristics** (File Identification) -> **AI Analyze** (Content Extraction).
- **Significant Files Management**: Added an interactive, foldable UI component to view and manually edit the list of files identified for deep analysis.
- **Enhanced Metadata Rendering**:
    - **Software Badges**: Software names are now displayed as badges with version details in tooltips.
    - **Funding Badges**: Funder and award information is regularized into "Agency (ID)" badges with full details in tooltips.
- **Prompt Architecture Documentation**: Created `docs/PROMPT_ARCHITECTURE.md` detailing the hierarchical protocol system and context injection mechanics.

### Changed
- **AI Timeout**: Increased OpenAI/Ollama provider timeout to 120 seconds to handle slower local endpoints.
- **Context Injection**: The AI analysis phase now actively reads and sends the full text content of all identified significant files (papers, configs, READMEs).
- **Protocol Naming**: Renamed "Global" protocol to **"User"** protocol to better reflect its per-user configuration nature.

### Fixed
- **Stability**: Fixed several `AttributeError` and `TypeError` crashes during AI response parsing and form submission.
- **Data Integrity**: Implemented robust Pydantic validators to handle structured AI responses (e.g., software/funding as dictionaries) and ensure consistent metadata updates.
- **UI Responsiveness**: Added `try...finally` blocks to all background tasks to ensure the scanning spinner is always reset, even on failure or cancellation.
- **Auto-Open**: Selecting a directory via the folder browser now automatically opens the project and initializes its state.
- **Database Initialization**: Fixed `sqlite3.OperationalError` by ensuring project directories are created before initializing the inventory database.

## [0.20.12] - 2026-02-13
### Fixed
- **AI Response Parsing**: Added robust handling for malformed JSON and error messages from AI providers.
- **UI Polish**: Adjusted field heights and padding in the metadata panel to prevent text clipping.
- **Cancellation**: Improved visual feedback when stopping an active AI analysis.

## [0.20.11] - 2026-02-13
### Added
- **Diagnostic Logging**: Implemented standard logging system with command-line switches.
- **CLI Arguments**: Added `-v`/`--verbose` (DEBUG) and `-q`/`--quiet` (ERROR) flags to control log verbosity.
- **Process Logging**: Ensured consistent logging configuration across the main process and the server subprocess.

## [0.20.10] - 2026-02-12
### Changed
- **Binary Optimization**: Reverted to `slim` Docker container for Linux builds and removed UPX compression (which was ineffective). Maintained module exclusions to keep the bundle size manageable.

## [0.20.9] - 2026-02-12
### Fixed
- **Linux Build**: Switched from Docker container to native Ubuntu runner for more reliable dependency management and UPX support.

## [0.20.8] - 2026-02-12
### Fixed
- **Linux Build**: Switched to non-slim build container and corrected UPX package name to resolve build failures.

## [0.20.7] - 2026-02-12
### Fixed
- **CI/CD Pipeline**: Fixed YAML syntax error and job structure in GitHub Actions workflow.

## [0.20.6] - 2026-02-12
### Added
- **Anchor UI Improvements**: Added version number and "About" description to the Desktop Anchor window.
### Changed
- **Binary Optimization**: Enabled UPX compression and expanded module exclusions (matplotlib, PyQt, IPython, etc.) across all platforms to reduce binary size.

## [0.20.5] - 2026-02-12
### Changed
- **Version Management**: Implemented "Single Source of Truth" for versioning. The version is now defined only in `src/opendata/VERSION` and used dynamically by `pyproject.toml` and the application code.

## [0.20.4] - 2026-02-12
### Fixed
- **Linux Binary**: Fixed missing Tkinter in Linux binary by removing it from PyInstaller excludes and installing system dependencies in the build container.

## [0.20.3] - 2026-02-12
### Changed
- **Code Quality**: Improved NiceGUI multiprocessing fix with better documentation and cleaner imports. The fix properly handles NiceGUI's intentional early return in child processes by manually starting uvicorn when needed.

## [0.20.2] - 2026-02-11
### Added
- **AI Status in Settings**: The Settings tab now displays the active AI provider and the currently logged-in account (email for Google, base URL for OpenAI/Ollama).

## [0.20.1] - 2026-02-11
### Fixed
- **Linux Build Environment**: Added `binutils` to the Linux build container, resolving the `objdump` requirement for PyInstaller.

## [0.20.0] - 2026-02-11
### Changed
- **Architectural Shift**: Removed all system tray (`pystray`) and desktop anchor (`pywebview`) logic. The application now runs as a pure Terminal + Browser (NiceGUI) service for maximum cross-platform reliability and simplicity.
- **Dependency Cleanup**: Removed `pystray`, `Pillow`, and `qrcode` from core dependencies.
- **CI/CD Optimization**: Greatly simplified the build pipeline by removing GUI-specific system headers and metadata hacks.
### Added
- **Version Display**: Added the application version number to the Settings tab for easier identification.

## [0.19.5] - 2026-02-11
### Fixed
- **Linux Tray Menu**: Included `libayatana-appindicator3-dev` in the build container. This ensures the necessary system headers are present for `PyGObject` to link against the AppIndicator libraries used by GNOME, which should restore functional tray menus in the distributed binary.

## [0.19.4] - 2026-02-11
### Fixed
- **Linux Build**: Changed CI/CD strategy to install `PyGObject` from source (pip) within the build container. This ensures `dist-info` metadata is correctly generated, allowing PyInstaller to bundle the GTK bindings without hacks.
- **Binary Size**: Significantly reduced Linux binary size by explicitly excluding unused heavy libraries (`matplotlib`, `PyQt5`, `PyQt6`, `tkinter`) from the build.
- **About Action**: Tray menu "About" now opens the dashboard URL in the default browser, ensuring consistent behavior across all platforms.

## [0.19.3] - 2026-02-11
### Fixed
- **Linux Build**: Restored `PyGObject` (`gi`) support in the binary build. PyInstaller now correctly bundles the `gi` module by manually injecting package metadata in the build container, resolving the "No module named 'gi'" error and enabling the `gtk` backend for the system tray icon.

## [0.19.2] - 2026-02-11
### Fixed
- **GNOME Tray Menu**: Delayed menu attachment to the system tray icon until *after* the icon is visible. This resolves issues on GNOME where the menu would fail to render if attached during initialization.

## [0.19.1] - 2026-02-11
### Fixed
- **Linux Tray Menu**: Removed the default action from the system tray icon to prevent menu hijacking on certain desktop environments (e.g., GNOME with AppIndicator). The icon now explicitly opens the menu on click, ensuring access to "Open Dashboard" and "Quit" options.
- **Diagnostics**: Added logging of the desktop environment (`XDG_CURRENT_DESKTOP`) to assist in debugging Linux UI issues.

## [0.19.0] - 2026-02-11
### Changed
- **Python Upgrade**: Upgraded the required Python version to `>=3.11`.
- **CI/CD Modernization**: Switched GitHub Actions and Linux build container to Python 3.11 and `python:3.11-slim-bookworm` (Debian 12). This provides a modern, stable base for current dependencies.

## [0.18.7] - 2026-02-11
### Fixed
- **System Tray Menu**: Simplified the tray menu structure to improve compatibility across different Linux desktop environments (resolved missing menu issue).

## [0.18.6] - 2026-02-11
### Added
- **Tray Icon Branding**: Updated the system tray icon to match the application logo (OpenData "OD" logo with sparkles on a navy background).
- **Expanded Tray Menu**: Added "About", "Start Dashboard", and "Quit OpenData" actions to the system tray menu.
- **Improved Error Messaging**: Provided specific installation hints (`python3-gi`, `libayatana-appindicator3-1`) for Linux users when the system tray icon fails to initialize.

## [0.18.5] - 2026-02-11
### Fixed
- **Version Detection**: Corrected the version detection logic to properly display the version number in the UI tooltip across all execution modes (development, bundled, and installed).
- **Packaging**: Included the `VERSION` file in the package data and PyInstaller bundle.

## [0.18.4] - 2026-02-11
### Changed
- **Dependency Cleanup**: Removed `webkit` and `pywebview` related dependencies and build flags as they are no longer required after the `pystray` migration.
- **CI/CD Optimization**: Simplified the Linux build and test environment by removing redundant metadata injection steps.

## [0.18.3] - 2026-02-11
### Changed
- **CI/CD Architecture**: Migrated Linux builds to a `python:3.10-slim-bullseye` (Debian 11) container. This improves binary compatibility across different Linux distributions by building on an older glibc baseline.

## [0.18.2] - 2026-02-11
### Added
- **Version Tooltip**: Added application version number to the logo tooltip in the header.
### Fixed
- **Linux Stability**: Added robust error handling and fallback to terminal mode for `pystray` system tray icon, resolving crashes on systems with missing `libayatana-appindicator` libraries.

## [0.18.1] - 2026-02-11
### Fixed
- **Curator Recommendations**: AI suggestions are now persistent across app restarts and session changes. 
- **Recommendation UI**: Added "Dismiss" (hide) and "Forget" (delete) buttons to the recommendations banner to allow better control over precious data.
- **Data Integrity**: Modified the analysis loop to prevent unrelated metadata questions from clearing file suggestions.
- **Project State**: Fixed a crash on project load due to project state schema mismatch.
### Documentation
- **Manuals**: Updated Tester and Developer manuals to reflect the migration to `pystray` and new curator workflows.

## [0.18.0] - 2026-02-11
### Changed
- **Architecture Migration:** Replaced `pywebview` with `pystray` + `NiceGUI` (Browser mode). The application now runs as a system tray service, opening the dashboard in the default system browser. This simplifies cross-platform UI dependencies and improves stability.
- **Headless Mode:** Improved `--no-gui` mode to work without X11/GUI dependencies by deferring imports of `pystray` and `Pillow`.
### Added
- **Procedural Icon:** Integrated a generated system tray icon to ensure the application remains functional without external asset dependencies.
### Removed
- **Dependency:** Removed `pywebview` as a core dependency.

## [0.17.2] - 2026-02-10
### Fixed
- **Linux GUI Compatibility:** Aggressively excluded core C++ runtime libraries (`libstdc++.so.6` and `libgcc_s.so.1`) from the binary bundle. This prevents `CXXABI` version conflicts with the host OS, enabling successful WebKitGTK initialization on modern distributions like Debian 13 and Ubuntu 24.04.

## [0.17.1] - 2026-02-10
### Fixed
- **CI/CD Uniformity:** Standardized the entire pipeline on `ubuntu-22.04` to ensure consistent availability of system libraries (like `libwebkit2gtk-4.0-dev`) across test and build stages. This resolves package location errors observed on newer Ubuntu distributions in CI.

## [0.17.0] - 2026-02-10
### Fixed
- **Infrastructure Stabilization:** Rolled back build environment to Python 3.10 and Ubuntu 22.04 for binary distribution. This configuration is highly stable for PyInstaller and resolves infinite recursion errors and GI import failures observed in newer environments.
- **Binary Distribution:** Reverted to simplified CLI-based PyInstaller calls for robust asset bundling.
- **GUI Verification:** Continued use of GUI Smoke Tests to guarantee binary health.

## [0.16.4] - 2026-02-10
### Fixed
- **Website UI/UX Redesign:** Dramatically improved the look and feel of the documentation sections. Integrated `Highlight.js` for syntax highlighting and applied premium typography styles to the Markdown renderer. The portal now features a high-end, professional design consistent with modern scientific tools.

## [0.16.3] - 2026-02-10
### Added
- **Integrated Documentation:** Added dynamic Markdown rendering to the website. The Beta Tester Manual and Developer Guide are now accessible directly on the portal, rendered from the repository's source docs.

## [0.16.2] - 2026-02-10
### Fixed
- **Stable Build Environment:** Standardized on Python 3.11 across all platforms. This version provides the best compatibility between modern Google AI libraries and PyInstaller's dependency analysis, resolving the infinite recursion errors observed with Python 3.12.

## [0.16.1] - 2026-02-10
### Fixed
- **Build Environments:** Tailored Python versions per platform (3.12 for Linux/Windows, 3.11 for macOS) to resolve PyInstaller recursion errors on macOS and modern system warnings elsewhere.
- **CI/CD Build (Linux):** Restored isolated Python environments to bypass PEP 668 restrictions while maintaining system-wide GObject integration.

## [0.16.0] - 2026-02-10
### Added
- **GUI Smoke Test:** Integrated automated GUI verification in the Linux CI pipeline using `Xvfb`. Binaries are now launched in a virtual framebuffer to ensure stability before release.
### Fixed
- **CI/CD Modernization:** Upgraded the build environment to Python 3.12 across all platforms.
- **Binary Stability:** Restored the `unittest` module to the binary bundle, resolving import failures in third-party libraries (e.g., `pyparsing`).
- **Resource Loading:** Further refined absolute path resolution for assets during cross-platform builds.

## [0.15.1] - 2026-02-10
### Fixed
- **Cross-Platform Assets:** Fixed missing prompts and resources on Windows and macOS by using absolute paths during `.spec` file generation.
- **Unified Secret Injection:** Ensured that `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are passed to the build process on all platforms, guaranteeing built-in OAuth2 credentials in all distributed binaries.

## [0.15.0] - 2026-02-10
### Fixed
- **OAuth2 (Built-in Secrets):** Refined the build-time secret injection process. Secrets are now generated and bundled via a dedicated Python script, ensuring they are always present in the final binary.
- **Linux GUI (Library Conflict Fix):** Resolved the `MOUNT_2_40` version mismatch by aggressively excluding `libmount`, `libblkid`, `libuuid`, and `libselinux` from the binary bundle. This forces the application to use the host's system libraries, fixing GUI launch failures on modern Linux distributions (e.g., Ubuntu 24.04).

## [0.14.9] - 2026-02-10
### Fixed
- **CI/CD Optimization (Linux):** Completely avoided `PyGObject` compilation by manually injecting package metadata (`.dist-info`) into the CI virtual environment. This satisfies PyInstaller's hooks while using the reliable system-provided `python3-gi` package.
- **OAuth2:** Built-in secrets are now correctly resolved using the fixed `get_resource_path`.

## [0.14.8] - 2026-02-10
### Fixed
- **PyInstaller Metadata Patch:** Implemented monkey-patching of `importlib.metadata` within the `.spec` file to bypass persistent failures in PyInstaller's `gi` hook. This ensures successful Linux builds even when package metadata is not fully present in the CI environment.
- **Resource Loading:** Finalized robust asset path resolution for both dev and bundled modes.

## [0.14.7] - 2026-02-10
### Fixed
- **PyInstaller Config:** Resolved `NameError` in the generated `.spec` file by cleaning up unused variables and ensuring internal consistency. This fixes build failures on all platforms.

## [0.14.6] - 2026-02-10
### Fixed
- **PyInstaller Hooks:** Introduced custom hooks (`pyinstaller_hooks/hook-gi.py`) to bypass `importlib.metadata` failures in CI. This definitively solves the "Package metadata not found for pygobject" error during Linux builds.
- **Resource Management:** Finalized the integration of `get_resource_path` for all bundled assets.

## [0.14.5] - 2026-02-10
### Fixed
- **Package Distribution:** Updated `pyproject.toml` to explicitly include Markdown templates and UI assets in the wheel distribution.
- **Resource Loading (Final):** Enhanced `get_resource_path` to reliably detect resources across all execution modes, including pip-installed test environments in CI. This resolves "Template not found" errors during tests.

## [0.14.4] - 2026-02-10
### Fixed
- **Resource Loading:** Improved `get_resource_path` to handle multiple environments: PyInstaller bundles, pip-installed packages (CI/tests), and local development. This resolves "Template not found" errors during tests and in distributed binaries.
- **OAuth2:** Secrets are now correctly loaded from bundled resources within the one-file binary.
- **Linux GUI:** Continued use of aggressive binary exclusion to ensure host OS compatibility.

## [0.14.3] - 2026-02-10
### Fixed
- **Linux Distribution Infrastructure:** Switched to system-provided Python and packages for Linux builds. This ensures `PyGObject` is correctly recognized by PyInstaller with full metadata, bypassing all previous compilation and dependency conflict issues in the CI environment.
- **Binary Stability:** Unified the build commands to handle system-specific Python aliases correctly.

## [0.14.2] - 2026-02-10
### Fixed
- **CI/CD Build (Linux):** Switched from global `PYTHONPATH` to precision symlinking of the system `gi` module. Manually injected package metadata into the virtual environment to satisfy PyInstaller's `gi` hook without breaking `pydantic` dependencies (resolved `typing_extensions` conflict).

## [0.14.1] - 2026-02-10
### Fixed
- **CI/CD Build (Linux):** Resolved `PyGObject` compilation issues by switching to the system-provided package (`python3-gi`) and explicitly setting `PYTHONPATH`. This bypasses Meson/PkgConfig failures in the CI environment while maintaining full metadata support for PyInstaller.
- **OAuth2:** Continued refinement of the resource-path loading logic.

## [0.14.0] - 2026-02-10
### Fixed
- **OAuth2 (Baked-in Secrets):** Secrets are now correctly located within the bundled resources using `sys._MEIPASS`. Authentication works out-of-the-box in the distributed binaries.
- **Linux GUI Final Fix:** Restored standard Python 3.10 environment for Linux builds with full development headers. This allows `PyGObject` to compile correctly with full metadata, satisfying PyInstaller's requirements. Continued use of aggressive binary exclusion to ensure host OS library usage.
- **Binary Size:** Optimized binaries by stripping symbols and excluding redundant Python modules.

## [0.13.9] - 2026-02-10
### Fixed
- **OAuth2 (Baked-in Secrets):** Implemented `get_resource_path` to correctly locate bundled `client_secrets.json` within the PyInstaller environment (`sys._MEIPASS`). This enables friction-free authentication without external files.
- **Linux GUI (Final Stability):** Applied absolute exclusion of all GTK/WebKit/GLib binaries from the bundle. This guarantees zero symbol conflicts with the host OS.
- **Binary Optimization:** Reduced binary size by stripping symbols and excluding unused modules (tkinter, tcl, unittest).

## [0.13.8] - 2026-02-10
### Fixed
- **CI/CD Infrastructure:** Moved spec file generation to a dedicated Python script (`scripts/generate_spec.py`) to avoid YAML/Bash escaping issues. This ensures stable and predictable builds across all platforms.
- **Linux GUI Fix (Phase 4):** Finalized the surgical exclusion of system libraries in the dynamic spec file, which is now the default build method for Linux.

## [0.13.7] - 2026-02-10
### Fixed
- **Linux GUI Architecture:** Migrated to dynamic `.spec` file generation in CI. This allows for surgical removal of `libglib`, `libgobject`, and `libgio` from the binary bundle, forcing the application to use system libraries and resolving the `undefined symbol` error in WebKitGTK.
- **Binary Assets:** Unified asset inclusion logic within the `.spec` file for better cross-platform reliability.

## [0.13.6] - 2026-02-10
### Fixed
- **OAuth2 Authentication:** Added support for Google API credentials via environment variables (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`). The build process now "bakes in" a fallback `client_secrets.json` into the binaries.
- **Linux GUI Stability (Phase 3):** Switched to aggressive binary exclusion (`--exclude-binary`) for GLib/GObject libraries. This ensures the application uses the host's system libraries, finally resolving WebKitGTK symbol conflicts and enabling the GUI on Linux.

## [0.13.5] - 2026-02-10
### Fixed
- **Release Downloads:** Marked GitHub Releases as stable (non-prerelease) to ensure `/releases/latest/download/` links work correctly on the website.
- **Linux GUI Fix (Phase 2):** Applied more aggressive exclusions for system GLib libraries in the PyInstaller bundle to force usage of native OS libraries, resolving WebKitGTK symbol conflicts.

## [0.13.4] - 2026-02-10
### Fixed
- **Linux GUI Stability:** Excluded system libraries (GLib, GObject, Gio, libz) from the PyInstaller bundle to prevent symbol conflicts with system WebKitGTK drivers. This resolves the `undefined symbol` errors when launching the GUI.
- **CD Workflow:** Removed environment restrictions for website deployment, enabling automated updates for version tags.

## [0.13.3] - 2026-02-10
### Fixed
- **Linux Distribution:** Switched to system Python and `python3-gi` package for Linux builds to resolve PyInstaller hook failures related to missing package metadata.

## [0.13.2] - 2026-02-10
### Fixed
- **PyInstaller Cleanup:** Removed absolute-path-dependent `.spec` files that caused CI conflicts.
- **Binary Assets:** Added missing UI resources to all binaries using `--add-data`.
- **Build Robustness:** Improved cross-platform data separator handling (`:` vs `;`) in the build script.

## [0.13.1] - 2026-02-10
### Fixed
- **PyInstaller Conflict:** Resolved a conflict in the `--name` argument that caused build failures.
- **Windows Build:** Explicitly set the shell to `bash` for the build step to ensure cross-platform consistency of internal scripts.

## [0.13.0] - 2026-02-10
### Fixed
- **CI/CD Architecture:** Complete restructuring of the GitHub Actions workflow to use native YAML conditional steps (`if: runner.os == 'Linux'`). This resolves shell syntax errors on Windows runners and ensures stable cross-platform builds.
- **Linux GUI:** Finalized the integration of system-wide `PyGObject` for both testing and distribution.

## [0.12.9] - 2026-02-10
### Fixed
- **CI/CD:** Fixed cross-platform build errors by properly isolating Linux-specific system commands in the workflow.

## [0.12.8] - 2026-02-10
### Fixed
- **CI/CD (Linux):** Switched from compiling `PyGObject` via `pip` to using the system-provided `python3-gi` package. Linked the system module to the CI virtual environment to ensure successful builds and tests without complex compilation steps.

## [0.12.7] - 2026-02-10
### Fixed
- **CI/CD (Linux):** Added `gobject-introspection` and `libglib2.0-dev` to ensure `PyGObject` can be compiled by `pip` during the build process.

## [0.12.6] - 2026-02-10
### Fixed
- **CI/CD (Ubuntu 24.04):** Updated WebKit dependency to `libwebkit2gtk-4.1-dev` to match Ubuntu Noble repositories.

## [0.12.5] - 2026-02-10
### Fixed
- **CI/CD:** Moved system dependencies installation to the `test` job to ensure environment consistency across all stages.

## [0.12.4] - 2026-02-10
### Fixed
- **CI/CD (Linux):** Added missing system headers (`libgirepository1.0-dev`, `libcairo2-dev`) and `pkg-config` to the build runner to allow `PyGObject` compilation.

## [0.12.3] - 2026-02-10
### Fixed
- **Linux Binaries:** Resolved `ModuleNotFoundError: No module named 'gi'` by including GTK and GObject Introspection dependencies in the build process.
- **CD Workflow:** Website deployment is now restricted to version tags only, preventing the production site from reflecting unreleased changes in `main`.

## [0.12.2] - 2026-02-10
### Fixed
- **UI Architecture:** Transitioned from desktop-anchor to browser-first UX.
- **CI/CD:** Integrated automated build and release workflow.
