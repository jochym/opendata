from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import List, Optional, Literal, Any, Dict
from pathlib import Path
from enum import Enum


class ProtocolLevel(str, Enum):
    SYSTEM = "system"
    GLOBAL = "global"
    FIELD = "field"
    PROJECT = "project"


class ExtractionProtocol(BaseModel):
    id: str
    name: str
    level: ProtocolLevel
    is_read_only: bool = False
    include_patterns: List[str] = Field(default_factory=list)
    exclude_patterns: List[str] = Field(default_factory=list)
    extraction_prompts: List[str] = Field(default_factory=list)


class PackageManifest(BaseModel):
    """Stores manual file selections for the package."""

    project_id: str
    # Files explicitly selected by user (overrides exclusions)
    force_include: List[str] = Field(default_factory=list)
    # Files explicitly excluded by user (overrides inclusions)
    force_exclude: List[str] = Field(default_factory=list)
    # Snapshot of the file tree structure for UI
    cached_tree: Optional[Dict[str, Any]] = None


class UserSettings(BaseModel):
    language: Literal["en", "pl"] = "en"
    ai_consent_granted: bool = False
    splitter_value: float = 70.0  # Percentage for the chat/metadata split

    # AI Configuration
    ai_provider: Literal["google", "openai"] = "google"
    google_model: str = "gemini-3-flash-preview"  # Default Google model
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-3.5-turbo"

    workspace_path: str = Field(
        default=str(Path.home() / ".opendata_tool"),
        description="Global workspace for metadata and packages",
    )
    field_protocols_path: str = Field(
        default=str(Path.home() / ".opendata_tool" / "protocols"),
        description="User's custom extraction rules",
    )


class PersonOrOrg(BaseModel):
    name: str = Field(..., description="Surname, first name or organization name")
    affiliation: Optional[str] = Field(None, description="Affiliation in English")
    identifier_scheme: Optional[str] = Field(None, description="ORCID, ISNI, etc.")
    identifier: Optional[str] = Field(None, description="ID without https:// prefix")


class Contact(BaseModel):
    person_to_contact: str = Field(..., description="Full name")
    affiliation: Optional[str] = Field(None)
    email: EmailStr = Field(...)


class RelatedResource(BaseModel):
    relation_type: str = Field(..., description="e.g., 'cited by', 'supplement to'")
    authors: Optional[str] = Field(None, description="APA style list")
    title: str = Field(...)
    id_type: Optional[str] = Field(None, description="DOI, Handle, etc.")
    id_number: Optional[str] = Field(None, description="Full URL identifier")


class Metadata(BaseModel):
    # Field protection
    locked_fields: List[str] = Field(
        default_factory=list, description="Fields protected from AI updates"
    )

    # RODBUK Mandatory Fields (Made optional for intermediate drafting)
    title: Optional[str] = Field(None, description="Full dataset title")
    authors: List[PersonOrOrg] = Field(default_factory=list)
    contacts: List[Contact] = Field(default_factory=list)
    description: List[str] = Field(
        default_factory=list, description="Dataset summaries"
    )
    keywords: List[str] = Field(default_factory=list)
    science_branches_mnisw: List[str] = Field(default_factory=list)
    science_branches_oecd: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default=["English"])
    kind_of_data: Optional[str] = Field(
        None,
        description="e.g., 'Experimental', 'Simulation'",
        validation_alias="kindof_data",
    )
    license: Optional[str] = Field(
        "CC-BY-4.0", description="Data license (e.g., CC-BY-4.0, MIT)"
    )
    software: List[str] = Field(
        default_factory=list,
        description="Software and versions used (e.g., VASP 6.4.1)",
    )

    # Persistence of session settings
    ai_model: Optional[str] = Field(
        None, description="Selected AI model for this project"
    )

    # Optional Fields
    alternative_titles: List[str] = Field(default_factory=list)
    abstract: Optional[str] = Field(None)
    related_publications: List[RelatedResource] = Field(default_factory=list)
    related_datasets: List[RelatedResource] = Field(default_factory=list)
    funding: List[dict] = Field(default_factory=list)
    notes: Optional[str] = Field(None)

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
    def ensure_list_fields(cls, v: Any) -> List[str]:
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
    extensions: List[str]
    structure_sample: List[str] = Field(description="First 50 file paths found")


class Question(BaseModel):
    field: str
    label: str
    question: str
    type: Literal["text", "choice"]
    options: Optional[List[str]] = None
    value: Optional[Any] = None


class FileSuggestion(BaseModel):
    """A suggestion from AI to include a file in the package."""

    path: str
    reason: str


class AIAnalysis(BaseModel):
    summary: str
    missing_fields: List[str] = Field(
        default_factory=list, validation_alias="missingfields", alias="missing_fields"
    )
    non_compliant: List[str] = Field(
        default_factory=list, validation_alias="noncompliant", alias="non_compliant"
    )
    conflicting_data: List[Dict[str, Any]] = Field(
        default_factory=list,
        validation_alias="conflictingdata",
        alias="conflicting_data",
    )
    questions: List[Question] = Field(default_factory=list)
    file_suggestions: List[FileSuggestion] = Field(
        default_factory=list,
        validation_alias="filesuggestions",
        alias="file_suggestions",
    )
