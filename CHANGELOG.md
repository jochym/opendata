# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
