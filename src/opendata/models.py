from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import List, Optional, Literal, Any, Dict
from pathlib import Path
from enum import Enum


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
    include_patterns: List[str] = Field(default_factory=list)
    exclude_patterns: List[str] = Field(default_factory=list)
    extraction_prompts: List[str] = Field(default_factory=list)
    metadata_prompts: List[str] = Field(default_factory=list)
    curator_prompts: List[str] = Field(default_factory=list)

    @field_validator("level", mode="before")
    @classmethod
    def migrate_level(cls, v: Any) -> Any:
        if v == "global":
            return "user"
        return v


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
    relation_type: str = Field(
        "IsSupplementTo", description="e.g., 'cited by', 'supplement to'"
    )
    authors: Optional[str] = Field(None, description="APA style list")
    title: str = Field(...)
    id_type: Optional[str] = Field(None, description="DOI, Handle, etc.")
    id_number: Optional[str] = Field(None, description="Full URL identifier")

    @model_validator(mode="before")
    @classmethod
    def from_string(cls, v: Any) -> Any:
        if isinstance(v, str):
            return {"title": v, "relation_type": "IsSupplementTo"}
        return v


class SoftwareInfo(BaseModel):
    name: str = Field(..., description="Software name")
    version: Optional[str] = Field(None, description="Software version")

    def __str__(self) -> str:
        if self.version:
            return f"{self.name} {self.version}"
        return self.name


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
    software: List[SoftwareInfo] = Field(
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
        "related_publications",
        "related_datasets",
        mode="before",
    )
    @classmethod
    def ensure_list_fields(cls, v: Any) -> List[Any]:
        if v is None:
            return []
        if isinstance(v, str):
            if "," in v and "[" not in v:
                items = [i.strip() for i in v.split(",")]
            else:
                items = [v]

            # For related_publications/datasets, convert string to title object
            # We check the field name context if possible, but here we just check if
            # we are dealing with a field that expects RelatedResource objects.
            # Actually, Pydantic will try to validate the list items later.
            return items
        return v

    @field_validator("software", mode="before")
    @classmethod
    def ensure_software_list(cls, v: Any) -> List[SoftwareInfo]:
        if v is None:
            return []
        if isinstance(v, str):
            if "," in v and "[" not in v:
                items = [i.strip() for i in v.split(",")]
            else:
                items = [v]
            return [SoftwareInfo(name=i) for i in items]
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, str):
                    res.append(SoftwareInfo(name=item))
                elif isinstance(item, dict):
                    res.append(SoftwareInfo(**item))
                else:
                    res.append(item)
            return res
        return v


class ProjectFingerprint(BaseModel):
    """A light representation of the project directory."""

    root_path: str
    file_count: int
    total_size_bytes: int
    extensions: List[str]
    structure_sample: List[str] = Field(description="First 50 file paths found")
    primary_file: Optional[str] = Field(
        None, description="Path to the main research paper (TeX/Docx)"
    )
    significant_files: List[str] = Field(
        default_factory=list,
        description="Files identified by AI or heuristics for deep analysis",
    )


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

    @field_validator("non_compliant", "missing_fields", mode="before")
    @classmethod
    def ensure_string_list(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, dict):
                    # Convert dict to string representation
                    field = item.get("field", "unknown")
                    reason = item.get("reason", "")
                    res.append(f"{field}: {reason}" if reason else field)
                else:
                    res.append(str(item))
            return res
        return v

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
