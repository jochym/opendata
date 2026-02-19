# Building OpenData Tool Binaries

This document describes how to build OpenData Tool binaries for all supported platforms.

## Quick Start

The project includes a unified build script (`build.py`) that handles binary building for all platforms:

```bash
# Auto-detect platform and build
python build.py

# Build for specific platform
python build.py --platform linux
python build.py --platform windows
python build.py --platform macos-intel
python build.py --platform macos-arm

# Build and test the binary
python build.py --test

# Custom binary name
python build.py --name my-custom-name
```

## Prerequisites

### All Platforms

1. **Python 3.11+** (Python 3.12 recommended)
2. **PyInstaller**: `pip install pyinstaller`
3. **Project dependencies**: `pip install -e .`

### Linux

```bash
# Ubuntu/Debian
sudo apt-get install -y python3-tk libxcb-xinerama0 libxcb-cursor0 binutils

# RHEL/Rocky/Fedora
sudo dnf install -y python3-tk libxcb-xinerama0 libxcb-cursor0 binutils
```

### Windows

No additional dependencies required.

### macOS

No additional dependencies required. Xcode Command Line Tools recommended:

```bash
xcode-select --install
```

## Build Process

### 1. Install Dependencies

```bash
# Clone the repository
git clone https://github.com/jochym/opendata.git
cd opendata

# Install Python dependencies
pip install -e .
pip install pyinstaller
```

### 2. (Optional) Configure Google OAuth Credentials

If you want to embed Google OAuth credentials in the binary:

```bash
# Set environment variables
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
```

The build script will automatically create `client_secrets.json` and include it in the binary.

### 3. Run the Build Script

```bash
# Build for your current platform
python build.py

# Or specify a platform explicitly
python build.py --platform linux
```

### 4. Test the Binary

```bash
# The build script can test the binary automatically
python build.py --test

# Or test manually
./dist/opendata-linux --help
./dist/opendata-linux --headless --port 8080
```

## Build Artifacts

After a successful build, you'll find:

- **Binary**: `dist/opendata-{platform}`
- **Build files**: `build/` (can be deleted)
- **Spec file**: `opendata-{platform}.spec` (PyInstaller configuration)

## Platform-Specific Notes

### Linux

- **Build on oldest supported system** for maximum compatibility
- Ubuntu 22.04 recommended (glibc 2.35)
- Binary should work on Ubuntu 22.04+, Debian 12+, RHEL 9+, etc.
- Uses `--noconsole` flag (no terminal window)

### Windows

- Builds as `.exe` file
- Uses `--noconsole` flag (no command prompt window)
- Binary includes embedded manifest for DPI awareness
- Works on Windows 10+ (x86_64)

### macOS

- **Intel**: Build on macOS 13+ with Intel processor
- **Apple Silicon**: Build on macOS 14+ with M1/M2/M3
- Uses `--noconsole` flag (no terminal window)
- Binary is code-signed if `codesign` identity is available

## CI/CD Integration

The project uses GitHub Actions to build binaries for all platforms automatically on every tagged release.

### Workflow

1. **Tests run** on all platforms (Ubuntu, Windows, macOS)
2. **GUI smoke tests** verify the app starts correctly
3. **Binaries are built** for each platform
4. **Binary tests** ensure each binary responds to `--headless` mode
5. **GitHub Release** is created with all binaries attached

### Triggering a Release Build

```bash
# Tag a release
git tag v0.23.0
git push origin v0.23.0

# GitHub Actions will automatically:
# - Run tests
# - Build binaries for all platforms
# - Create a GitHub release
# - Upload binaries as release assets
```

## Build Script Architecture

The `build.py` script:

1. **Detects platform** automatically or uses `--platform` argument
2. **Validates paths** for all required resources (ui, prompts, VERSION)
3. **Creates client_secrets.json** from environment variables (if available)
4. **Builds PyInstaller command** with correct separators and flags
5. **Executes PyInstaller** with comprehensive module exclusions
6. **Tests the binary** (optional) to ensure it works
7. **Reports results** with binary size and location

### Key Features

- ✅ **Cross-platform**: Works on Linux, Windows, macOS (Intel and ARM)
- ✅ **Consistent**: Same build logic for all platforms
- ✅ **Validated**: Ensures all required files are included
- ✅ **Tested**: Can automatically test the built binary
- ✅ **Documented**: Clear output at each step
- ✅ **Flexible**: Supports custom names and platforms

## Troubleshooting

### Binary is too large

The binary includes all Python dependencies. Current size: ~100 MB

To reduce size:
- Exclude more modules in `build.py` (be careful not to break functionality)
- Use UPX compression (disabled by default due to compatibility issues)

### Binary doesn't start

1. **Check console output**:
   ```bash
   # Build with console enabled for debugging
   # Edit build.py: set console: True in get_platform_config()
   python build.py
   ```

2. **Check dependencies**:
   ```bash
   # Linux only - check which libraries are missing
   ldd dist/opendata-linux
   ```

3. **Check PyInstaller warnings**:
   ```bash
   cat build/opendata-*/warn-opendata-*.txt
   ```

### Build fails on macOS

- Ensure Xcode Command Line Tools are installed
- Check that you have Python 3.11+ installed via Homebrew or python.org
- On Apple Silicon, you may need Rosetta for Intel builds

### Build fails on Windows

- Run the build in cmd.exe or PowerShell (not Git Bash)
- Ensure Python is in PATH
- Check Windows Defender isn't blocking PyInstaller

## Legacy Build Scripts

- `build_dist.py`: Deprecated, redirects to `build.py`
- `scripts/generate_spec.py`: Legacy spec file generator (not used in new workflow)

## Additional Resources

- [PyInstaller Documentation](https://pyinstaller.org/)
- [SUPPORTED_PLATFORMS.md](SUPPORTED_PLATFORMS.md)
- [.github/workflows/main.yml](.github/workflows/main.yml) - CI/CD configuration

---

**Last Updated**: 2026-02-19  
**Maintainer**: OpenData Tool Team
