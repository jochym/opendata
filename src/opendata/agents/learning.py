from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class FieldProtocol(BaseModel):
    """
    A persistent instruction set for a specific scientific domain.
    Learned from user interactions.
    """

    field_name: str
    heuristics: list[str] = Field(
        default_factory=list, description="Regex or pattern rules"
    )
    ai_prompts: list[str] = Field(
        default_factory=list, description="Specific prompt snippets learned from user"
    )


class ProtocolStore:
    """Manages the lifecycle of Field Protocols in YAML format."""

    def __init__(self, protocols_dir: Path):
        self.protocols_dir = protocols_dir

    def save_protocol(self, protocol: FieldProtocol):
        """Saves a domain protocol to a YAML file."""
        safe_name = protocol.field_name.lower().replace(" ", "_")
        target_path = self.protocols_dir / f"{safe_name}.yaml"

        with open(target_path, "w", encoding="utf-8") as f:
            yaml.dump(protocol.model_dump(), f, allow_unicode=True, sort_keys=False)

    def get_protocol(self, field_name: str) -> FieldProtocol | None:
        """Retrieves a protocol by field name."""
        safe_name = field_name.lower().replace(" ", "_")
        target_path = self.protocols_dir / f"{safe_name}.yaml"

        if not target_path.exists():
            return None

        with open(target_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return FieldProtocol.model_validate(data)
