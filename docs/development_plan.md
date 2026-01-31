# OpenData Tool Development Plan

This development plan outlines the roadmap to evolve the OpenData prototype into a production-ready tool for researchers. The focus is on **Psychological Safety** (preserving research data), **Frictionless UX** (no technical setup), and **Agentic Intelligence** (learning from the researcher).

---

## Phase 1: Core Engine & Workspace Architecture
**Objective:** Establish the "Source of Truth" and a robust, read-only analysis framework.

*   **Pydantic Schema Finalization:** Define strict models in `src/opendata/models.py` for RODBUK metadata, User Settings, and Field Protocols.
*   **Isolated Workspace Manager:** Implement a system to manage a hidden workspace (e.g., `~/.opendata/workspaces/`) where metadata and packages are built without touching the source directory.
*   **Human-Readable Storage (YAML):** Use YAML for all human-facing configuration and metadata drafts. Avoid JSON for these files to ensure readability and error-forgiveness.
*   **Read-Only "Lazy" Scanner:** Build a `pathlib`-based crawler that generates a "Project Fingerprint" (file tree, extensions, sizes). 
    *   **Lazy Loading:** Avoid reading large data files. Focus on file names, structure, and headers.
    *   **Chunked Reading:** Only read the first few KB of unknown files to detect headers or magic numbers.
*   **Heuristic Extractor Registry:** Create a plugin-based system for "Passive Extractors" (e.g., extracting authors from `README.md`, `pyproject.toml`, or LaTeX headers).

## Phase 2: Agentic Partner & AI Integration
**Objective:** Implement the "Frictionless" AI and the iterative metadata discovery loop.

*   **OAuth2 Identity Flow:** Implement Google/Gemini OAuth2 flow to eliminate "API Key Fatigue." Use local state to persist tokens securely.
*   **The "Protocol Store" (Meta-Learning):** Create the layer in `src/opendata/protocols/`. 
    *   **Text-to-Regex:** AI should support translating user rules (e.g., "files starting with 'raw_' are sensors") into concrete regex patterns.
*   **Context Injection Logic:** Develop the prompt-assembly engine that combines RODBUK constraints, Field Protocols, and Project Fingerprints.
*   **Iterative Chat State Machine:** Build the logic for the "Clarification Loop."

## Phase 3: Browser-Centric UI & Mobile Sync
**Objective:** Deliver the "No-Terminal" experience via NiceGUI.

*   **Guided Wizard Component:** Multi-step setup (Language -> AI Auth -> Directory Selection).
*   **The Chat Loop UI:** Specialized NiceGUI interface for the "Agentic Partner," featuring "Rule Capture" buttons.
*   **Secure Mobile Bridge:**
    *   Opt-in toggle for `0.0.0.0` binding.
    *   Dynamic QR code with local IP and session token.
*   **Real-time "Idiot Lights":** Dashboard indicators for "AI Connected," "Source Locked," and "Workspace Ready."

## Phase 4: Desktop Anchor & Distribution
**Objective:** Ensure the app feels like a "tool," not just a website.

*   **Pywebview Control Window:** Minimalist window acting as a "Kill Switch" and providing the "Open Dashboard" button.
*   **PyInstaller "Silent" Packaging:** Configure build with `--noconsole` and `--onefile`.
*   **Cross-Platform Path Handling:** Rigorous testing on Windows vs. Unix.

## Phase 5: RODBUK Packaging & Validation
**Objective:** Final output generation and compliance.

*   **Schema Validator:** Final check-pass for RODBUK JSON schema.
*   **BagIt/ZIP Packaging:** Copy source files (Lazy/Read-Only) and metadata into a compliant structure in the workspace.
*   **Submission Preview:** Final review screen.

---

## Technical Stack Summary
| Component | Technology |
| :--- | :--- |
| **UI Framework** | NiceGUI (Tailwind, Quasar-based) |
| **Desktop Wrapper** | Pywebview |
| **Data Models** | Pydantic v2 |
| **AI / LLM** | Google Gemini (via Google GenAI SDK) |
| **Auth** | OAuth2 (Google) |
| **Distribution** | PyInstaller |

---

## Testing & Quality Strategy
1.  **The "Safety" Suite:** Assert no modifications to source directories.
2.  **Heuristic & Chat Testing:** Fixture-based extraction tests and LLM mocking.
3.  **Multi-Platform CI:** GitHub Actions for Windows, Ubuntu, and macOS.
