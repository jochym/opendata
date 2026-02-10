# OpenData Tool - Beta Tester Manual

**Version:** v0.12.0
**Status:** Proof of Concept (PoC) / Beta
**Target Audience:** Domain Scientists (Physics, Medical Physics) & Research Data Stewards

---

## 1. Introduction & Mission
The **OpenData Tool** is an AI-powered assistant designed to "read" your research directory and automatically draft high-quality metadata for the [RODBUK](https://rodbuk.pl/) repository. 

**Our Goal:** To see if Generative AI (Google Gemini) can accurately interpret complex scientific data (VASP, Phonopy, DICOM, LaTeX) with minimal human help.

**Your Role:** As a beta tester, your job is to use the tool on real-world data, identify where the AI fails, and "teach" it using the chat interface. We need you to break it so we can fix it.

### Core Safety Guarantee
> 🛡️ **Read-Only Promise:** This tool is strictly **READ-ONLY**. It will scan your files to extract text and headers, but it will **NEVER** modify, delete, or move your original research data. All metadata and packages are created in a separate workspace (`~/.opendata_tool/`).

---

## 2. Installation & Setup

### Prerequisites
- **OS:** Windows 10/11, macOS (Arm64/Intel), or Linux (x64).
- **Google Account:** Required for AI features (to access Gemini).
- **Access:** You must be whitelisted for the internal testing team. Contact `Pawel T. Jochym` if you cannot sign in.

### Step-by-Step Launch
1. **Download:** Get the latest binary for your OS from the [Testing Portal](website/index.html) or your distribution source.
2. **Run:** Double-click the executable (`opendata-win.exe`, `opendata-linux`, or `.dmg`).
   - *Note:* On Windows/Mac, you may need to "Run Anyway" if the app is unsigned.
3. **Control Window:** A small window will appear. This is your "Kill Switch". 
   - **Green Light:** Server is running.
   - **Open Dashboard:** Relaunches the browser if you closed it.
   - **Quit:** Stops the server and exits.
4. **Browser Dashboard:** The main interface will open automatically in your default web browser (usually `http://localhost:8000`).

---

## 3. The Workflow: A Walkthrough

### Phase 1: Sign In & Configure
1. Click **"Sign in with Google"** in the top-right corner.
2. Grant the requested permissions. 
   - *Why?* The tool sends text snippets from your files to your personal Google Gemini instance for analysis.
3. (Optional) Go to the **Settings** tab to choose your preferred AI Model (e.g., `gemini-1.5-flash` for speed, `gemini-1.5-pro` for reasoning).

### Phase 2: Select a Project
1. Click the **folder icon** in the top-left project bar.
2. Navigate to your research directory (e.g., `/home/user/data/my_paper_project`).
3. Click **"Select Directory"**.
4. **Scanning:** The tool will index your files. 
   - *Watch:* The **Package Tab** will populate with a file list.
   - *Performance:* It can handle 10,000+ files easily.

### Phase 3: The "Chat" Loop (Analysis)
1. Go to the **Analysis Tab**.
2. Click **"Start Analysis"** (or type "Analyze this project").
3. **The Proposal:** The AI will look at your `README.md`, `*.tex`, `*.docx`, or `VASP` files. It will propose a "Main Paper" and draft initial metadata.
   - *Example:* "I found 'manuscript.tex'. Should I use it as the primary source?"
4. **Refinement:** Use the chat to correct it.
   - *User:* "Yes, but add 'John Doe' as a co-author."
   - *User:* "The license should be CC-BY-4.0."
   - *User:* "In this lab, *.dat files are always specific heat measurements." (The AI will ask to save this as a **Protocol**).
5. **Transparency:** Look for `[System]` messages in the chat. They tell you exactly what the AI is reading.
   - If the AI gets stuck, hit the **Stop Button** (square icon) in the input bar.

### Phase 4: Metadata Review
1. Switch to the **Preview Tab**.
2. Review the drafted RODBUK metadata (Title, Authors, Abstract, Keywords).
3. **Edit Manually:** You can click the "Edit" (pencil) icon on any field to override the AI.

### Phase 5: Packaging
1. In the **Preview Tab**, click **"Generate Package"**.
2. The tool will create a ZIP file containing:
   - `metadata.json` / `metadata.yaml` (RODBUK Schema)
   - `README.md`, `LICENSE`, `codemeta.json` (Documentation)
   - *Note:* It currently does NOT include the heavy data files (to keep packages light for testing).
3. The browser will prompt you to download the ZIP.

---

## 4. Feature Highlights & Tips

### 📂 File Explorer (Package Tab)
- **Checkboxes:** You can manually include/exclude specific files.
- **Smart Filters:** Type `.tex` or `README` in the filter bar to find files quickly.
- **Lazy Loading:** Scroll down to load more files.

### 🧠 Protocols (Meta-Learning)
- If you find yourself repeating instructions (e.g., "Always ignore the 'tmp' folder"), tell the AI!
- It will ask: *"Should I remember this rule?"*
- Say **"Yes"**.
- Check the **Protocols Tab** to see your saved rules. These will be applied automatically to *all* future projects.

### ⚡ Interactive Forms
- Sometimes the AI is unsure (e.g., "I found two different titles").
- It will show a **Interactive Form** in the chat.
- Select the correct option and click "Submit".

---

## 5. Troubleshooting & Bug Reporting

### Common Issues
- **"Rate Limit Hit":** You might see a "Waiting 2s..." message. This is normal; the AI is backing off to respect Google's API limits.
- **Infinite Loading:** If the UI freezes, refresh the browser page. The server state is persistent.
- **Corrupt Project:** If a project won't load, try selecting a different one, then delete the broken one from the dropdown list.

### 🐞 Reporting a Bug
We have a built-in diagnostic tool.
1. In the chat box, type: `/bug`
2. Press Enter.
3. The tool will generate a zip file containing logs, the current metadata draft, and chat history.
4. Email this zip file to `jochym@ifj.edu.pl` with a short description of what happened.

---

## 6. Testing Checklist (What we need you to try)

- [ ] **Scan a Physics Project:** Does it detect VASP/Phonopy/ALAMODE files?
- [ ] **Scan a Paper:** Does it correctly extract Title/Abstract/Authors from a LaTeX or Word file?
- [ ] **Teach a Protocol:** Create a custom rule (e.g., "Ignore 'old' folders") and see if it works on a *new* project.
- [ ] **Interrupt the AI:** Click the "Stop" button while it's thinking. Does it recover gracefully?
- [ ] **Package It:** Generate a ZIP and check if the `metadata.yaml` looks correct.

Thank you for helping us shape the future of Open Science tools!
