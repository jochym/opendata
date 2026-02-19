# Supported Platforms

The OpenData Tool supports the following platforms for both development and production use:

## Operating Systems

### Linux
- **Ubuntu 22.04 LTS** (primary build environment)
- **Ubuntu 24.04 LTS**
- **Debian 12**
- **Rocky Linux 9**

### Windows
- **Windows 10** (version 1909 or later)
- **Windows 11**

### macOS
- **macOS Ventura** (13.x)
- **macOS Monterey** (12.x)

## Python Versions

- **Python 3.11** (recommended)
- **Python 3.12** (supported)

## Architecture Support

- **x86_64** (Intel/AMD 64-bit) - All platforms
- **ARM64** (Apple Silicon) - macOS only

## Binary Distribution

The official binary distribution strategy:

1. **Linux Universal Binary**: Built on Ubuntu 22.04 for maximum compatibility with glibc 2.35+
2. **Windows Binary**: Built on Windows-latest (Windows 10/11)
3. **macOS Intel Binary**: Built on macOS-13 for Intel Macs
4. **macOS ARM Binary**: Built on macOS-latest for Apple Silicon Macs

## CI/CD Testing Matrix

All code changes are tested on the following platforms before merging:

- Ubuntu 22.04
- Ubuntu 24.04
- Windows-latest (Windows 10/11)
- macOS-13 (Intel Mac)

## Minimum System Requirements

- **RAM**: 2GB (4GB recommended)
- **Disk Space**: 100MB for application, plus user project space
- **Display**: Headless operation supported; GUI requires X11 on Linux (with Xvfb for headless environments)

## Unsupported Platforms

The following platforms are no longer supported as of the latest release:

- Rocky Linux 8 (too old, Python 3.6)
- Debian 13 (pre-release)
- macOS-latest (Apple Silicon) - temporarily disabled until stable
- Any system with Python < 3.11

## Compatibility Notes

- Linux binaries built on Ubuntu 22.04 are compatible with most modern Linux distributions
- For older Linux systems, source installation is recommended
- All binaries are statically linked where possible to minimize runtime dependencies