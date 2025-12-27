# Python Process Manager

A lightweight, self-contained process manager for Python applications with a beautiful web UI. Monitor, control, and view logs of multiple Python programs from a single dashboard.

## Features

- **Web-based Dashboard** - Modern, responsive UI with real-time status updates
- **Program Upload** - Upload Python programs as ZIP files directly from the web UI
- **Background Installation** - Automatic venv creation and dependency installation with live logs
- **Process Monitoring** - Automatic restart on failures with configurable retry limits
- **CPU Monitoring** - Real-time CPU usage tracking with sparkline charts (requires psutil)
- **Log Management** - Automatic log rotation with built-in log viewer
- **Persistent State** - Processes survive manager restarts
- **Flexible Configuration** - Global settings with per-program overrides for venv, cwd, and args
- **Virtual Environment Support** - Global or per-program Python venv configuration
- **Working Directory Control** - Set cwd globally or per-program; scripts resolved relative to cwd
- **Command-Line Arguments** - Pass args to scripts as list or string
- **Zero Dependencies UI** - No external JavaScript frameworks, pure HTML/CSS/JS
- **Graceful Shutdown** - Manager stops without killing managed processes

![Card View](doc/picture-card-view.png)
![Table View](doc/picture-table-view.png)

## Installation

### Requirements

- Python 3.7+
- Virtual environment (recommended)

### Setup

1. Clone or download this repository

2. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```
   *Note: If you encounter `ModuleNotFoundError: No module named 'psutil'` or issues during `psutil` installation, ensure you have the necessary build tools for your operating system (e.g., `python3-dev` and `gcc` on Linux, Xcode command line tools on macOS, or Visual C++ Build Tools on Windows). `psutil` is required for CPU monitoring features.*

## Configuration

Edit `manager.yaml` to configure your setup:

```yaml
# Web UI settings
web_ui:
  host: "0.0.0.0"      # Bind address (0.0.0.0 for all interfaces)
  port: 10000          # Web UI port
  title: "My Services" # Custom title for the dashboard

# Python Virtual Environment
venv: ".venv"     # Path to venv (relative or absolute)

# Working Directory (optional, can override per-program)
# cwd: "/path/to/scripts"

# Restart settings
restart:
  delay_seconds: 1                # Wait time before restart
  max_consecutive_failures: 10    # Mark as broken after N failures
  failure_reset_seconds: 60       # Reset failure count after stable run

# Logging settings
logging:
  max_size_mb: 10      # Log rotation threshold

# Programs to manage
programs:
  - name: "My Application"
    script: my_app.py
    enabled: true
    # venv: ".venv"  # Optional: program-specific venv
    # cwd: "/path/to/workdir"  # Optional: working directory
    # args: ["--port", "8080"]  # Optional: command-line arguments
    # environment:  # Optional: environment variables
    #   - PYTHONUNBUFFERED=TRUE
    #   - API_KEY=your-key-here
```

### Configuration Options

#### Web UI
- `host` - Network interface to bind (use `127.0.0.1` for localhost only)
- `port` - HTTP port for the web interface
- `title` - Custom title displayed in the dashboard

#### Virtual Environment (`venv`)
- **Global**: Set at top level, applies to all programs (default: `.venv`)
- **Per-program**: Override in program config for specific programs
- Path can be relative (to config file) or absolute
- Priority: **program venv > global venv**

#### Working Directory (`cwd`)
- **Global**: Set at top level, applies to all programs
- **Per-program**: Override in program config for specific programs
- Scripts are resolved relative to the working directory
- Path can be relative (to config file) or absolute
- Priority: **program cwd > global cwd > config file directory**

#### Arguments (`args`)
- Command-line arguments passed to the script
- Can be a list: `["--port", "8080", "--verbose"]`
- Can be a single value: `"--verbose"`
- Only available per-program (no global setting)

#### Environment Variables (`environment`)
- Environment variables set for the process
- List of `KEY=VALUE` strings
- Each program can have its own environment variables
- Merged with system environment (program-specific vars take precedence)
- Example:
  ```yaml
  environment:
    - PYTHONUNBUFFERED=TRUE
    - DTU_HOST=192.168.1.132
    - UPDATE_EVERY=45
  ```
- Only available per-program (no global setting)

#### Restart Behavior
- `delay_seconds` - Delay before restarting a failed process
- `max_consecutive_failures` - Maximum failures before marking as broken
- `failure_reset_seconds` - Stable runtime required to reset failure counter

#### Logging
- `max_size_mb` - Maximum log file size before rotation (copytruncate method)

#### Programs
- `name` - Display name in the UI
- `script` - Python script path (resolved relative to `cwd` if set, otherwise config directory)
- `enabled` - Auto-start on manager launch (default: true)
- `venv` - Override global venv for this program
- `cwd` - Override global cwd for this program
- `args` - Command-line arguments (list or single string)
- `environment` - Environment variables (list of KEY=VALUE strings)

## Usage

### Starting the Manager

```bash
python3 -m manager
```

The manager will:
1. Load settings from `manager.yaml` and programs from `progs.yaml`
2. Restore any previously running processes
3. Start all enabled programs
4. Launch the web UI

```
Process Manager started
Web UI available at http://0.0.0.0:10000
Press Ctrl+C to stop
```

### Accessing the Web UI

Open your browser and navigate to `http://localhost:10000` (or the configured host/port).

### Stopping the Manager

Press `Ctrl+C` to gracefully shutdown. The manager will:
- Save current process states
- Exit without stopping managed processes
- Processes continue running in the background

On next startup, the manager will reconnect to running processes.

## Web UI Features

### Dashboard

- **Real-time Status** - Process state updates every 2 seconds
- **CPU Charts** - Live sparkline graphs showing CPU usage history
- **Process Controls** - Start, Stop, Restart buttons for each program
- **Log Viewer** - Click "Logs" to view process output in a modal

### Process States

- **Running** (Green) - Process is active and healthy
- **Stopped** (Red) - Process is not running
- **Installing** (Purple) - Program is being installed (venv creation + pip install)
- **Restarting** (Blue) - Automatic restart in progress
- **Stopping** (Orange) - Shutdown in progress
- **Error** (Orange) - Installation or runtime error occurred
- **Broken** (Red) - Too many consecutive failures, auto-restart disabled

### Log Viewer

- **Pagination** - Navigate through large log files
- **Auto-refresh** - Toggle live tail mode
- **File Info** - Shows line ranges and total size
- **Keyboard Shortcuts** - Press `Esc` to close modal

## Adding Programs

### Add via Web UI

Click the **"+ New Program"** button in the top right to add a new Python program:

1. **Name** - Display name for the program
2. **Script** - Main Python file to run (e.g., `main.py`, `app.py`)
3. **ZIP File** (optional) - Select a ZIP file containing your program files
4. **Comment** (optional) - Description or notes about the program
5. **Arguments** - Optional command-line arguments
6. **Environment Variables** - Optional KEY=VALUE pairs (one per line)
7. **Start automatically** - Check to auto-start after adding

**Two modes:**
- **With ZIP file**: Creates an uploaded program with isolated venv and installs dependencies
- **Without ZIP file**: Creates a manual program referencing existing scripts on disk

When uploading with a ZIP file, the manager will:
- Extract the ZIP file to `uploaded_programs/{Program_Name}/`
- Create a dedicated virtual environment at `.venv/`
- Install dependencies from `requirements.txt` (if present)
- Show real-time installation logs
- Auto-start the program (if enabled)

### ZIP File Structure

Your ZIP can be structured in two ways:

**Option 1: Files directly in ZIP root**
```
program.zip
├── main.py
├── requirements.txt
├── config.yaml
└── utils.py
```

**Option 2: Single top-level folder (auto-flattened)**
```
program.zip
└── my_program/
    ├── main.py
    ├── requirements.txt
    └── utils.py
```

Both structures work - the manager automatically flattens single-folder ZIPs.

### Background Installation

After upload, programs install in the background:
- Status shows **"installing"** (purple badge)
- Click **"Logs"** to watch real-time installation progress
- Venv creation and pip install output streams to the log
- Status automatically changes to **"running"** or **"stopped"** when done

Example installation log:
```
==================================================================
Program Upload: My App
Time: 2025-12-26 16:45:23
Directory: /path/to/uploaded_programs/My_App
==================================================================

============================================================
Creating virtual environment...
Command: /usr/bin/python3 -m venv /path/to/.venv
============================================================

[SUCCESS] Virtual environment created successfully

============================================================
Installing dependencies from requirements.txt...
Command: /path/to/.venv/bin/python -m pip install -r requirements.txt
============================================================

Collecting requests==2.31.0
  Downloading requests-2.31.0-py3-none-any.whl (62 kB)
Installing collected packages: requests
Successfully installed requests-2.31.0

[SUCCESS] Dependencies installed successfully
==================================================================
[SUCCESS] Installation completed successfully!
==================================================================
```

### Managing Programs

All programs can be edited and removed via the web UI:

- **Edit** - Modify program settings (name, script, args, environment, etc.)
- **Remove** - Delete the program from configuration (only when stopped)

For uploaded programs, the Edit dialog also allows:
- **Update Code** - Upload a new ZIP to replace program files (keeps venv)

**Edit Process:**
1. Click **"Edit"** button on the program
2. Modify settings as needed
3. For uploaded programs: optionally upload a new ZIP file
4. Click **"Save Changes"**

**Remove Process:**
1. Stop the program
2. Click **"Remove"** button
3. Confirm deletion
4. Program is removed from config (uploaded programs also delete files)

### Size Limits and Restrictions

- **Maximum ZIP size**: 50 MB
- **Security**: Path traversal attacks are prevented (no `..` or `/` in paths)
- **Name conflicts**: Cannot add if name already exists (use Edit to modify)

### Creating a Test Program

To create a simple test program for upload:

1. Create a directory with your program files:
```bash
mkdir my_test_app
cd my_test_app
```

2. Create `main.py`:
```python
import time
from datetime import datetime

while True:
    print(f"[{datetime.now()}] Test app is running...")
    time.sleep(10)
```

3. Create `requirements.txt` (optional):
```
requests==2.31.0
```

4. Create the ZIP file:
```bash
# Option 1: Zip the contents (recommended)
zip -r ../my_test_app.zip .

# Option 2: Zip the folder (also works - auto-flattened)
cd ..
zip -r my_test_app.zip my_test_app/
```

5. Upload via web UI:
   - Name: "Test App"
   - Script: "main.py"
   - ZIP: Select `my_test_app.zip`
   - Check "Start automatically"

## Process Management

### Automatic Restart

Processes are automatically restarted when they crash. The failure counter resets after running successfully for `failure_reset_seconds`.

### Broken State

After `max_consecutive_failures`, a process is marked as **broken** and auto-restart is disabled. Use the **Restart** button to manually reset and restart.

### Log Rotation

When a log file exceeds `max_size_mb`, it's copied to `{name}.log.1` and truncated. This uses the copytruncate method, so processes keep writing without interruption.

### Process Persistence

Process IDs are saved to `manager.pids.json`. When the manager restarts:
- It checks if processes are still running
- Reconnects to running processes
- Starts stopped processes if enabled

## File Structure

```
.
├── manager/                    # Main application package
│   ├── __init__.py
│   ├── __main__.py
│   ├── models.py
│   ├── manager.py
│   ├── web_handler.py
│   └── web_template.py
├── manager.yaml                # Settings configuration (web UI, restart, logging, venv)
├── progs.yaml                  # All program definitions (auto-managed)
├── requirements.txt            # Python dependencies
├── manager.pids.json           # Saved process states (auto-generated)
├── uploaded_programs/          # Uploaded program files (auto-generated)
│   └── {Program_Name}/
│       ├── .venv/              # Program-specific virtual environment
│       ├── main.py
│       ├── requirements.txt
│       └── ...
└── log/                        # Log directory (auto-generated)
    ├── {program_name}.log      # Process log files
    └── {program_name}.log.1    # Rotated log files
```

### Configuration Files

- **`manager.yaml`** - Settings only (web UI, restart behavior, logging, global venv/cwd)
- **`progs.yaml`** - All program definitions (both manual and uploaded)
  - Managed via web UI (Edit, Add, Remove)
  - Can also be edited manually when the manager is not running

## Advanced Usage

### Global Settings with Per-Program Overrides

Set defaults at the top level and override for specific programs:

```yaml
# Global settings - apply to all programs unless overridden
venv: ".venv"
cwd: "/data/apps/myproject"

programs:
  # Uses global venv and cwd
  - name: "Main App"
    script: main.py
    args: ["--config", "prod.yaml"]

  # Uses global cwd, but different venv
  - name: "Legacy App"
    script: legacy.py
    venv: ".venv-python37"

  # Uses global venv, but different cwd
  - name: "Admin Tool"
    script: admin.py
    cwd: "/data/apps/admin"
    args: "--verbose"
```

### Working Directory and Script Resolution

The `cwd` setting controls both:
1. Where the script file is looked up
2. The working directory when the process runs

```yaml
cwd: "/data/apps/trading"  # Global cwd

programs:
  # Script resolved as: /data/apps/trading/streamer.py
  - name: "Streamer"
    script: streamer.py

  # Script resolved as: /data/apps/tools/monitor.py (cwd override)
  - name: "Monitor"
    script: monitor.py
    cwd: "/data/apps/tools"
```

### Command-Line Arguments

Pass arguments to your scripts:

```yaml
programs:
  # List format (recommended for multiple args)
  - name: "Web Server"
    script: server.py
    args: ["--host", "0.0.0.0", "--port", "8080", "--workers", "4"]

  # String format (convenience for single arg)
  - name: "Worker"
    script: worker.py
    args: "--verbose"
```

### Environment Variables

Set environment variables for your programs:

```yaml
programs:
  - name: "Data Collector"
    script: collector.py
    environment:
      - PYTHONUNBUFFERED=TRUE        # Disable Python output buffering
      - DTU_HOST=192.168.1.132       # Custom application config
      - UPDATE_EVERY=45              # Polling interval
      - LOG_LEVEL=INFO               # Logging verbosity
      - API_KEY=your-api-key-here    # API credentials

  - name: "Production API"
    script: api.py
    environment:
      - PYTHONUNBUFFERED=TRUE
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://localhost/mydb
      - REDIS_URL=redis://localhost:6379
```

Environment variables are merged with the system environment, with program-specific variables taking precedence.

### Running in Production

#### Using systemd (Linux)

Create `/etc/systemd/system/process-manager.service`:

```ini
[Unit]
Description=Python Process Manager
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/process-manager
ExecStart=/path/to/.venv/bin/python -m manager
Restart=always
KillMode=process

[Install]
WantedBy=multi-user.target
```

**Important: `KillMode=process`**

The `KillMode=process` setting is **critical** - it tells systemd to only kill the process manager itself, not the managed Python programs. Without this:
- `systemctl stop` or `systemctl restart` will kill all your managed programs
- Defeats the purpose of process persistence

With `KillMode=process`:
- Only the manager is stopped/restarted
- Managed programs keep running
- Manager reconnects to them on restart

Enable and start:
```bash
sudo systemctl enable process-manager
sudo systemctl start process-manager
```

Reload after changes:
```bash
sudo systemctl daemon-reload
sudo systemctl restart process-manager
```

#### Using screen/tmux

```bash
screen -dmS process-manager python3 -m manager
```

Reattach:
```bash
screen -r process-manager
```

### Security Considerations

- **Network Access** - Set `host: "127.0.0.1"` to restrict to localhost
- **Firewall** - Use firewall rules to control access to the web UI port
- **Authentication** - The web UI has no built-in authentication; use a reverse proxy with auth if needed

## Troubleshooting

### Process Not Starting

1. Check the log file: `{program_name}.log`
2. Verify the script path in `manager.yaml`
3. Ensure the venv exists and has required dependencies
4. Check file permissions

### Uploaded Program Installation Issues

**Status stuck on "installing":**
- Check the program logs for the current status
- Large dependencies may take several minutes to install
- Network issues can slow down pip install
- Installation timeout is 5 minutes - check logs for timeout errors

**Status shows "error":**
1. Click "Logs" to view detailed error messages
2. Common issues:
   - Invalid package names in `requirements.txt`
   - Python version incompatibility
   - Missing system dependencies for packages (e.g., gcc for compiled packages)
3. Fix the issue and re-upload or update the program

**Program starts then immediately crashes:**
- Check the script name matches exactly (case-sensitive)
- Verify the script is executable Python code
- Check for missing imports or syntax errors in logs
- Ensure `requirements.txt` includes all needed dependencies

### Manager Can't Connect to Running Process

The manager uses PID files to reconnect. If a process was killed externally:
1. The manager will detect it's gone
2. Start a new instance if enabled
3. Update the PID file

### Web UI Not Accessible

1. Check the configured port isn't already in use
2. Verify firewall settings allow the port
3. Check the host binding (`0.0.0.0` vs `127.0.0.1`)

### Modal Not Closing

If a modal doesn't close after submitting:
- Check browser console for JavaScript errors
- Ensure the server is responding (check terminal output)
- Try refreshing the page

## Dependencies

- **pyyaml** - YAML configuration parsing
- **psutil** - CPU monitoring (required for CPU monitoring)

Standard library only for core functionality!

## License

MIT License - feel free to use and modify for your projects.

## Contributing

Contributions welcome! This is a lightweight, single-file tool designed to be easy to understand and modify.
