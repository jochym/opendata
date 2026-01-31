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

        # Merge heuristics into current_metadata
        self.current_metadata = Metadata.model_validate(
            {**self.current_metadata.model_dump(), **heuristics_data}
        )

        # Prepare the first 'Agent Thought'
        msg = f"I've scanned {self.current_fingerprint.file_count} files in your project. "

        found_fields = list(heuristics_data.keys())
        if found_fields:
            msg += f"I automatically found some data for: {', '.join(found_fields)}. "
        else:
            msg += "I couldn't find obvious metadata files like LaTeX or BibTeX. "

        exts = list(set(self.current_fingerprint.extensions))

        # Specialized Physics Reasoning in Chat Loop
        physics_tools = []
        if any(
            ext in [".incar", ".outcar", ".poscar"]
            or p.name.upper() in ["INCAR", "OUTCAR", "POSCAR"]
            for p in project_dir.rglob("*")
        ):
            physics_tools.append("VASP")
        if any("phonopy" in p.name.lower() for p in project_dir.rglob("*")):
            physics_tools.append("Phonopy")
        if any("alamode" in p.name.lower() for p in project_dir.rglob("*")):
            physics_tools.append("ALAMODE")

        if physics_tools:
            msg += f"I noticed you are using {', '.join(physics_tools)}. "
            msg += "This looks like a computational physics project. "
        else:
            msg += f"I noticed clusters of {', '.join(exts[:3])} files. "

        msg += "Should I use AI to analyze the paper titles and suggest more specific metadata?"

        self.chat_history.append(("agent", msg))
        return msg

    def process_user_input(self, user_text: str, ai_service: Any) -> str:
        """Main iterative loop: process user input, call AI, update metadata."""
        self.chat_history.append(("user", user_text))

        # 1. Construct dynamic prompt with history
        context = self.generate_ai_prompt()
        history_str = "\n".join([f"{role}: {m}" for role, m in self.chat_history[-5:]])

        full_prompt = f"""
        {context}
        
        RECENT CONVERSATION:
        {history_str}
        
        INSTRUCTION: 
        Respond to the user's latest message. 
        If they provided new information, update your mental model.
        If they confirmed an AI guess, incorporate it.
        ASK ONE FOLLOW-UP QUESTION to complete the RODBUK requirements.
        """

        # 2. Call AI
        ai_response = ai_service.ask_agent(full_prompt)

        # 3. Handle Knowledge Capture (Meta-Learning)
        # In a real scenario, we'd look for patterns like "In my lab..."
        # For now, we just log the response.

        self.chat_history.append(("agent", ai_response))
        return ai_response
