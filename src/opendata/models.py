from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal


class PersonOrOrg(BaseModel):
    name: str = Field(..., description="Surname, first name or organization name")
    affiliation: Optional[str] = Field(
        None, description="University main name or institute/department (in English)"
    )
    identifier_scheme: Optional[str] = Field(
        None, description="Name of the identifier scheme (ORCID, ISNI)"
    )
    identifier: Optional[str] = Field(None, description="Identifier (without https://)")


class Author(PersonOrOrg):
    pass


class Contributor(PersonOrOrg):
    pass


class Contact(BaseModel):
    person_to_contact: str = Field(
        ..., description="Surname, first name or organization name"
    )
    affiliation: Optional[str] = Field(
        None, description="University main name or institute/department"
    )
    email: EmailStr = Field(
        ..., description="E-mail address for contact (not displayed)"
    )


class RelatedResource(BaseModel):
    relation_type: str = Field(..., description="Type of relation (predefined list)")
    authors: Optional[str] = Field(None, description="Authors in APA style")
    title: str = Field(..., description="Title of the related resource")
    id_type: Optional[str] = Field(
        None, description="Type of digital identifier (e.g. DOI)"
    )
    id_number: Optional[str] = Field(
        None, description="Identifier URL (starting with https://)"
    )
    url: Optional[str] = Field(
        None, description="Web page URL (starting with https://)"
    )


class Producer(BaseModel):
    name: str = Field(..., description="Producer name")
    affiliation: Optional[str] = Field(
        None, description="Organization with which producer is affiliated"
    )
    abbreviation: Optional[str] = Field(None, description="Producer's short name")
    url: Optional[str] = Field(None, description="Producer's website URL")


class Funding(BaseModel):
    grant_agency: str = Field(..., description="Full name of the grant agency")
    grant_name: Optional[str] = Field(
        None, description="Funding program name: project title"
    )
    grant_id: Optional[str] = Field(None, description="Unique grant number")
    grant_agency_ror: Optional[str] = Field(None, description="ROR identifier URL")


class UserSettings(BaseModel):
    language: Literal["en", "pl"] = "en"
    ai_consent_granted: bool = False
    workspace_path: str = Field(
        ..., description="Path where generated metadata and packages are stored"
    )
    field_protocols_path: str = Field(
        ..., description="Path to the user's custom instruction sets"
    )


class Metadata(BaseModel):
    title: str = Field(..., description="Full title of the dataset")
    alternative_titles: List[str] = Field(
        default_factory=list, description="Translations of the title"
    )
    authors: List[Author] = Field(..., min_length=1)
    contributors: List[Contributor] = Field(default_factory=list)
    contacts: List[Contact] = Field(..., min_length=1)
    description: List[str] = Field(
        ..., min_length=1, description="Summaries of the dataset"
    )
    abstract: Optional[str] = Field(
        None, description="Short description of the project"
    )
    keywords: List[str] = Field(..., min_length=1)
    science_branches_mnisw: List[str] = Field(..., min_length=1)
    science_branches_oecd: List[str] = Field(..., min_length=1)
    related_publications: List[RelatedResource] = Field(default_factory=list)
    related_datasets: List[RelatedResource] = Field(default_factory=list)
    notes: Optional[str] = Field(None)
    languages: List[str] = Field(..., min_length=1)
    producers: List[Producer] = Field(default_factory=list)
    funding: List[Funding] = Field(default_factory=list)
    depositor: Optional[str] = Field(
        None, description="Person or organization that deposited the dataset"
    )
    deposit_date: Optional[str] = Field(
        None, description="Automatically filled by system"
    )
    collection_dates: List[str] = Field(
        default_factory=list, description="Date(s) when the data were collected"
    )
    kind_of_data: str = Field(..., description="General type of data deposited")
