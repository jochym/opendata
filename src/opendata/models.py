from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class ProtocolLevel(str, Enum):
    SYSTEM = "system"
    USER = "user"
    FIELD = "field"
    PROJECT = "project"


class ExtractionProtocol(BaseModel):
    id: str
    name: str
    level: ProtocolLevel
    is_read_only: bool = False
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    extraction_prompts: list[str] = Field(default_factory=list)
    metadata_prompts: list[str] = Field(default_factory=list)
    curator_prompts: list[str] = Field(default_factory=list)


class PackageManifest(BaseModel):
    """Stores manual file selections for the package."""

    project_id: str
    # Files explicitly selected by user (overrides exclusions)
    force_include: list[str] = Field(default_factory=list)
    # Files explicitly excluded by user (overrides inclusions)
    force_exclude: list[str] = Field(default_factory=list)
    # Snapshot of the file tree structure for UI
    cached_tree: dict[str, Any] | None = None


class UserSettings(BaseModel):
    language: Literal["en", "pl"] = "en"
    ai_consent_granted: bool = False
    splitter_value: float = 70.0  # Percentage for the chat/metadata split

    # AI Configuration
    ai_provider: Literal["google", "openai"] = "google"
    google_model: str = "gemini-3-flash-preview"  # Default Google model
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-3.5-turbo"

    workspace_path: str = Field(
        default_factory=lambda: str(Path.home() / ".opendata_tool"),
        description="Global workspace for metadata and packages",
    )
    field_protocols_path: str = Field(
        default_factory=lambda: str(Path.home() / ".opendata_tool" / "protocols"),
        description="User's custom extraction rules",
    )


class PersonOrOrg(BaseModel):
    name: str = Field(..., description="Surname, first name or organization name")
    affiliation: str | None = Field(None, description="Affiliation in English")
    identifier_scheme: str | None = Field(None, description="ORCID, ISNI, etc.")
    identifier: str | None = Field(None, description="ID without https:// prefix")


class Contact(BaseModel):
    person_to_contact: str = Field(..., description="Full name")
    affiliation: str | None = Field(None)
    email: EmailStr = Field(...)


class RelatedResource(BaseModel):
    relation_type: str = Field(..., description="e.g., 'cited by', 'supplement to'")
    authors: str | None = Field(None, description="APA style list")
    title: str = Field(...)
    id_type: str | None = Field(None, description="DOI, Handle, etc.")
    id_number: str | None = Field(None, description="Full URL identifier")


class Metadata(BaseModel):
    model_config = {"populate_by_name": True}

    # Field protection
    locked_fields: list[str] = Field(
        default_factory=list, description="Fields protected from AI updates"
    )

    # RODBUK Mandatory Fields (Made optional for intermediate drafting)
    title: str | None = Field(None, description="Full dataset title")
    authors: list[PersonOrOrg] = Field(default_factory=list)
    contacts: list[Contact] = Field(default_factory=list)
    description: list[str] = Field(
        default_factory=list, description="Dataset summaries"
    )
    keywords: list[str] = Field(default_factory=list)
    science_branches_mnisw: list[str] = Field(default_factory=list)
    science_branches_oecd: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default=["English"])
    kind_of_data: str | None = Field(
        None,
        description="e.g., 'Experimental', 'Simulation'",
        validation_alias="kindof_data",
    )
    license: str | None = Field(
        "CC-BY-4.0", description="Data license (e.g., CC-BY-4.0, MIT)"
    )
    software: list[str] = Field(
        default_factory=list,
        description="Software and versions used (e.g., VASP 6.4.1)",
    )

    # Persistence of session settings
    ai_model: str | None = Field(None, description="Selected AI model for this project")

    # Optional Fields
    alternative_titles: list[str] = Field(default_factory=list)
    abstract: str | None = Field(None)
    related_publications: list[RelatedResource] = Field(default_factory=list)
    related_datasets: list[RelatedResource] = Field(default_factory=list)
    funding: list[dict] = Field(default_factory=list)
    notes: str | None = Field(None)

    @field_validator(
        "description",
        "keywords",
        "science_branches_mnisw",
        "science_branches_oecd",
        "languages",
        "software",
        mode="before",
    )
    @classmethod
    def ensure_list_fields(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            if "," in v and "[" not in v:
                return [i.strip() for i in v.split(",")]
            return [v]
        return v


class ProjectFingerprint(BaseModel):
    """A light representation of the project directory."""

    root_path: str
    file_count: int
    total_size_bytes: int
    extensions: list[str]
    structure_sample: list[str] = Field(description="First 50 file paths found")
    primary_file: str | None = Field(
        None, description="Path to the main research paper (TeX/Docx)"
    )
    significant_files: list[str] = Field(
        default_factory=list, description="Files identified by AI as important"
    )


class Question(BaseModel):
    field: str
    label: str
    question: str
    type: Literal["text", "choice"]
    options: list[str] | None = None
    value: Any | None = None


class FileSuggestion(BaseModel):
    """A suggestion from AI to include a file in the package."""

    path: str
    reason: str


class AIAnalysis(BaseModel):
    summary: str
    missing_fields: list[str] = Field(
        default_factory=list, validation_alias="missingfields", alias="missing_fields"
    )
    non_compliant: list[str] = Field(
        default_factory=list, validation_alias="noncompliant", alias="non_compliant"
    )
    conflicting_data: list[dict[str, Any]] = Field(
        default_factory=list,
        validation_alias="conflictingdata",
        alias="conflicting_data",
    )
    questions: list[Question] = Field(default_factory=list)
    file_suggestions: list[FileSuggestion] = Field(
        default_factory=list,
        validation_alias="filesuggestions",
        alias="file_suggestions",
    )
