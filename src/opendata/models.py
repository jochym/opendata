from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from pathlib import Path


class UserSettings(BaseModel):
    language: Literal["en", "pl"] = "en"
    ai_consent_granted: bool = False

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
        None, description="e.g., 'Experimental', 'Simulation'"
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


class ProjectFingerprint(BaseModel):
    """A light representation of the project directory."""

    root_path: str
    file_count: int
    total_size_bytes: int
    extensions: List[str]
    structure_sample: List[str] = Field(description="First 50 file paths found")
