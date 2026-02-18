import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("opendata.ai.telemetry")


class AITelemetry:
    """
    Handles structured logging of AI interactions with blob sanitization.
    """

    def __init__(self, log_path: Path, sanitize_blobs: bool = True):
        self.log_path = log_path
        self.sanitize_blobs = sanitize_blobs

        # Clear log file on session start (initialization)
        try:
            if self.log_path.exists():
                self.log_path.unlink()
        except Exception as e:
            logger.warning(f"Could not clear AI telemetry log: {e}")

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Could not create telemetry log directory: {e}")

    def generate_id(self) -> str:
        """Generates a unique ID for an interaction."""
        return str(uuid.uuid4())

    def sanitize_prompt(self, prompt: str) -> str:
        """
        Removes large file content blobs from the prompt for cleaner logs.
        Looks for '--- FILE CONTENT: ... ---' patterns.
        """
        if not self.sanitize_blobs:
            return prompt

        # Pattern to match file content blocks
        # Matches: --- FILE CONTENT: filename --- [content] ---
        # We use a non-greedy match for the content to avoid eating the whole prompt
        pattern = r"(--- FILE CONTENT: .*? ---\n)(.*?)(\n---)"

        def replace_blob(match):
            header = match.group(1)
            content = match.group(2)
            footer = match.group(3)

            if len(content) > 500:
                return f"{header}[... content truncated ({len(content)} chars) ...]{footer}"
            return match.group(0)

        sanitized = re.sub(pattern, replace_blob, prompt, flags=re.DOTALL)

        # Also handle trailing file content if it's the last thing in the prompt
        end_pattern = r"(--- FILE CONTENT: .*? ---\n)(.*?)$"

        def replace_end_blob(match):
            header = match.group(1)
            content = match.group(2)
            if len(content) > 500:
                return f"{header}[... content truncated ({len(content)} chars) ...]"
            return match.group(0)

        sanitized = re.sub(end_pattern, replace_end_blob, sanitized, flags=re.DOTALL)

        return sanitized

    def log_interaction(
        self,
        interaction_id: str,
        model_name: str,
        prompt: str,
        response: str,
        latency_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Logs a single AI interaction to a structured JSONL file."""
        log_entry = {
            "id": interaction_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model_name,
            "prompt": self.sanitize_prompt(prompt),
            "response": response,
            "latency_ms": latency_ms,
            "metadata": metadata or {},
        }

        try:
            # Ensure parent directory exists before each write (defensive)
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            # Force log to stdout for E2E testing visibility
            print(f"TELEMETRY_LOG: {json.dumps(log_entry, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f"Failed to write AI telemetry to {self.log_path}: {e}")

    @staticmethod
    def get_id_tag(interaction_id: str) -> str:
        """Returns a hidden HTML comment tag containing the ID."""
        return f"\n<!-- OPENDATA_AI_ID: {interaction_id} -->"

    @staticmethod
    def extract_id(text: str) -> Optional[str]:
        """Extracts the interaction ID from a text response."""
        match = re.search(r"<!-- OPENDATA_AI_ID: (.*?) -->", text)
        return match.group(1) if match else None

    @staticmethod
    def strip_id_tag(text: str) -> str:
        """Removes the ID tag from the text."""
        return re.sub(r"\n?<!-- OPENDATA_AI_ID: .*? -->", "", text).strip()
