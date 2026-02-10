# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
