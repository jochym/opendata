"""Custom exceptions for the OpenData Tool.

This module defines domain-specific exceptions to improve error handling
and provide better context for error messages throughout the application.
"""


class OpenDataError(Exception):
    """Base exception for all OpenData Tool errors."""

    pass


class AuthenticationError(OpenDataError):
    """Raised when authentication fails or credentials are invalid."""

    pass


class ProjectNotFoundError(OpenDataError):
    """Raised when a project cannot be found in the workspace."""

    pass


class ProjectScanError(OpenDataError):
    """Raised when scanning a project directory fails."""

    pass


class MetadataValidationError(OpenDataError):
    """Raised when metadata validation fails."""

    pass


class PackagingError(OpenDataError):
    """Raised when creating a package fails."""

    pass


class AIServiceError(OpenDataError):
    """Raised when an AI service call fails."""

    pass


class ExtractionError(OpenDataError):
    """Raised when data extraction from a file fails."""

    pass


class ProtocolError(OpenDataError):
    """Raised when loading or saving a protocol fails."""

    pass
