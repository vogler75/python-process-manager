# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Process Manager is a lightweight process manager with an embedded web dashboard. It manages multiple Python, Node.js, and plain executable programs, provides auto-restart on crashes, and serves a real-time web UI for monitoring and control.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the manager (as a module)
python3 -m manager

# Web UI available at http://localhost:10000 (or configured host/port)
```

There are no separate build, lint, or test commands - this is a straightforward Python package.

## Architecture

The application is organized as a Python package in `manager/`:

```
manager/
├── __init__.py         # Package exports
├── __main__.py         # Entry point (signal handling, HTTP server setup)
├── models.py           # ProcessInfo dataclass (state, metrics, failure tracking)
├── manager.py          # ProcessManager (lifecycle, monitoring, logging, persistence)
├── web_handler.py      # WebHandler (HTTP request routing, API endpoints)
└── web_template.py     # HTML/CSS/JS template for web UI
```

Key components:
1. **ProcessInfo** (models.py) - Represents a managed process with state, metrics, and failure tracking
2. **ProcessManager** (manager.py) - Core orchestrator handling process lifecycle, monitoring, logging, and persistence
3. **WebHandler** (web_handler.py) - HTTP request handler serving both the web UI and REST API
4. **get_html()** (web_template.py) - Embedded HTML/CSS/JS for the web dashboard

### Threading Model
- Main thread runs the HTTP server
- Daemon thread monitors process health (2-second interval)
- Background threads handle async stop/restart operations

### Key API Endpoints
- `GET /` - Web UI
- `GET /api/status` - JSON status of all processes
- `GET /api/logs/{name}?lines=100&offset=0` - Paginated log content
- `POST /api/start|stop|restart/{name}` - Process control
- `POST /api/upload` - Upload new program (multipart form data with ZIP)
- `POST /api/add` - Add new program (JSON, no ZIP)
- `POST /api/edit/{name}` - Edit program configuration (JSON)
- `POST /api/update/{name}` - Update uploaded program code (multipart with ZIP)
- `POST /api/remove/{name}` - Remove program

### Process States
`stopped` → `running` → `restarting` (auto) → `broken` (after max failures)
`installing` → `running` (for uploaded programs during background installation)

### Configuration

The application uses two configuration files:

**`manager.yaml`** - Settings only:
- `web_ui`: host, port, title
- `venv`: global Python venv (can override per-program)
- `node`: path to Node.js executable (optional, defaults to PATH)
- `cwd`: global working directory (can override per-program)
- `restart`: delay, max_consecutive_failures, failure_reset_seconds
- `logging`: max_size_mb for log rotation

**`progs.yaml`** - All program definitions:
- `programs`: list of all programs {name, script, module, type, enabled, uploaded, comment, venv, cwd, args, environment}
- `script`: path to script file (for Python, Node.js, or exec types)
- `module`: Python module name for `-m` execution (e.g., `uvicorn`, `flask`). Mutually exclusive with `script`
- `type`: "python" (default), "node" for Node.js, or "exec" for plain executables
- Managed via web UI (Add, Edit, Remove)
- The `uploaded` field marks programs that have upload directories (can update via ZIP)

## Runtime Files (Generated)

- `manager.pids.json` - Saved process states for persistence across restarts
- `progs.yaml` - All program definitions (created on first run)
- `uploaded_programs/` - Directory containing uploaded program files
  - `{program_name}/` - Each uploaded program gets its own directory
    - `.venv/` - Isolated virtual environment (Python only)
    - `node_modules/` - npm packages (Node.js only)
    - `*.py`, `*.js`, or executable files - Program source files
    - `requirements.txt` or `package.json` - Dependencies (optional, not used for exec type)
- `log/{program_name}.log` - Process output logs
- `log/{program_name}.log.1` - Rotated log files

## Dependencies

- `pyyaml` - Configuration parsing (required)
- `psutil` - CPU monitoring (optional, graceful degradation if missing)
