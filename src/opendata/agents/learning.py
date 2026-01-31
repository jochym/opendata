from typing import List
from pathlib import Path
from opendata.models import UserSettings


class ProtocolLearner:
    """Agentic logic to extract and store field-specific knowledge."""

    def __init__(self, protocols_dir: Path):
        self.protocols_dir = protocols_dir

    def extract_and_save_rule(self, field: str, user_rule: str):
        """Crystallizes a user correction into a permanent instruction file.

        Example:
        field='Physics', user_rule='In our lab, .dat is always vacuum pressure.'
        Result: Writes to protocols/physics.md
        """
        protocol_file = self.protocols_dir / f"{field.lower().replace(' ', '_')}.md"

        content = f"\n# Learned Rule\n- {user_rule}\n"

        with open(protocol_file, "a", encoding="utf-8") as f:
            f.write(content)

    def load_protocols(self, field: str) -> str:
        """Reads the custom instructions for the specific field."""
        protocol_file = self.protocols_dir / f"{field.lower().replace(' ', '_')}.md"
        if protocol_file.exists():
            return protocol_file.read_text(encoding="utf-8")
        return ""
