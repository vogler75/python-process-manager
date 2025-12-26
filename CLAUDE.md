# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python Process Manager is a lightweight process manager with an embedded web dashboard. It manages multiple Python programs, provides auto-restart on crashes, and serves a real-time web UI for monitoring and control.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the manager (as a module)
python3 -m process_manager

# Or using the old single-file script (if it exists)
# python3 process_manager.py

# Web UI available at http://localhost:10000 (or configured host/port)
```

There are no separate build, lint, or test commands - this is a straightforward Python package.

## Architecture

The application is organized as a Python package in `process_manager/`:

```
process_manager/
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

### Process States
`stopped` → `running` → `restarting` (auto) → `broken` (after max failures)

### Configuration
Edit `process_manager.yaml`:
- `web_ui`: host, port, title
- `venv_path`: global Python venv (can override per-program)
- `cwd`: global working directory (can override per-program)
- `restart`: delay, max_consecutive_failures, failure_reset_seconds
- `logging`: max_size_mb for log rotation
- `programs`: list of {name, script, enabled, venv_path, cwd, args}

## Runtime Files (Generated)

- `process_manager.pids.json` - Saved process states for persistence across restarts
- `{program_name}.log` - Process output logs
- `{program_name}.log.1` - Rotated log files

## Dependencies

- `pyyaml` - Configuration parsing (required)
- `psutil` - CPU monitoring (optional, graceful degradation if missing)
