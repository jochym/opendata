# Audit of Test System - OpenData Tool
**Date:** 2026-02-21
**Auditor:** OpenCode Agent

## 1. Executive Summary

The current test suite is stable and functional, with **72 passing tests** and **42 skipped tests** (correctly skipping AI/Local tests in this environment). The core infrastructure uses `pytest` effectively.

However, **code coverage is low (34%)**, with critical gaps in the "intelligence" layer of the application (Extractors, Agent Logic) and the UI layer. While the core data models are well-tested (100%), the logic that actually populates them is under-tested.

### Key Statistics
- **Total Tests:** 114
- **Passing:** 72
- **Skipped:** 42 (AI interaction, local only)
- **Total Coverage:** 34%
- **High Risk Areas:** `src/opendata/extractors` (24-35%), `src/opendata/ui` (4-19%).

## 2. Detailed Test File Audit

### ✅ High Quality Tests (Keep/Expand)
These tests verify *behavior* and business logic, not just implementation details.
- **`tests/unit/models/test_models.py`**: Excellent coverage (100%) of Pydantic models and validation logic.
- **`tests/unit/agents/test_parsing*.py`**: Robust testing of AI response parsing, covering edge cases, normalization, and error recovery. This is critical infrastructure.
- **`tests/unit/agents/test_field_protocol_persistence.py`**: Exemplary testing of business rules (Field Protocol isolation). Explicitly tests *requirements* (e.g., "no heuristics allowed"), not just code paths.
- **`tests/unit/protocols/test_protocol_manager.py`**: Solid testing of the protocol resolution logic.

### ⚠️ Implementation-Coupled Tests (Refactor if possible)
These tests mock heavily and might break if internal implementation details change, even if behavior stays the same.
- **`tests/unit/ui/test_package_stats.py`**: Tests that specific UI methods (`ui.label`) are called. While useful for regression, they are brittle.
- **`tests/unit/ui/test_chat_scan_message.py`**: Similar to above, relies on mocking internal UI state.

### ❌ Missing / Weak Areas
- **Extractors (`src/opendata/extractors/*.py`)**:
    - **Current State:** Almost no direct unit tests. `test_full_text_extraction.py` covers one utility, but specific logic for Physics (VASP, Phonopy), Medical (DICOM), and generic data is untested.
    - **Risk:** High. If a regex for parsing `OUTCAR` is broken, the user gets no metadata, and no test fails.
- **Project Agent (`src/opendata/agents/project_agent.py`)**:
    - **Current State:** 53% coverage. Tests cover basic loading/saving, but complex interaction flows and state management are partially uncovered.
- **UI Logic (`src/opendata/ui/components/*.py`)**:
    - **Current State:** Very low coverage (<20%). Logic is mixed with NiceGUI rendering code, making it hard to test without complex mocking.

## 3. Coverage Analysis Gap Report

| Component | Coverage | Status | Notes |
|-----------|:--------:|:------:|-------|
| **Models** | 100% | ✅ | Excellent foundation. |
| **Protocols** | 85% | ✅ | Good coverage of rules engine. |
| **Parsing** | 68% | ⚠️ | Good, but could be higher given its criticality. |
| **Project Agent** | 53% | ⚠️ | Core orchestrator needs better coverage. |
| **Extractors** | ~25% | ❌ | **CRITICAL GAP.** Heuristics are untested. |
| **UI Components** | ~15% | ❌ | Logic trapped in UI code. |

## 4. Action Plan

### Phase 1: Shore up the Intelligence (Extractors)
The "smart" part of the tool is the least tested. This must be fixed first.
1.  [ ] **Create `tests/unit/extractors/test_physics.py`**: Test `VaspExtractor`, `LatticeDynamicsExtractor` with sample file contents (mocked `read_file_header`).
2.  [ ] **Create `tests/unit/extractors/test_medical.py`**: Test `DicomExtractor` (mocking `pydicom`).
3.  [ ] **Create `tests/unit/extractors/test_generic.py`**: Test `ColumnarDataExtractor` with various CSV/DAT formats.

### Phase 2: Strengthen the Agent
1.  [ ] **Expand `tests/unit/agents/test_project_agent.py`**: Add tests for:
    - Heuristic application (when extractors return data).
    - Prompt construction (verifying context injection).
    - State transitions (Scan -> Analyze -> Report).

### Phase 3: UI Logic Extraction (Refactoring)
1.  [ ] **Refactor UI Components**: Move logic out of `render()` functions into pure Python functions or ViewModels that can be tested independently of NiceGUI.
    - *Target:* `src/opendata/ui/components/metadata.py` (Complex form logic).
    - *Target:* `src/opendata/ui/components/inventory_logic.py` (Filtering/Sorting logic).

## 5. Recommended Test Plan (Copy to Todo)

```todo
- [ ] Create unit tests for Physics Extractor (VASP, Phonopy) @high
- [ ] Create unit tests for Medical Extractor (DICOM) @high
- [ ] Create unit tests for Generic Extractor (CSV/Data) @medium
- [ ] Improve coverage for ProjectAnalysisAgent logic @medium
- [ ] Refactor Metadata UI logic for testability @low
```
