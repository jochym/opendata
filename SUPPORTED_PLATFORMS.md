# Supported Platforms

OpenData Tool is tested and built for the following operating systems.

## Binary Distribution Strategy

### Linux - Universal Binaries

We build Linux binaries on **older, stable distributions** to ensure maximum compatibility across newer systems. This follows the best practice of "build on oldest supported target."

| Binary | Built On | Compatible With | glibc Version |
|--------|----------|-----------------|---------------|
| **opendata-linux** | Ubuntu 20.04 | Ubuntu 20.04+, Debian 11+, Linux Mint 20+, Pop!_OS 20.04+ | ≥ 2.31 |
| **opendata-rhel** | Rocky Linux 8 | RHEL 8+, Rocky Linux 8+, AlmaLinux 8+, CentOS Stream 8+ | ≥ 2.28 |

**Which binary to choose?**
- **Most users:** Use `opendata-linux` (Ubuntu 20.04 build)
- **RHEL/CentOS/Rocky users:** Use `opendata-rhel` for best compatibility

### Windows & macOS

| Platform | Binary | Architecture |
|----------|--------|-------------|
| **Windows** | `opendata-win.exe` | x86_64 (universal) |
| **macOS Intel** | `opendata-macos-intel` | x86_64 |
| **macOS Apple Silicon** | `opendata-macos-arm` | ARM64 (M1/M2/M3) |

## Officially Tested Systems

Every release is tested on:

### Linux (Test Matrix)
- ✅ Ubuntu 22.04 LTS, 24.04 LTS
- ✅ Debian 12 (Bookworm), 13 (Trixie)
- ✅ Rocky Linux 8, 9 (RHEL-compatible)

### Windows
- ✅ Windows 10 (x86_64)
- ✅ Windows 11 (x86_64)

### macOS
- ✅ macOS 13 Ventura (Intel)
- ✅ macOS 14/15 Sonoma/Sequoia (Apple Silicon)

## System Requirements

### Minimum Requirements
- **RAM:** 2 GB (4 GB recommended)
- **Disk:** 500 MB for app + project space
- **Display:** 1280×720 or higher
- **Python:** Not required (bundled in binaries)

### Linux Dependencies

Most modern distributions include required libraries. If you encounter GUI errors:

**Ubuntu/Debian/Mint:**
```bash
sudo apt-get install -y python3-tk libxcb-xinerama0 libxcb-cursor0
```

**RHEL/Rocky/AlmaLinux:**
```bash
sudo dnf install -y python3-tk libxcb-xinerama0 libxcb-cursor0
```

### Windows & macOS
No additional dependencies required.

## Unsupported Systems

The following are **not officially supported** (but may work):
- ❌ Windows 7/8/8.1 (end of life)
- ❌ macOS 12 and earlier
- ❌ Ubuntu 18.04 and earlier
- ❌ Debian 10 and earlier
- ❌ 32-bit systems

## Building from Source

If your system isn't supported by our binaries:

```bash
# Install from source
pip install -e ".[dev]"
python src/opendata/main.py

# Or create custom binary
pip install pyinstaller
pyinstaller --onefile --name opendata-custom src/opendata/main.py
```

## Support Policy

We follow LTS (Long Term Support) timelines:
- **Ubuntu LTS:** 5 years from release
- **Debian Stable:** Until next stable release
- **RHEL/Rocky:** 10 years from release
- **Windows:** While Microsoft provides security updates
- **macOS:** 3 most recent versions

## Troubleshooting

### Binary won't start on Linux?
1. Try the RHEL binary (`opendata-rhel`) for better glibc compatibility
2. Install missing dependencies (see above)
3. Check terminal for error messages

### GUI doesn't appear?
```bash
# Run in headless mode to test
./opendata-linux --headless --port 8080
# Then open browser: http://127.0.0.1:8080
```

### Still having issues?
Please open a GitHub issue with:
- Your OS and version
- Which binary you're using
- Error messages from terminal

---

**Last Updated:** 2026-02-18  
**Current Version:** 0.22.0
