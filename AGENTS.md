# Agent Guidelines for OpenData Tool

This repository contains the OpenData Tool, designed for preparing metadata and packaging scientific projects for the RODBUK repository. This document provides essential information for AI agents to maintain consistency and quality while ensuring a **friction-free, browser-centric, multi-platform user experience** for researchers.

## Core Principles
1. **Browser-Centric UI with Desktop Anchor:** The primary user interaction happens in the browser (NiceGUI). However, the app must launch a small, simple **Desktop Control Window** (placeholder) as a "Kill Switch".
2. **Dashboard-First Transparency:** The Desktop Control Window should include "idiot lights" (red/green) and a button to "Open Dashboard".
3. **Mobile-Ready (Optional/Secure):** The UI includes an "Open on Mobile" feature. **Security Note:** By default, the server must only bind to `localhost` (127.0.0.1). Remote access (0.0.0.0) must be explicitly enabled by the user when they request mobile access.
4. **No-Terminal Experience:** When launched as an executable, **no terminal/console must be shown**.
5. **Strictly Read-Only Analysis:** The tool must NEVER modify the contents of the user's research directory.
6. **Domain Knowledge Accumulation:** The tool must support "Meta-Learning". As users refine analysis rules (e.g., "In this lab, .dat files are always pressure logs"), the agent should extract these as permanent **Field Protocols** (instructions). These protocols must be stored in the global workspace and transferable between projects.

## Project Workflow
1. **Guided Setup (Once per user):** 
   - Language selection.
   - AI capability configuration (Consent-based OAuth2/Google Account).
   - Persistence of settings (changeable at any time).
2. **Interactive Project Analysis (The "Chat" Loop):**
   - User points to a directory.
   - **Protocol Injection:** The agent reads both global instructions and the user's custom **Field Protocols**.
   - **Iterative Interaction:** The tool enters a specialized chat-like loop where the agent proposes metadata and asks for clarifications.
   - **Knowledge Capture:** If the user provides a repeatable rule, the agent asks: "Should I remember this rule for future projects in this field?"
3. **Metadata Refinement & Packaging:**
   - User reviews the final proposed RODBUK metadata and generates the package in the workspace.

## Directory Structure
- `src/opendata/ui/`: NiceGUI components for the Dashboard, Wizard, and Chat Loop.
- `src/opendata/agents/`: Specialized agent logic for project interpretation and **Protocol Learning**.
- `src/opendata/protocols/`: Storage for user-defined, field-specific instruction sets.
- `src/opendata/ai/`: Provider abstractions and configuration management.
- `src/opendata/models.py`: Pydantic models for RODBUK metadata and persistent user settings.
- `src/opendata/utils.py`: Cross-platform, read-only file utilities.


## Context Consistency & Chat Loop Best Practices (CRITICAL)
- **Stateless Model, Stateful Agent:** Models are stateless. The agent must rebuild the full context (System Prompt + Field Protocols + Current Metadata Draft + History) for every request.
- **Anchor Context with YAML:** The `current_metadata` draft (in YAML) is the "Source of Truth". Always inject it into the prompt. Never rely on the chat history for factual state.
- **Prompt Ordering:** System Prompt -> Field Protocols -> Current State (Metadata) -> Recent History -> User Input.
- **Immediate Extraction:** As soon as metadata is found or confirmed by the user, update the internal `Metadata` model. Do not leave it buried in the chat log.
- **Text-First Approximation:** For scientific projects, the primary text (LaTeX/Docx/PDF-converted-text) is the richest source of metadata. 
  - **First Prompt Strategy:** The first agent response should summarize gathered heuristics and propose the most likely "main paper" file. 
  - **The Ask:** "I've gathered these initial details. Is it okay to use [file_name] as the primary source for a first approximation of the metadata?"

## Build, Lint, and Test Commands

### Setup & Build
- Development: `pip install -e .`
- **Single Executable (No Console):** `pyinstaller --noconsole --onefile src/opendata/main.py`
- Running Tests: `pytest` (Must pass on Win/Mac/Linux).

### Vibe-Coding Verification (CRITICAL)
Every substantial step must have an accompanying automated test. Before completing a task, run the relevant test to verify the "vibe":
- **Run all tests:** `pytest`
- **Run specific test file:** `pytest tests/test_name.py`
- **Run single test case:** `pytest tests/test_name.py -k "test_function_name"`

## Registry of Accomplishments (Stage Log)
- **Phase 1 Infrastructure [COMPLETE]:** 
  - `WorkspaceManager`: Automated YAML-based persistence in `~/.opendata_tool/`.
  - `ProtocolStore`: Meta-learning logic for field-specific rule accumulation.
  - `Lazy Scanner`: TB-scale safe project fingerprinting (stat-only crawling).
  - `RODBUK Models`: Pydantic V2 schema for mandatory scientific metadata.
- **Phase 2 Extractor Registry [COMPLETE]:**
  - `BaseExtractor`: Extensible architecture for heuristic metadata discovery.
  - `LatexExtractor`: Regex-based discovery for physics papers.
  - `DocxExtractor`: Core property extraction for Office-based research.
  - `DicomExtractor`: Lazy header parsing for medical physics datasets.
  - `BibtexExtractor`: Citation-based metadata harvesting.
  - `Hdf5Extractor`: Attribute-only peeking for large hierarchical datasets.
  - `VaspExtractor`: System and version extraction for VASP calculations.
  - `LatticeDynamicsExtractor`: Specialized support for Phonopy and ALAMODE.
  - `ColumnarDataExtractor`: Detection of numeric text/CSV data clusters.
- **Phase 3 AI & OAuth2 Scaffold [COMPLETE]:**
  - `AIService`: OAuth2 identity flow for frictionless "Sign in with Google".
  - `AI_SETUP.md`: Clear developer instructions for Cloud Console configuration.
  - `ProjectAnalysisAgent`: Initial integration of heuristics and AI state.
  - **Iterative Chat Loop:** Implemented stateful conversation engine with 5-message context window and specialized physics reasoning (VASP/Phonopy/ALAMODE).
  - **External Tools:** Added recognition and automated fetching for arXiv, DOI, and ORCID identifiers.
  - **Google Search Grounding:** Enabled Gemini web search for factual verification.
  - **Model Persistence:** Integrated real-time model switching with context awareness.
- **Phase 4 Packaging & Validation [COMPLETE]:**
  - `PackagingService`: Zip-based RODBUK package generation.
  - **Metadata-Only Builder:** Implementation of intermediate packaging for submission skeletons (metadata + docs).
  - `Metadata Validator`: Domain-specific checks for scientific compliance.
  - **Read-Only Guarantee:** Verified that data is copied to workspace without modifying source.

- **Phase 5 Internationalization (i18n) [COMPLETE]:**
  - GNU gettext integration for Polish/English support.
  - Reactive language switching in the NiceGUI dashboard.
  - Dedicated `src/opendata/i18n/` module for translation management.

- **Phase 6 Project Management & Persistence [COMPLETE]:**
  - Automated project state saving (metadata, history, fingerprint) in `~/.opendata_tool/projects/`.
  - Unique project identification via path hashing.
  - Top-bar project selector for seamless switching between research directories.
  - Verified logic with `tests/test_workspace.py`.

- **Phase 7 Prompt Factorization & Management [COMPLETE]:**
  - Moved hardcoded AI prompts to external Markdown templates in `src/opendata/prompts/`.
  - Implemented `PromptManager` for dynamic rendering of system prompts and chat wrappers.
  - Decoupled AI logic from Python code for easier behavioral tweaking and token optimization.

- Phase 8 State Control & Isolation [COMPLETE]:
  - Implemented "Clear Chat History" and "Reset Metadata" buttons in the UI.
  - Added project state isolation logic to prevent cross-pollution during directory scans.
  - Fixed literal brace escaping in Markdown templates for Python's `str.format()` compliance.

- **Phase 9 Deep Analysis & UX Refinement [COMPLETE]:**
  - **Full-Text Reading:** Implemented `FullTextReader` with recursive LaTeX `\input{}` resolution and Docx support.
  - **One-Shot Extraction:** Added specialized Mega-Prompt for single-pass metadata harvesting from principal publications.
  - **Interactive UX:** Added "Cancel Scan" capability and reactive Project Path binding.
  - **Security:** Enhanced scanner to strictly ignore hidden directories (`.*`) and their contents.
  - **Navigation:** Seamless project switching with state persistence and "Guarded Load" logic.

- **Phase 10 UI/UX Enhancement [COMPLETE]:**
  - **Metadata Preview:** Redesigned authors/keywords with inline-icons, tooltips, and compact badges.
  - **Layout Optimization:** Implemented "magazine-style" text truncation with "more..." toggles and full-viewport height coordination.
  - **Chat Interface:** Overhauled with card-based bubbles, multiline input, and Ctrl+Enter submission.
  - **Persistence:** Enabled per-project and global AI model selection memory.
  - **State Sync:** Synchronized project and model selectors across all UI refreshes.

- **Phase 11 Advanced Grounding & Deep Analysis [COMPLETE]:**
  - **One-Shot Alignment:** Refactored mega-prompt to strictly match RODBUK/Pydantic schema.
  - **Auxiliary Context:** Automated injection of README and YAML metadata files into AI context.
  - **Search Grounding:** Mandatory Google Search instructions for ORCID and DOI discovery.
  - **@File Syntax:** Implemented user-driven context expansion via `@filename` in chat.
  - **Author Identity:** Enhanced author merging logic with automated ORCID scheme detection.

- **Phase 12 Scanner & UX Robustness [COMPLETE]:**
  - **Throttled Display:** Optimized file scanner with 10Hz time-based UI updates to eliminate flickering.
  - **Interactive Controls:** Added "Cancel Scan" capability and automated project list refresh.
  - **Selective Scanning:** Implemented `.ignore` file support to skip unwanted directory trees.
  - **Smart Path Shortening:** Improved path shortening (first two/last two components) with full-path tooltips.
  - **Robust Project Management:** Fixed deletion logic for partial/corrupt projects and ensured ID consistency via path resolution.

- **Phase 13 Layout Flexibility [COMPLETE]:**
  - **Resizable Dashboard:** Replaced static layout with `ui.splitter` for adjustable chat/metadata panels.
  - **Layout Persistence:** Integrated real-time saving of splitter position to global user settings.
  - **Enhanced UI Feedback:** Unified statistics and file-progress display in the scanner header.

- **Phase 14 Testing & Diagnostics [COMPLETE]:**
  - **Automated Bug Reporting:** Implemented `/bug` command for single-click diagnostic collection (System info, Metadata, Chat history).
  - **Tester Portal:** Created a dedicated landing page (`website/index.html`) with guides and downloads for domain professionals.
  - **LSP & Type Safety:** Refactored callback signatures and state handling to ensure robust agent-UI synchronization.

- **Phase 15 UI Reorganization & Branding [COMPLETE]:**
  - **Multi-tab Architecture:** Implemented a tabbed interface (Analysis, Protocols, Package, Preview, Settings) to manage increasing complexity.
  - **Responsive Header:** Optimized the top bar for narrow viewports by moving non-essential controls (model, language, mobile QR) to Settings.
  - **Branded Identity:** Designed and implemented a custom CSS-based "Open Data" logo following the official dane.gov.pl aesthetic.
  - **Workflow Isolation:** Relocated the final submission preview and package generation to the Preview tab.
  - **Enhanced Settings:** Created a centralized hub for global application configuration and AI session management.

## Code Style Guidelines

### 1. Multi-Platform Compatibility & i18n
- **Python-Centric:** All core logic must be written in Python 3.10+.
- **Internationalization:** All user-facing strings must be wrapped in `_()` using the `gettext` framework. The app must remain multilingual (PL/EN) during development.
- **YAML-First:** Use **YAML** instead of JSON for all human-facing configuration files, metadata drafts, and Field Protocols to ensure high readability and error-forgiveness.
- **Paths:** ALWAYS use `pathlib.Path`.
- **Encoding:** Explicitly use `encoding="utf-8"` for all file operations.

### 2. Frictionless AI & Authentication
- **No API Keys:** Implement OAuth2 flows.
- **Graceful Degradation:** If AI is unavailable, remain functional using heuristic extractors.

### 3. Interactive UI & Dashboard
- Use `NiceGUI` for all workflows. 
- Ensure background tasks report progress to the dashboard UI.
- Use clear, non-technical language for status messages.

### 4. Naming & Structure
- Follow `snake_case` for variables/functions and `PascalCase` for classes.
- `src/opendata/models.py` is the "Source of Truth".

## Metadata Standards (RODBOK)
- Strictly follow the RODBOK schema.
- Mandatory: `title`, `authors`, `abstract`, `license`, `keywords`.

## Agent Specific Instructions
- **Proactiveness:** Implement new extractors in `src/opendata/extractors/`.
- **Testing:** Include a "minimal viable project" fixture in `tests/fixtures/`.
- **Transparency:** Every background step should have a corresponding UI status update.

---
*This file is intended for AI agents. Please update it as the project evolves.*
