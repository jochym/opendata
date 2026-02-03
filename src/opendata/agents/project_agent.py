from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import yaml
import re
from opendata.models import Metadata, ProjectFingerprint
from opendata.extractors.base import ExtractorRegistry, PartialMetadata
from opendata.utils import scan_project_lazy


class ProjectAnalysisAgent:
    """
    Agent specialized in analyzing research directories and proposing metadata.
    Maintains the state of the 'Chat Loop' and uses external tools (arXiv, DOI, ORCID).
    """

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.registry = ExtractorRegistry()
        self._setup_extractors()
        self.current_fingerprint: Optional[ProjectFingerprint] = None
        self.current_metadata = Metadata.model_construct()
        self.chat_history: List[Tuple[str, str]] = []  # (Role, Message)

    def _setup_extractors(self):
        from opendata.extractors.latex import LatexExtractor
        from opendata.extractors.docx import DocxExtractor
        from opendata.extractors.medical import DicomExtractor
        from opendata.extractors.citations import BibtexExtractor
        from opendata.extractors.hierarchical import Hdf5Extractor
        from opendata.extractors.physics import (
            VaspExtractor,
            LatticeDynamicsExtractor,
            ColumnarDataExtractor,
        )

        self.registry.register(LatexExtractor())
        self.registry.register(DocxExtractor())
        self.registry.register(DicomExtractor())
        self.registry.register(BibtexExtractor())
        self.registry.register(Hdf5Extractor())
        self.registry.register(VaspExtractor())
        self.registry.register(LatticeDynamicsExtractor())
        self.registry.register(ColumnarDataExtractor())

    def start_analysis(self, project_dir: Path) -> str:
        """Initial scan and heuristic extraction phase."""
        self.current_fingerprint = scan_project_lazy(project_dir)

        # Run Heuristics
        heuristics_data = {}
        for p in project_dir.rglob("*"):
            if p.is_file():
                for extractor in self.registry.get_extractors_for(p):
                    partial = extractor.extract(p)
                    for key, val in partial.model_dump(exclude_unset=True).items():
                        if val:
                            heuristics_data[key] = val

        self.current_metadata = Metadata.model_construct(**heuristics_data)

        msg = f"I've scanned {self.current_fingerprint.file_count} files in your project. "
        found_fields = list(heuristics_data.keys())
        if found_fields:
            msg += f"I automatically found some data for: {', '.join(found_fields)}. "
        else:
            msg += "I couldn't find obvious metadata files like LaTeX or BibTeX. "

        # Specialized Physics Reasoning
        physics_tools = []
        for p in project_dir.rglob("*"):
            if p.is_file():
                name_upper = p.name.upper()
                if (
                    name_upper in ["INCAR", "OUTCAR", "POSCAR"]
                    and "VASP" not in physics_tools
                ):
                    physics_tools.append("VASP")
                if "phonopy" in p.name.lower() and "Phonopy" not in physics_tools:
                    physics_tools.append("Phonopy")
                if "alamode" in p.name.lower() and "ALAMODE" not in physics_tools:
                    physics_tools.append("ALAMODE")

        if physics_tools:
            msg += f"I noticed you are using {', '.join(physics_tools)}. "
            msg += "This looks like a computational physics project. "

        msg += "Should I use AI to analyze the paper titles or would you like to provide an arXiv/DOI link?"

        self.chat_history.append(("agent", msg))
        return msg

    def process_user_input(self, user_text: str, ai_service: Any) -> str:
        """Main iterative loop with Context Persistence and Tool recognition."""
        self.chat_history.append(("user", user_text))

        # 1. TOOL RECOGNITION (arXiv/DOI/ORCID)
        arxiv_match = re.search(r"arxiv[:\s]*([\d\.]+)", user_text, re.IGNORECASE)
        doi_match = re.search(r"doi[:\s]*(10\.\d{4,}/[^\s]+)", user_text, re.IGNORECASE)
        orcid_match = re.search(
            r"orcid[:\s]*(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", user_text, re.IGNORECASE
        )
        orcid_search_match = re.search(
            r"orcid (?:for|of) ([^,\?\.]+)", user_text, re.IGNORECASE
        )

        enhanced_input = user_text
        if arxiv_match:
            arxiv_id = arxiv_match.group(1)
            raw_data = ai_service.fetch_arxiv_metadata(arxiv_id)
            enhanced_input = f"The user provided arXiv ID {arxiv_id}. Here is raw metadata: {raw_data}. USE THIS TO UPDATE METADATA."
        elif doi_match:
            doi_id = doi_match.group(1)
            json_data = ai_service.fetch_doi_metadata(doi_id)
            enhanced_input = f"The user provided DOI {doi_id}. Here is the metadata: {json_data}. USE THIS TO UPDATE METADATA."
        elif orcid_match:
            orcid_id = orcid_match.group(1)
            json_data = ai_service.fetch_orcid_metadata(orcid_id)
            enhanced_input = f"The user provided ORCID {orcid_id}. Here is the profile: {json_data}. UPDATE AUTHOR INFO."
        elif orcid_search_match:
            author_name = orcid_search_match.group(1).strip()
            results = ai_service.search_orcid_by_name(author_name)
            enhanced_input = f"User wants ORCID search for '{author_name}'. Top matches: {results}. ASK USER TO CONFIRM ONE."

        # 2. CONTEXT PERSISTENCE
        # We always reconstruct the full context + history to handle model switches gracefully
        context = self.generate_ai_prompt()
        # We include the last 10 messages for deep context
        history_str = "\n".join(
            [f"{role}: {m}" for role, m in self.chat_history[-10:-1]]
        )

        full_prompt = f"""
        {context}
        
        RECENT CONVERSATION HISTORY:
        {history_str}
        
        LATEST USER INPUT:
        {enhanced_input}
        
        INSTRUCTION: 
        Respond to the user. Maintain the existing metadata draft in your reasoning.
        ASK ONE CLEAR FOLLOW-UP QUESTION.
        """

        ai_response = ai_service.ask_agent(full_prompt)
        self.chat_history.append(("agent", ai_response))
        return ai_response

    def generate_ai_prompt(self) -> str:
        if not self.current_fingerprint:
            return "No project scanned."
        fingerprint_summary = self.current_fingerprint.model_dump_json(indent=2)
        prompt = f"""
        You are a scientific data steward assistant for the RODBUK repository.
        
        PROJECT FINGERPRINT:
        {fingerprint_summary}
        
        CURRENT METADATA DRAFT (YAML):
        {yaml.dump(self.current_metadata.model_dump(exclude_unset=True))}
        
        INSTRUCTIONS:
        1. Propose research metadata based on files and structure.
        2. Identify what is missing for a valid RODBUK package.
        3. Ask ONE clear, non-technical question.
        
        Response format: A brief summary of your 'thoughts' followed by the question.
        """
        return prompt
