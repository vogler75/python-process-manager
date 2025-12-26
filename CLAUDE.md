# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python Process Manager is a lightweight, single-file process manager with an embedded web dashboard. It manages multiple Python programs, provides auto-restart on crashes, and serves a real-time web UI for monitoring and control.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the manager
python3 process_manager.py

# Web UI available at http://localhost:10000 (or configured host/port)
```

There are no separate build, lint, or test commands - this is a single-file application.

## Architecture

The entire application lives in `process_manager.py` (~1,100 lines):

1. **ProcessInfo** (dataclass) - Represents a managed process with state, metrics, and failure tracking
2. **ProcessManager** - Core orchestrator handling process lifecycle, monitoring, logging, and persistence
3. **WebHandler** - HTTP request handler serving both the web UI and REST API (embedded HTML/CSS/JS)

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
