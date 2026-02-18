"""
Project Management API

Provides REST endpoints for project management operations.
Designed for test automation and programmatic access.

Security: Localhost only (no authentication required)
"""

from nicegui import app
from fastapi import HTTPException
from pathlib import Path
import logging

logger = logging.getLogger("opendata.api.projects")


def register_project_api(ctx):
    """Registers project API endpoints with the NiceGUI app."""
    
    # Define endpoint functions
    async def list_projects():
        """List all available projects."""
        try:
            projects = ctx.wm.list_projects()
            return {"projects": projects}
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            raise HTTPException(500, str(e))
    
    async def load_project(project_data: dict):
        """Load a project by path."""
        try:
            from opendata.ui.components.header import handle_load_project
            
            project_path = project_data.get("project_path")
            if not project_path:
                raise HTTPException(400, "project_path is required")
            
            # Validate path
            path_obj = Path(project_path).expanduser().resolve()
            if not path_obj.exists():
                raise HTTPException(404, f"Project path not found: {project_path}")
            
            # Load project
            await handle_load_project(ctx, str(path_obj))
            
            return {
                "status": "success",
                "project_id": ctx.agent.project_id,
                "project_path": str(path_obj)
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error loading project: {e}", exc_info=True)
            raise HTTPException(500, str(e))
    
    async def get_project(project_id: str):
        """Get project details."""
        try:
            # Check if project exists
            projects = ctx.wm.list_projects()
            project = next((p for p in projects if p["id"] == project_id), None)
            if not project:
                raise HTTPException(404, f"Project not found: {project_id}")
            
            # Get project config if loaded
            config = {}
            if ctx.agent.project_id == project_id:
                config = ctx.wm.load_project_config(project_id)
            
            return {
                "project": project,
                "config": config,
                "is_loaded": ctx.agent.project_id == project_id
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting project: {e}", exc_info=True)
            raise HTTPException(500, str(e))
    
    async def get_project_config(project_id: str):
        """Get project configuration."""
        try:
            config = ctx.wm.load_project_config(project_id)
            return {"config": config}
        except Exception as e:
            logger.error(f"Error getting config: {e}", exc_info=True)
            raise HTTPException(500, str(e))
    
    async def update_project_config(project_id: str, config: dict):
        """Update project configuration."""
        try:
            # Load existing config
            existing_config = ctx.wm.load_project_config(project_id)
            
            # Merge configs
            existing_config.update(config)
            
            # Save
            ctx.wm.save_project_config(project_id, existing_config)
            
            return {"config": existing_config}
        except Exception as e:
            logger.error(f"Error updating config: {e}", exc_info=True)
            raise HTTPException(500, str(e))
    
    async def delete_project(project_id: str):
        """Delete a project from workspace."""
        try:
            success = ctx.wm.delete_project(project_id)
            if success:
                return {"status": "deleted", "project_id": project_id}
            else:
                raise HTTPException(500, "Failed to delete project")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting project: {e}", exc_info=True)
            raise HTTPException(500, str(e))
    
    async def set_field_protocol(project_id: str, field_name: str):
        """Set field protocol for a project."""
        try:
            # Verify project is loaded
            if ctx.agent.project_id != project_id:
                raise HTTPException(400, "Project must be loaded first")
            
            # Set field protocol
            ctx.agent.set_field_protocol(field_name)
            
            # Return updated config
            config = ctx.wm.load_project_config(project_id)
            return {"config": config, "field_name": field_name}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error setting field protocol: {e}", exc_info=True)
            raise HTTPException(500, str(e))
    
    # Register routes using add_api_route
    app.add_api_route("/api/projects", list_projects, methods=["GET"])
    app.add_api_route("/api/projects/load", load_project, methods=["POST"])
    app.add_api_route("/api/projects/{project_id}", get_project, methods=["GET"])
    app.add_api_route("/api/projects/{project_id}/config", get_project_config, methods=["GET"])
    app.add_api_route("/api/projects/{project_id}/config", update_project_config, methods=["PUT"])
    app.add_api_route("/api/projects/{project_id}", delete_project, methods=["DELETE"])
    app.add_api_route("/api/projects/{project_id}/field-protocol", set_field_protocol, methods=["POST"])
    
    logger.info("Project API routes registered successfully")
