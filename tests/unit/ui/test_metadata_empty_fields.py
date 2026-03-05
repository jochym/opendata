"""Tests for metadata field editing - Issue #48: Non-editable metadata fields."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from opendata.ui.context import AppContext
from opendata.workspace import WorkspaceManager
from opendata.agents.project_agent import ProjectAnalysisAgent
from opendata.models import ProjectFingerprint, AIAnalysis, Metadata


@pytest.fixture
def app_context(tmp_path):
    """Creates a mock AppContext with initialized agent and empty metadata."""
    wm = WorkspaceManager(base_path=tmp_path)
    agent = ProjectAnalysisAgent(wm=wm)

    # Setup mock fingerprint
    agent.current_fingerprint = ProjectFingerprint(
        root_path=str(tmp_path),
        file_count=3,
        total_size_bytes=1500,
        extensions=[".tex", ".py"],
        structure_sample=["paper.tex", "script.py"],
        primary_file="paper.tex",
        significant_files=["paper.tex"],
    )

    # Setup mock analysis
    agent.current_analysis = AIAnalysis(summary="Test")
    agent.heuristics_run = True

    # Create mock context
    ctx = MagicMock(spec=AppContext)
    ctx.agent = agent
    ctx.session = MagicMock()
    ctx.session.inventory_cache = []
    ctx.session.folder_children_map = {}
    ctx.session.explorer_path = ""
    ctx.refresh = MagicMock()

    return ctx


class TestEmptyMetadataFields:
    """Tests for Issue #48: All metadata fields should be visible and editable even when empty."""

    def test_all_fields_visible_when_empty(self, app_context):
        """All RODBUK mandatory fields should be visible even when empty."""
        # Arrange: Metadata is empty (default)
        metadata = app_context.agent.current_metadata

        # Act: Get all field names (excluding internal fields)
        all_fields = metadata.model_dump()
        visible_fields = [
            k for k in all_fields.keys() if k not in ["locked_fields", "ai_model"]
        ]

        # Assert: All fields are accessible (not just set ones)
        assert "title" in visible_fields
        assert "authors" in visible_fields
        assert "abstract" in visible_fields
        assert "license" in visible_fields
        assert "keywords" in visible_fields

    def test_mandatory_fields_are_identified(self, app_context):
        """Mandatory fields should be correctly identified."""
        # Arrange
        MANDATORY_FIELDS = {"title", "authors", "abstract", "license", "keywords"}
        metadata = app_context.agent.current_metadata

        # Act: Check each mandatory field
        for field in MANDATORY_FIELDS:
            # Assert: Field exists
            assert hasattr(metadata, field)
            # Note: license has default "CC-BY-4.0", others are None or empty list

    def test_empty_field_detection_logic(self, app_context):
        """Test the logic for detecting empty fields."""
        # Arrange
        metadata = app_context.agent.current_metadata

        # Act & Assert: None values are empty
        assert metadata.title is None
        assert (metadata.title is None) == True

        # Act & Assert: Empty lists are empty
        assert metadata.authors == []
        assert (
            isinstance(metadata.authors, list) and len(metadata.authors) == 0
        ) == True

        # Act: Set a value
        metadata.title = "Test Title"

        # Assert: Field is no longer empty
        assert metadata.title is not None
        assert (metadata.title is None) == False

    def test_field_value_can_be_set_from_empty(self, app_context):
        """Empty fields should be settable."""
        # Arrange: Start with empty title
        metadata = app_context.agent.current_metadata
        assert metadata.title is None

        # Act: Set the field
        metadata.title = "New Title"

        # Assert: Field is updated
        assert metadata.title == "New Title"

    def test_list_field_can_be_populated_from_empty(self, app_context):
        """Empty list fields should be populateable."""
        # Arrange: Start with empty keywords
        metadata = app_context.agent.current_metadata
        assert metadata.keywords == []

        # Act: Set the field
        metadata.keywords = ["physics", "data"]

        # Assert: Field is updated
        assert len(metadata.keywords) == 2
        assert "physics" in metadata.keywords

    def test_authors_field_can_be_populated_from_empty(self, app_context):
        """Empty authors field should be populateable."""
        # Arrange: Start with empty authors
        metadata = app_context.agent.current_metadata
        assert metadata.authors == []

        # Act: Add an author
        from opendata.models import PersonOrOrg

        metadata.authors = [PersonOrOrg(name="John Doe", affiliation="University")]

        # Assert: Field is updated
        assert len(metadata.authors) == 1
        assert metadata.authors[0].name == "John Doe"

    def test_edit_dialog_handles_none_values(self, app_context):
        """Edit dialog should handle None values gracefully."""
        # Arrange: Field is None
        metadata = app_context.agent.current_metadata
        assert metadata.title is None

        # Act: Simulate what edit dialog does
        val = getattr(metadata, "title")
        display_value = val or ""

        # Assert: None is converted to empty string for editing
        assert display_value == ""
        assert isinstance(display_value, str)

    def test_edit_dialog_handles_empty_list_values(self, app_context):
        """Edit dialog should handle empty list values gracefully."""
        # Arrange: Field is empty list
        metadata = app_context.agent.current_metadata
        assert metadata.keywords == []

        # Act: Simulate what edit dialog does for list fields
        val = getattr(metadata, "keywords")
        display_value = "\n".join(val) if val else ""

        # Assert: Empty list is converted to empty string
        assert display_value == ""
        assert isinstance(display_value, str)

    def test_save_value_from_empty_string_works(self, app_context):
        """Saving a value from empty string should work."""
        # Arrange: Field is empty
        metadata = app_context.agent.current_metadata
        assert metadata.title is None

        # Act: Simulate save operation
        new_val = "New Title"
        setattr(metadata, "title", new_val)

        # Assert: Value is saved
        assert metadata.title == "New Title"

    def test_save_list_from_empty_works(self, app_context):
        """Saving a list from empty should work."""
        # Arrange: Field is empty
        metadata = app_context.agent.current_metadata
        assert metadata.keywords == []

        # Act: Simulate save operation for keywords
        new_val = "physics\ndata\nscience"
        new_list = [line.strip() for line in new_val.split("\n") if line.strip()]
        setattr(metadata, "keywords", new_list)

        # Assert: List is saved
        assert len(metadata.keywords) == 3
        assert "physics" in metadata.keywords
        assert "data" in metadata.keywords
        assert "science" in metadata.keywords

    def test_mandatory_fields_visual_indicator_needed(self, app_context):
        """Mandatory empty fields should have visual indicators (tested via logic)."""
        # Arrange
        MANDATORY_FIELDS = {"title", "authors", "abstract", "license", "keywords"}
        metadata = app_context.agent.current_metadata

        # Act: Check which mandatory fields are empty (license has default)
        empty_mandatory = []
        for field in MANDATORY_FIELDS:
            value = getattr(metadata, field)
            is_empty = value is None or (isinstance(value, list) and len(value) == 0)
            if is_empty:
                empty_mandatory.append(field)

        # Assert: Most mandatory fields are empty (except license which has default)
        assert len(empty_mandatory) == 4  # All except license
        assert "title" in empty_mandatory
        assert "authors" in empty_mandatory
        assert "abstract" in empty_mandatory
        assert "keywords" in empty_mandatory
        assert "license" not in empty_mandatory  # Has default "CC-BY-4.0"

    def test_optional_fields_dont_need_warning_indicator(self, app_context):
        """Optional empty fields should not show warning indicators."""
        # Arrange
        MANDATORY_FIELDS = {"title", "authors", "abstract", "license", "keywords"}
        OPTIONAL_FIELDS = {"alternative_titles", "notes", "related_publications"}
        metadata = app_context.agent.current_metadata

        # Act & Assert: Optional fields exist and are empty but shouldn't trigger warning
        for field in OPTIONAL_FIELDS:
            assert hasattr(metadata, field)
            # These are empty but that's OK - no red warning needed
            value = getattr(metadata, field)
            is_empty = value is None or (isinstance(value, list) and len(value) == 0)
            assert is_empty == True
            # But they're not mandatory, so no warning
            assert field not in MANDATORY_FIELDS
