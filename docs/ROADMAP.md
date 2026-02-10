# Project Roadmap

**Project:** OpenData Tool
**Current Version:** v0.12.0 (Beta / PoC)

---

## 🏗️ Completed Milestones

### Phase 1: Proof of Concept (v0.1 - v0.5) ✅
- [x] Basic NiceGUI Dashboard.
- [x] Google Gemini Integration (OAuth2).
- [x] LaTeX & Docx Heuristic Extraction.
- [x] Basic Chat Interface.
- [x] RODBUK Metadata Schema Implementation.

### Phase 2: User Experience & Grounding (v0.6 - v0.9) ✅
- [x] Google Search Grounding (Fact-checking).
- [x] External Tool Integration (arXiv, DOI, ORCID).
- [x] "Field Protocol" Meta-Learning System.
- [x] Persistent Project Workspace (`~/.opendata_tool`).
- [x] Multi-platform support (Win/Mac/Linux).

### Phase 3: Scalability & Performance (v0.10 - v0.12) ✅
- [x] **SQLite Inventory:** Handling projects with >100k files.
- [x] **High-Performance File Explorer:** Virtualized list view replacing the tree.
- [x] **Transparent Status:** Real-time feedback on AI operations and rate limits.
- [x] **Stop Button:** Graceful interruption of long-running tasks.
- [x] **Raw Error Handling:** Better debugging for malformed AI responses.

---

## 🚀 Active Development (v0.13 - v0.15)

### Priority 1: Advanced Scientific Extraction
- [ ] **Data-Level Extraction:** Parse headers from `.nc` (NetCDF) and `.fits` (Astronomy) files.
- [ ] **Plot Digitization:** (Experimental) Use Vision capabilities to read axes and legends from PNG/PDF plots.
- [ ] **Code Analysis:** Extract "Software Used" by scanning `requirements.txt`, `environment.yml`, or `import` statements in Python scripts.

### Priority 2: Direct Repository Integration
- [ ] **InvenioRDM API:** Implement OAuth2 flow for the RODBUK repository itself.
- [ ] **Draft Creation:** Allow creating a "Draft Dataset" directly in RODBUK from the UI.
- [ ] **File Upload:** (Long-term) Support resumable upload of large datasets via S3/API.

---

## 🔮 Future Horizons (v1.0+)

### 1. Offline / Local AI
- **Goal:** Remove the dependency on Google Cloud.
- **Tech:** Integrate `Ollama` or `Llama.cpp` to run open-weights models (Llama 3, Mistral) locally on the user's GPU.
- **Benefit:** Total privacy for sensitive/medical data that cannot leave the premises.

### 2. Semantic Search
- **Goal:** "Find the file where I calculated the specific heat."
- **Tech:** Local RAG (Retrieval-Augmented Generation) using lightweight embeddings (e.g., `all-MiniLM-L6-v2`) stored in the SQLite inventory.

### 3. Plugin Architecture
- **Goal:** Allow labs to write their own extractors.
- **Tech:** A simple Python plugin hook system (`@extractor` decorator) so users can drop in a script to parse their custom binary formats.
