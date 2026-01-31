from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import yaml
from opendata.models import Metadata, ProjectFingerprint
from opendata.extractors.base import ExtractorRegistry, PartialMetadata
from opendata.utils import scan_project_lazy


class ProjectAnalysisAgent:
    """
    Agent specialized in analyzing research directories and proposing metadata.
    Maintains the state of the 'Chat Loop'.
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
                    heuristics_data.update(partial.model_dump(exclude_unset=True))

        # Prepare the first 'Agent Thought'
        msg = f"I've scanned {self.current_fingerprint.file_count} files in your project. "

        found_fields = list(heuristics_data.keys())
        if found_fields:
            msg += f"I automatically found data for: {', '.join(found_fields)}. "
        else:
            msg += "I couldn't find obvious metadata files like LaTeX or BibTeX. "

        exts = list(set(self.current_fingerprint.extensions[:3]))
        msg += f"I noticed clusters of {', '.join(exts)} files. "
        msg += (
            "Should I use AI to analyze the paper titles and guess the research field?"
        )

        self.chat_history.append(("agent", msg))
        return msg

    def generate_ai_prompt(self) -> str:
        """Assembles the state into a prompt for the AI partner."""
        if not self.current_fingerprint:
            return "No project scanned."

        fingerprint_summary = self.current_fingerprint.model_dump_json(indent=2)

        prompt = f"""
        You are a scientific data steward assistant for the RODBUK repository.
        Your goal is to help the user complete their metadata.
        
        PROJECT FINGERPRINT:
        {fingerprint_summary}
        
        CURRENT METADATA DRAFT (YAML):
        {yaml.dump(self.current_metadata.model_dump(exclude_unset=True))}
        
        INSTRUCTIONS:
        1. Analyze the file extensions and structure.
        2. Propose the most likely 'Research Field' (Physics, Medicine, etc.).
        3. Identify what is missing for a valid RODBUK package.
        4. Ask the user ONE clear, non-technical question to fill a gap.
        
        Response format: A brief summary of your 'thoughts' followed by the question.
        """
        return prompt
