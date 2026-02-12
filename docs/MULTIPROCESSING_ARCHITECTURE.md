# NiceGUI Multiprocessing Implementation

## Overview
This document explains the multiprocessing architecture used in the OpenData Tool and why the current implementation is correct.

## Architecture

### Components
- **Main Process**: Tkinter-based Anchor window (lightweight GUI)
- **Child Process**: NiceGUI web server (heavy imports, AI services)
- **Process Communication**: Process lifecycle management only (no IPC needed)

### Process Flow
1. Main process starts Tkinter Anchor window
2. Main process spawns child process for NiceGUI server
3. Child process initializes and starts web server
4. Main process opens system browser (after 1.5s delay)
5. User interacts via browser
6. Closing Anchor terminates child process cleanly

## The Multiprocessing Challenge

### NiceGUI's Design Decision
NiceGUI **intentionally** prevents server startup in child processes. From `nicegui/ui_run.py` (lines 165-166):

```python
if multiprocessing.current_process().name != 'MainProcess':
    return
```

**Rationale**: Prevents accidental server starts in worker processes when using `multiprocessing.Pool()` or similar patterns.

### Impact on Our Architecture
Since we use:
```python
server_process = multiprocessing.Process(
    target=run_server_process,
    args=(args.host, args.port),
    name="OpenDataServer",  # <-- Not "MainProcess"
)
```

The process name is `"OpenDataServer"`, causing `ui.run()` to return early.

## The Solution

### Implementation (`src/opendata/ui/app.py`)

```python
def start_ui(host: str = "127.0.0.1", port: int = 8080):
    """Start the NiceGUI application server.
    
    Note: When running in a multiprocessing child process, NiceGUI's ui.run()
    returns early by design (see nicegui.ui_run line 165-166). We handle this
    by manually starting uvicorn if the app wasn't started.
    """
    import uvicorn
    
    # ... application initialization ...
    
    # Initialize NiceGUI app (completes setup even in child processes)
    ui.run(title="OpenData Agent", port=port, show=False, reload=False, host=host)
    
    # Start server manually if ui.run() returned early (multiprocessing child)
    if not app.is_started:
        uvicorn.run(app, host=host, port=port, log_level="info")
```

### Why This Works

1. **Complete Initialization**: `ui.run()` performs ALL initialization (routes, middleware, config) before checking process name
2. **app Object Ready**: The FastAPI/Starlette `app` object is fully configured when `ui.run()` returns
3. **Standard Pattern**: Calling `uvicorn.run(app, ...)` is the normal way to start a Starlette/FastAPI app
4. **Safe Check**: `app.is_started` ensures we don't double-start in `--headless` mode

### Verification

Testing confirms:
- ✓ All `@ui.page()` routes are registered
- ✓ Middleware is properly configured
- ✓ Pages render correctly
- ✓ WebSocket connections work
- ✓ Server blocks as expected
- ✓ Clean shutdown via `terminate()` works

## Alternative Approaches Considered

### ❌ Option 1: Rename Process to "MainProcess"
```python
# DON'T DO THIS
multiprocessing.current_process().name = "MainProcess"
ui.run(...)
```
**Rejected**: Brittle hack that could break with NiceGUI updates.

### ❌ Option 2: Use Threading Instead
```python
# Run NiceGUI in main process, Tkinter in thread
```
**Rejected**: Tkinter threading is problematic on some platforms. Current architecture (Tk in main, web in child) is more robust.

### ❌ Option 3: Run Both in Main Process
```python
# No multiprocessing
```
**Rejected**: Heavy NiceGUI imports delay Anchor window appearance. User experience suffers.

## Conclusion

The current implementation is:
- ✅ **Correct**: Works with NiceGUI's design, not against it
- ✅ **Robust**: Tested and verified across scenarios
- ✅ **Maintainable**: Clear comments explain the why
- ✅ **Standard**: Uses documented FastAPI/uvicorn patterns

This is **not a hack** - it's a proper workaround for NiceGUI's multiprocessing limitation.

## References
- NiceGUI source: `nicegui/ui_run.py` lines 165-166
- Testing: `REVIEW_NICEGUI_FIX.md` (detailed analysis)
- FastAPI/Uvicorn docs: https://www.uvicorn.org/
