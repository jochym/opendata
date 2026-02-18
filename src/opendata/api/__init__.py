"""
OpenData Tool API

REST API endpoints for test automation and programmatic access.
All endpoints are localhost-only (no authentication required).
"""

from .projects import register_project_api

__all__ = ["register_project_api"]
