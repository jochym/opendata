# Agent Guidelines for OpenData Tool

This repository contains the OpenData Tool, designed for preparing metadata and packaging scientific projects for the RODBUK repository. This document provides essential information for AI agents to maintain consistency and quality while ensuring a **friction-free, browser-centric, multi-platform user experience** for researchers.

## Core Principles
6: 1. **Browser-Centric UI with Desktop Anchor:** The primary user interaction happens in the browser (NiceGUI). However, the app must launch a small, simple **Desktop Control Window** (placeholder) as a "Kill Switch".
7: 2. **Dashboard-First Transparency:** The Desktop Control Window should include "idiot lights" (red/green) and a button to "Open Dashboard".
8: 3. **Mobile-Ready (Optional/Secure):** The UI includes an "Open on Mobile" feature. **Security Note:** By default, the server must only bind to `localhost` (127.0.0.1). Remote access (0.0.0.0) must be explicitly enabled by the user when they request mobile access.
9: 4. **No-Terminal Experience:** When launched as an executable, **no terminal/console must be shown**.
10: 5. **Strictly Read-Only Analysis:** The tool must NEVER modify the contents of the user's research directory.
11: 6. **Domain Knowledge Accumulation:** The tool must support "Meta-Learning". As users refine analysis rules (e.g., "In this lab, .dat files are always pressure logs"), the agent should extract these as permanent **Field Protocols** (instructions). These protocols must be stored in the global workspace and transferable between projects.
12: 7. **Comprehensive Testing (MANDATORY):** Every new functionality, structural change, or bug fix MUST be accompanied by a complete suite of unit and/or integration tests. Refer to `docs/TESTING_INFRASTRUCTURE.md` for standards.

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
> **Moved to `docs/ACCOMPLISHMENTS.md`** - Please refer to that file for the full historical log of development phases.

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
