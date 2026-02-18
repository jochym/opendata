# Supported Platforms

OpenData Tool is tested and built for the following operating systems and versions.

## Officially Supported Systems

### Linux Distributions

| Distribution | Version | Codename | Support Status |
|-------------|---------|----------|----------------|
| **Ubuntu** | 22.04 LTS | Jammy Jellyfish | ✅ Supported |
| **Ubuntu** | 24.04 LTS | Noble Numbat | ✅ Supported |
| **Debian** | 12 | Bookworm | ✅ Supported |
| **Debian** | 13 | Trixie | ✅ Supported |
| **RHEL** | 9 | Plow | ✅ Supported (via Rocky Linux) |
| **Rocky Linux** | 9 | | ✅ Supported |

**Note:** For Linux, we provide separate binaries for each distribution to ensure maximum compatibility. If your distribution is not listed, try the binary for the closest related distribution (e.g., use Ubuntu 22.04 binary for Linux Mint 21.x).

### Windows

| Version | Architecture | Support Status |
|---------|-------------|----------------|
| **Windows 10** | x86_64 | ✅ Supported |
| **Windows 11** | x86_64 | ✅ Supported |
| **Windows Server 2019+** | x86_64 | ✅ Supported |

**Note:** A single universal binary is provided for all Windows versions.

### macOS

| macOS Version | Architecture | Support Status |
|--------------|-------------|----------------|
| **macOS 13** (Ventura) | Intel (x86_64) | ✅ Supported |
| **macOS 14** (Sonoma) | Apple Silicon (ARM64) | ✅ Supported |
| **macOS 15** (Sequoia) | Apple Silicon (ARM64) | ✅ Supported |

**Note:** We provide separate binaries for Intel and Apple Silicon Macs. Choose the appropriate binary for your hardware:
- **Intel Macs (2019 and earlier):** Use `opendata-macos-intel`
- **Apple Silicon Macs (M1/M2/M3, 2020+):** Use `opendata-macos-arm`

## System Requirements

### Minimum Requirements

- **Python:** 3.11 or higher (included in binaries)
- **RAM:** 2 GB minimum, 4 GB recommended
- **Disk Space:** 500 MB for application + space for projects
- **Display:** 1280x720 resolution or higher

### Linux Dependencies

Most modern Linux distributions include the required libraries by default. If you encounter errors, install these packages:

**Ubuntu/Debian:**
```bash
sudo apt-get install -y python3-tk libxcb-xinerama0 libxcb-cursor0
```

**RHEL/Rocky Linux:**
```bash
sudo dnf install -y python3-tk libxcb-xinerama0 libxcb-cursor0
```

### Windows Dependencies

No additional dependencies required. The binary includes all necessary components.

### macOS Dependencies

No additional dependencies required. The binary includes all necessary components.

## Testing Matrix

Every release is tested on all supported platforms using GitHub Actions:

- ✅ Unit tests (all platforms)
- ✅ GUI smoke tests (all platforms)
- ✅ Binary launch verification (all platforms)
- ✅ Server responsiveness check (all platforms)

## Unsupported Systems

The following systems are **not officially supported**:

- ❌ Windows 7/8/8.1 (end of life)
- ❌ macOS 12 and earlier (end of life)
- ❌ Ubuntu 20.04 and earlier (end of life)
- ❌ Debian 11 and earlier (oldoldstable)
- ❌ 32-bit systems (no longer tested)

However, the application may still work on these systems. If you encounter issues, please try building from source.

## Building from Source

If your system is not supported by our pre-built binaries, you can build from source:

```bash
pip install -e ".[dev]"
python src/opendata/main.py
```

For creating a binary on your system:

```bash
pip install pyinstaller
pyinstaller --onefile --name opendata-custom src/opendata/main.py
```

## Reporting Issues

If you encounter platform-specific issues, please report them on GitHub with:
- Your operating system and version
- The binary you're using
- Error messages from the terminal/logs

## Support Timeline

We follow the LTS (Long Term Support) model for our supported platforms:

- **Ubuntu LTS:** Supported for 5 years from release
- **Debian Stable:** Supported until next stable release
- **RHEL/Rocky:** Supported for 10 years from release
- **Windows:** Supported while Microsoft provides security updates
- **macOS:** Supported for the 3 most recent versions

## Questions?

If you have questions about platform support, please open an issue on GitHub.
