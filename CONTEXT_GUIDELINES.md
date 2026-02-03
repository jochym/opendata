# Context Consistency & State Management Guidelines

To ensure a high-quality user experience and accurate metadata extraction, the OpenData Tool follows these strictly enforced guidelines for AI agent interaction.

## 1. The "Source of Truth" (Anchor)
- The **`current_metadata`** draft is the only reliable state. 
- **Rule:** Every AI request MUST include the current metadata in YAML format.
- **Rule:** AI models must be instructed to never ask for information already present in the YAML draft.
- **Rule:** Any information confirmed by the user must be extracted and saved to the `Metadata` model immediately.

## 2. Stateless Model Handling
- Models can be switched at any time (e.g., from Flash to Pro).
- **Architecture:** The `ProjectAnalysisAgent` is responsible for state. The AI Service is purely a stateless execution layer.
- **Prompt Construction:**
    1. **System Prompt:** Role, RODBUK constraints, and response format.
    2. **Field Protocols:** Domain-specific instructions learned from previous sessions.
    3. **Metadata State:** The current YAML draft.
    4. **History:** A limited window (max 5-10 messages) of recent chat.
    5. **User Input:** The latest query, potentially enhanced with tool results (arXiv/DOI).

## 3. Text-Centric Metadata Extraction
- **The Core Source:** Scientific metadata (Title, Authors, Abstract) is best found in the main article text (LaTeX, PDF, Docx).
- **Optimization:** Skip the raw content of large data files (CSV, HDF5 headers) in the chat context unless specifically asked. Instead, provide a summary (e.g., "150 pressure logs found").
- **Full-Text Injection:** When the "main text" is identified, its content should be prioritized in the context for initial extraction.

## 4. The First-Turn Strategy
The first response after a project scan must follow this pattern:
1. **Summary:** Briefly state what was found (number of files, detected technologies like VASP).
2. **Identification:** Guess the "main" research paper or manuscript.
3. **The Confirmation Question:** "I've gathered these initial details. Is it okay to use `[main_file_name]` as the primary source for a first approximation of the metadata?"

## 5. Metadata Drift Prevention
- If the AI asks a question that was already answered, it is a sign of "Context Drift".
- **Prevention:** Update the YAML state after *every* message. Ensure the model's "Thoughts" section evaluates the YAML draft against the user's latest input before generating a "Question".
