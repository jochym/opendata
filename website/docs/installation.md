# Installation Guide for Beta Testers

Welcome to the OpenData Tool testing program! This guide will walk you through the process of running the tool on your computer. The tool is prepared so that it **does not require installing Python** or any complex libraries. Everything you need is in a single file.

Note: All binary files follow the naming pattern: `opendata-<platform>-pyapp-<version>`.

---

## 🪟 Windows (10 / 11)

1. **Download:** Get the `opendata-win-pyapp-<version>.exe` file from the portal.
2. **Run:** Double-click the downloaded file.
3. **SmartScreen Warning:** Since the program is in early testing and doesn't have a digital certificate yet, Windows may show a "Windows protected your PC" window.
   - Click **"More info"**.
   - Click the **"Run anyway"** button.
4. **First Launch:** On the first run, the program may need 30 to 60 seconds to prepare its working environment. Please be patient – subsequent launches will be near-instant.
5. **How to check if it's working?** A small OpenData Tool icon will appear in your system tray (near the clock). Right-click it and select **"Open Dashboard"** to open the interface in your browser.

---

## 🍎 macOS (Intel and M1/M2/M3)

1. **Download the correct version:**
   - If you have an Apple Silicon processor (M1, M2, M3): choose `opendata-macos-arm-pyapp-<version>`.
   - If you have an older Intel processor: choose `opendata-macos-intel-pyapp-<version>`.
2. **Running (Bypassing security):** Apple is strict about apps from outside the App Store. You will see a message that the app is from an "unidentified developer".
   - **Method 1:** **Right-click** the file and select **Open**. A dialog will appear with an "Open" button that isn't there with a normal click.
   - **Method 2:** Go to *System Settings -> Privacy & Security*. Scroll down and click the **"Open Anyway"** button next to the program name.
3. **Permissions:** The program may ask for access to your "Downloads" folder or other locations you choose for analysis. Please accept these requests.

---

## 🐧 Linux (Ubuntu, Debian, Fedora, etc.)

1. **Download:** Get the `opendata-linux-pyapp-<version>` file.
2. **Grant Permissions:** After downloading, the file must be made "executable".
   - **GUI:** Right-click the file -> *Properties* -> *Permissions* -> Check **"Allow executing file as program"**.
   - **Terminal:** `chmod +x opendata-linux-pyapp-*`
3. **Run:** Double-click or type `./opendata-linux-pyapp-*` in the terminal.
4. **Dependencies:** The program is almost entirely self-sufficient, but on very "slim" Linux versions, you might need `libfuse2` or standard C libraries. If the program doesn't start, check the terminal logs.

---

## 💡 Good to Know (Potential Issues)

### ⏳ First Launch is a "Silent Installation"
The **PyApp** technology we use performs an automatic configuration of your working environment on the first run (it creates a "virtual environment").
- **Be Patient:** During the first launch, the program window (or tray icon) may appear with a significant delay (up to a minute). The system is unpacking hundreds of files needed for the AI tools.
- **Disk Space:** The program takes about 300-500 MB after unpacking in your home folder (usually in `.cache/pyapp` or similar).
- **Internet:** Although most files are in the package, we recommend an internet connection for the first launch so the program can verify the installation.

### 🌐 Browser Interface
OpenData Tool runs as a background server. The user interface opens in your default browser at `http://localhost:8080`.
- If the browser window doesn't open automatically, try entering this address manually.
- The program does not send your research data to the server without your consent (AI only needs to send text fragments for analysis after you sign in).

### 🛠️ Where to Get Help?
If the program freezes or won't start:
1. Check if the system tray icon (near the clock) is active.
2. Try closing the program (Exit in the icon menu) and restart it.
3. If the error persists, send us information at `jochym@ifj.edu.pl`, including (if possible) a screenshot of the error.
