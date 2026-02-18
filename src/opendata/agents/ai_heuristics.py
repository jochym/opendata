import json
import logging
import re
from pathlib import Path
from typing import List, Any, Tuple, Dict, Optional

from opendata.storage.project_db import ProjectInventoryDB
from opendata.workspace import WorkspaceManager
from opendata.utils import format_size
from opendata.models import ProjectFingerprint, AIAnalysis, FileSuggestion

logger = logging.getLogger("opendata.agents.ai_heuristics")


class AIHeuristicsService:
    def __init__(self, wm: WorkspaceManager):
        self.wm = wm

    def identify_significant_files(
        self, project_id: str, ai_service: Any
    ) -> Tuple[List[str], Optional[AIAnalysis]]:
        """
        Uses AI to identify significant files from the inventory.
        Returns a list of file paths and an AIAnalysis object.
        """
        db_path = self.wm.get_project_db_path(project_id)
        try:
            db = ProjectInventoryDB(db_path)
            inventory = db.get_inventory()
        except Exception as e:
            logger.error(f"Failed to load inventory: {e}")
            return [], None

        if not inventory:
            return [], None

        # Prepare dense file list (limit to 3000 files for Gemini's large context)
        # We sort by depth then name to give a clear tree-like structure
        sorted_files = sorted(
            inventory, key=lambda x: (x["path"].count("/"), x["path"])
        )
        file_lines = []
        for item in sorted_files[:3000]:
            file_lines.append(f"{item['path']} ({format_size(item['size'])})")

        file_list_str = "\n".join(file_lines)
        truncated = len(sorted_files) > 3000

        prompt = f"""
You are an expert scientific data curator.
Your task is to analyze the project's file inventory and identify files that are CRITICAL for metadata extraction and results reproduction.

FILE INVENTORY ({"truncated to 3000 files" if truncated else "complete"}):
{file_list_str}

GOAL:
1. Identify the "Primary Publication" (the main paper, usually .tex or .docx).
2. Identify auxiliary metadata sources (README, config.yaml, metadata.json).
3. Identify domain-specific data logs or headers (e.g., .log, OUTCAR, .fits, .hdf5).

RESPONSE FORMAT (Strict JSON):
Return a JSON object with two keys:
- "ANALYSIS": A summary of your reasoning and what you found.
- "SELECTION": A list of objects {{"path": "relative/path", "reason": "why this file is important"}}.

Example:
{{
  "ANALYSIS": "Found a LaTeX paper and a README. Identified VASP output files.",
  "SELECTION": [
    {{"path": "paper/main.tex", "reason": "Primary publication source"}},
    {{"path": "README.md", "reason": "Project overview and documentation"}}
  ]
}}

Return ONLY the JSON block.
"""

        try:
            response = ai_service.ask_agent(prompt)
            print(f"\nDEBUG: AI Heuristics Raw Response:\n{response}\n")

            # Find JSON block (more robust regex)
            # Look for the first opening brace and the last closing brace
            start = response.find("{")
            end = response.rfind("}")

            if start != -1 and end != -1:
                json_str = response[start : end + 1]
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(
                        f"AI Heuristics: JSON decode error: {e}. String: {json_str}"
                    )
                    return [], None

                selection = data.get("SELECTION", [])
                analysis_text = data.get("ANALYSIS", "AI identified significant files.")

                # Validate and extract paths
                existing_paths = {item["path"] for item in inventory}
                valid_selection = [
                    s
                    for s in selection
                    if isinstance(s, dict) and s.get("path") in existing_paths
                ]
                paths = [s["path"] for s in valid_selection]

                # Create AIAnalysis object for consistency
                suggestions = [
                    FileSuggestion(
                        path=s["path"],
                        reason=s.get("reason", "Identified as significant"),
                    )
                    for s in valid_selection
                ]

                analysis = AIAnalysis(
                    summary=analysis_text, file_suggestions=suggestions
                )

                return paths, analysis
            else:
                logger.warning(
                    f"AI Heuristics: No JSON block found in response: {response}"
                )
                return [], None

        except Exception as e:
            logger.error(f"AI Heuristics failed: {e}")
            return [], None
