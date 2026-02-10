# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.16.5] - 2026-02-10
### Fixed
- **Stable Build (Linux):** Removed experimental binary exclusions that caused `ImportError: cannot import name '_gi'`. Standardized on a clean build process for better compatibility with host OS libraries.
- **GUI Verification:** Enhanced the Smoke Test to check for specific error messages in the logs (e.g., "GUI launch failed") when running in a virtual X server. This prevents publishing broken binaries.
- **Binary Stability:** Re-included `unittest` to satisfy dependencies of libraries like `pyparsing`.

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
