# Supported Platforms

OpenData Tool is tested and built for the following operating systems.

## Binary Distribution Strategy

### Linux - Single Universal Binary

We build **one universal Linux binary** on **Rocky Linux 8** (glibc 2.28) to ensure maximum compatibility across all distributions. This follows the Linux best practice of "build on oldest supported target."

| Binary | Built On | Compatible With | glibc Version |
|--------|----------|-----------------|---------------|
| **opendata-linux** | Rocky Linux 8 | **All modern Linux:** Ubuntu 20.04+, Debian 11+, RHEL 8+, Rocky 8+, AlmaLinux 8+, Fedora 33+, Linux Mint 20+, Pop!_OS 20.04+ | ≥ 2.28 |

**Why Rocky Linux 8?**
- Oldest still-supported enterprise Linux (glibc 2.28)
- Binary built here works on ALL newer systems (Ubuntu 24.04, Debian 13, Fedora 40, etc.)
- Industry standard (used by AppImage, Steam, JetBrains IDEs)

### Windows & macOS

| Platform | Binary | Architecture |
|----------|--------|-------------|
| **Windows** | `opendata-win.exe` | x86_64 (universal) |
| **macOS Intel** | `opendata-macos-intel` | x86_64 |
| **macOS Apple Silicon** | `opendata-macos-arm` | ARM64 (M1/M2/M3) |

## Officially Tested Systems

Every release is **tested** on:

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
- **glibc:** ≥ 2.28 (all modern Linux have this)

### Linux Dependencies

Most modern distributions include required libraries. If you encounter GUI errors:

**Ubuntu/Debian/Mint/Pop!_OS:**
```bash
sudo apt-get install -y python3-tk libxcb-xinerama0 libxcb-cursor0
```

**RHEL/Rocky/AlmaLinux/Fedora:**
```bash
sudo dnf install -y python3-tk libxcb-xinerama0 libxcb-cursor0
```

### Windows & macOS
No additional dependencies required.

## Unsupported Systems

The following are **not officially supported** (but may work):
- ❌ Windows 7/8/8.1 (end of life)
- ❌ macOS 12 and earlier (end of life)
- ❌ Ubuntu 18.04 and earlier (end of life)
- ❌ Debian 10 and earlier (oldoldstable)
- ❌ RHEL/CentOS 7 and earlier (end of life)
- ❌ 32-bit systems (no longer tested)

## Building from Source

If your system isn't supported by our binaries:

```bash
# Install from source
pip install -e ".[dev]"
python src/opendata/main.py

# Or create custom binary using our unified build script
pip install pyinstaller
python build.py --platform YOUR_PLATFORM --test

# Available platforms: linux, windows, macos-intel, macos-arm
# The build script auto-detects your platform if not specified
```

## Support Policy

We follow LTS (Long Term Support) timelines:
- **Ubuntu LTS:** 5 years from release
- **Debian Stable:** Until next stable release
- **RHEL/Rocky/AlmaLinux:** 10 years from release
- **Windows:** While Microsoft provides security updates
- **macOS:** 3 most recent versions

## Troubleshooting

### Binary won't start on Linux?
1. Check glibc version: `ldd --version` (must be ≥ 2.28)
2. Install missing dependencies (see above)
3. Check terminal for error messages
4. Try running in headless mode: `./opendata-linux --headless --port 8080`

### GUI doesn't appear?
```bash
# Run in headless mode to test
./opendata-linux --headless --port 8080
# Then open browser: http://127.0.0.1:8080
```

### "version 'GLIBC_2.XX' not found"
Your system is too old. Minimum required: glibc 2.28 (Rocky Linux 8, Ubuntu 20.04, Debian 11).

### Still having issues?
Please open a GitHub issue with:
- Your OS and version
- Which binary you're using
- Error messages from terminal
- Output of `ldd --version`

---

**Last Updated:** 2026-02-18  
**Current Version:** 0.22.1  
**Universal Linux Binary:** Built on Rocky Linux 8 (glibc 2.28)
