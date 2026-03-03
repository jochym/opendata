# OpenData Tool API Documentation

**Base URL:** `http://127.0.0.1:8080/api`  
**Authentication:** None (localhost only)  
**Status:** ⚠️ **DISABLED BY DEFAULT** - Use `--api` flag to enable  
**Content-Type:** `application/json`

---

## Quick Start

### 1. Enable API

```bash
# Start app with API enabled
python src/opendata/main.py --api
```

### 2. Load Project via API

```bash
# Load a project
curl -X POST http://127.0.0.1:8080/api/projects/load \
  -H "Content-Type: application/json" \
  -d '{"project_path": "/home/jochym/calc/3C-SiC/Project"}'
```

### Set Field Protocol

```bash
# Set field protocol
curl -X POST "http://127.0.0.1:8080/api/projects/ec7e33c23da584709f6322cb52b01d52/field-protocol?field_name=physics"

# Response:
{
  "config": {
    "field_name": "physics"
  },
  "field_name": "physics"
}
```

---

## Endpoints

### Projects

#### List All Projects
```http
GET /api/projects
```

**Response:**
```json
{
  "projects": [
    {
      "id": "ec7e33c23da584709f6322cb52b01d52",
      "path": "/home/jochym/calc/3C-SiC/Project",
      "title": "3C-SiC"
    }
  ]
}
```

---

#### Load Project
```http
POST /api/projects/load
Content-Type: application/json

{
  "project_path": "/home/jochym/calc/3C-SiC/Project"
}
```

**Response:**
```json
{
  "status": "success",
  "project_id": "ec7e33c23da584709f6322cb52b01d52",
  "project_path": "/home/jochym/calc/3C-SiC/Project"
}
```

**Error Response (404):**
```json
{
  "detail": "Project path not found: /invalid/path"
}
```

---

#### Get Project Details
```http
GET /api/projects/{project_id}
```

**Response:**
```json
{
  "project": {
    "id": "ec7e33c23da584709f6322cb52b01d52",
    "path": "/home/jochym/calc/3C-SiC/Project",
    "title": "3C-SiC"
  },
  "config": {
    "field_name": "physics"
  },
  "is_loaded": true
}
```

---

#### Delete Project
```http
DELETE /api/projects/{project_id}
```

**Response:**
```json
{
  "status": "deleted",
  "project_id": "ec7e33c23da584709f6322cb52b01d52"
}
```

---

### Project Configuration

#### Get Configuration
```http
GET /api/projects/{project_id}/config
```

**Response:**
```json
{
  "config": {
    "field_name": "physics"
  }
}
```

---

#### Update Configuration
```http
PUT /api/projects/{project_id}/config
Content-Type: application/json

{
  "field_name": "medical"
}
```

**Response:**
```json
{
  "config": {
    "field_name": "medical"
  }
}
```

---

#### Set Field Protocol
```http
POST /api/projects/{project_id}/field-protocol?field_name=physics
```

**Response:**
```json
{
  "config": {
    "field_name": "physics"
  },
  "field_name": "physics"
}
```

**Error Response (400):**
```json
{
  "detail": "Project must be loaded first"
}
```

---

## Python Examples

### Using requests library

```python
import requests

BASE_URL = "http://127.0.0.1:8080/api"

# List projects
response = requests.get(f"{BASE_URL}/projects")
projects = response.json()["projects"]

# Load project
response = requests.post(
    f"{BASE_URL}/projects/load",
    json={"project_path": "/path/to/project"}
)
project_id = response.json()["project_id"]

# Set field protocol
response = requests.post(
    f"{BASE_URL}/projects/{project_id}/field-protocol",
    params={"field_name": "physics"}
)
```

### Using pytest fixtures

```python
# tests/e2e/conftest.py provides fixtures

def test_with_preloaded_project(page, preloaded_project):
    """Project is automatically loaded via API"""
    page.goto("http://127.0.0.1:8080/protocols")
    # Project already loaded, can test immediately

def test_custom_loading(page, api_project):
    """Manual control via API fixture"""
    # List projects
    projects = api_project.list()
    
    # Set field protocol
    api_project.set_field_protocol(projects[0]["id"], "physics")
    
    # Get config
    config = api_project.get_config(projects[0]["id"])
    assert config["field_name"] == "physics"
```

---

## Error Handling

All API errors return standard HTTP status codes with JSON error messages:

| Status Code | Meaning | Example |
|-------------|---------|---------|
| 200 | Success | Project loaded successfully |
| 400 | Bad Request | Project must be loaded first |
| 404 | Not Found | Project path not found |
| 500 | Server Error | Internal error during operation |

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Security

**Current Implementation:**
- ✅ **DISABLED BY DEFAULT** - Must use `--api` flag
- ✅ Localhost only (127.0.0.1)
- ✅ No authentication required (when enabled)
- ✅ Path validation (prevents directory traversal)

**For Production Use:**
- ⚠️ Keep API disabled in production
- ⚠️ If needed, add API token authentication
- ⚠️ Enable CORS for specific origins
- ⚠️ Add rate limiting
- ⚠️ Validate project paths against allowed directories

---

## Command Line Options

```bash
# Start without API (default, secure)
python src/opendata/main.py

# Start with API enabled (for testing)
python src/opendata/main.py --api

# Start with API in headless mode
python src/opendata/main.py --headless --api
```

**Log Output:**
```
# Without --api:
🔒 API endpoints DISABLED (use --api flag to enable)

# With --api:
✅ API endpoints ENABLED (localhost:8080) - For test automation
```

---

## Testing

### Run API Tests

```bash
# 1. Start app with API enabled
python src/opendata/main.py --api

# 2. Run tests (they will auto-load project via API)
pytest tests/e2e/test_simple_gui.py -v
```

### Manual Testing

```bash
# 1. Start the app
python src/opendata/main.py

# 2. In another terminal, test API
curl http://127.0.0.1:8080/api/projects

# 3. Load project
curl -X POST http://127.0.0.1:8080/api/projects/load \
  -H "Content-Type: application/json" \
  -d '{"project_path": "/home/jochym/calc/3C-SiC/Project"}'
```

---

## Implementation Details

**Files:**
- `src/opendata/api/projects.py` - API endpoint implementations
- `src/opendata/api/__init__.py` - API package initialization
- `tests/e2e/conftest.py` - Test fixtures for API access
- `src/opendata/ui/app.py` - API registration

**Architecture:**
- Built on NiceGUI's FastAPI-compatible routing
- Reuses existing `handle_load_project()` logic
- Synchronous API calls (no async in tests)
- Localhost-only binding (security by default)

---

**Last Updated:** February 17, 2026  
**Version:** 1.0.0  
**Status:** Production Ready
