# PyApp Build Configuration for OpenData Tool

This directory contains the configuration for building OpenData binaries using [PyApp](https://github.com/ofek/pyapp).

## What is PyApp?

PyApp is a Rust-based wrapper that creates standalone Python application binaries. It provides:
- Cross-platform binary builds (Linux, Windows, macOS)
- Self-updating capabilities
- Minimal runtime footprint
- No Python installation required for end users

## Build Instructions

### Prerequisites

1. **Install Rust** (required for building):
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

2. **Get PyApp source** (latest release):
   ```bash
   # Linux/macOS
   curl -L https://github.com/ofek/pyapp/releases/latest/download/source.tar.gz -o pyapp-source.tar.gz
   tar -xzf pyapp-source.tar.gz
   mv pyapp-v* pyapp-latest
   
   # Windows (PowerShell)
   Invoke-WebRequest https://github.com/ofek/pyapp/releases/latest/download/source.zip -OutFile pyapp-source.zip
   Expand-Archive pyapp-source.zip
   Move-Item pyapp-v* pyapp-latest
   ```

### Configuration

PyApp is configured via environment variables. The key variables are:

| Variable | Value | Description |
|----------|-------|-------------|
| `PYAPP_PROJECT_NAME` | `opendata-tool` | Package name from PyPI |
| `PYAPP_PROJECT_VERSION` | (from VERSION file) | Version to install |
| `PYAPP_EXEC_MODULE` | `opendata.main` | Entry point module |
| `PYAPP_EXEC_FUNCTION` | `main` | Entry point function |
| `PYAPP_PYTHON_VERSION` | `3.11` | Python version to bundle |

### Build Commands

#### Native Builds

```bash
# Linux
cd pyapp-latest
PYAPP_PROJECT_NAME=opendata-tool \
PYAPP_PROJECT_VERSION=0.22.24 \
PYAPP_EXEC_MODULE=opendata.main \
PYAPP_EXEC_FUNCTION=main \
PYAPP_PYTHON_VERSION=3.11 \
cargo build --release

# Output: target/release/pyapp → rename to opendata-linux-pyapp
```

```bash
# Windows (PowerShell)
cd pyapp-latest
$env:PYAPP_PROJECT_NAME="opendata-tool"
$env:PYAPP_PROJECT_VERSION="0.22.24"
$env:PYAPP_EXEC_MODULE="opendata.main"
$env:PYAPP_EXEC_FUNCTION="main"
$env:PYAPP_PYTHON_VERSION="3.11"
cargo build --release

# Output: target/release/pyapp.exe → rename to opendata-win-pyapp.exe
```

```bash
# macOS (Apple Silicon)
cd pyapp-latest
PYAPP_PROJECT_NAME=opendata-tool \
PYAPP_PROJECT_VERSION=0.22.24 \
PYAPP_EXEC_MODULE=opendata.main \
PYAPP_EXEC_FUNCTION=main \
PYAPP_PYTHON_VERSION=3.11 \
cargo build --release

# Output: target/release/pyapp → rename to opendata-macos-arm-pyapp
```

#### Cross-Compilation (macOS Intel from Apple Silicon)

```bash
# Install Intel target
rustup target add x86_64-apple-darwin

# Build for Intel
PYAPP_PROJECT_NAME=opendata-tool \
PYAPP_PROJECT_VERSION=0.22.24 \
PYAPP_EXEC_MODULE=opendata.main \
PYAPP_EXEC_FUNCTION=main \
PYAPP_PYTHON_VERSION=3.11 \
cargo build --release --target x86_64-apple-darwin

# Output: target/x86_64-apple-darwin/release/pyapp → opendata-macos-intel-pyapp
```

## GitHub Actions Workflow

The CI/CD workflow (`.github/workflows/pyapp-build-binary.yml`) automates this process:

1. Installs Rust
2. Downloads PyApp source
3. Sets environment variables from VERSION file
4. Builds for each platform
5. Uploads binaries as artifacts

## Runtime Behavior

End users can run the binary directly:

```bash
# Linux/macOS
./opendata-linux-pyapp

# Windows
opendata-win-pyapp.exe
```

### Optional: Enable Self-Updates

To enable the built-in self-update command, set:
```bash
PYAPP_PROJECT_PATH="github.com/jochym/opendata"
```

This allows users to run:
```bash
./opendata-linux-pyapp app update
```

## Advantages vs PyInstaller

| Feature | PyInstaller | PyApp |
|---------|-------------|-------|
| Build Speed | Fast | Slower (requires Rust compilation) |
| Binary Size | ~50-100MB | ~30-60MB |
| Cross-Platform | Limited | Excellent |
| Self-Updates | Manual | Built-in |
| Maintenance | Python-only | Requires Rust toolchain |
| Console Hiding | `--noconsole` flag | Configuration option |

## Troubleshooting

### Build fails with "Python not found"
Ensure `PYAPP_PYTHON_VERSION` is set correctly and matches a version available in PyApp's embedded Python distribution.

### Binary crashes on startup
Check that all required dependencies are included. PyApp bundles only what's specified in the package metadata.

### macOS notarization issues
For distribution outside App Store, you may need to notarize the binary with Apple.

## References

- [PyApp Documentation](https://ofek.dev/pyapp/)
- [PyApp GitHub](https://github.com/ofek/pyapp)
- [PyApp Configuration Options](https://ofek.dev/pyapp/latest/config/project/)
- [Rust Installation](https://www.rust-lang.org/tools/install)
