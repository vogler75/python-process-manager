# Python Process Manager

A lightweight, self-contained process manager for Python applications with a beautiful web UI. Monitor, control, and view logs of multiple Python programs from a single dashboard.

## Features

- **Web-based Dashboard** - Modern, responsive UI with real-time status updates
- **Process Monitoring** - Automatic restart on failures with configurable retry limits
- **CPU Monitoring** - Real-time CPU usage tracking with sparkline charts (requires psutil)
- **Log Management** - Automatic log rotation with built-in log viewer
- **Persistent State** - Processes survive manager restarts
- **Virtual Environment Support** - Global or per-program venv configuration
- **Zero Dependencies UI** - No external JavaScript frameworks, pure HTML/CSS/JS
- **Graceful Shutdown** - Manager stops without killing managed processes

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

## Configuration

Edit `process_manager.yaml` to configure your setup:

```yaml
# Web UI settings
web_ui:
  host: "0.0.0.0"      # Bind address (0.0.0.0 for all interfaces)
  port: 10000          # Web UI port
  title: "My Services" # Custom title for the dashboard

# Python Virtual Environment
venv_path: ".venv"     # Path to venv (relative or absolute)

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
    # venv_path: ".venv"  # Optional: program-specific venv
```

### Configuration Options

#### Web UI
- `host` - Network interface to bind (use `127.0.0.1` for localhost only)
- `port` - HTTP port for the web interface
- `title` - Custom title displayed in the dashboard

#### Virtual Environment
- `venv_path` - Global Python venv path (default: `.venv`)
- Per-program `venv_path` - Override global venv for specific programs

#### Restart Behavior
- `delay_seconds` - Delay before restarting a failed process
- `max_consecutive_failures` - Maximum failures before marking as broken
- `failure_reset_seconds` - Stable runtime required to reset failure counter

#### Logging
- `max_size_mb` - Maximum log file size before rotation (copytruncate method)

#### Programs
- `name` - Display name in the UI
- `script` - Python script path (relative to config file)
- `enabled` - Auto-start on manager launch (default: true)
- `venv_path` - Optional per-program venv override

## Usage

### Starting the Manager

```bash
python3 process_manager.py
```

The manager will:
1. Load configuration from `process_manager.yaml`
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
- **Restarting** (Blue) - Automatic restart in progress
- **Stopping** (Orange) - Shutdown in progress
- **Broken** (Red) - Too many consecutive failures, auto-restart disabled

### Log Viewer

- **Pagination** - Navigate through large log files
- **Auto-refresh** - Toggle live tail mode
- **File Info** - Shows line ranges and total size
- **Keyboard Shortcuts** - Press `Esc` to close modal

## Process Management

### Automatic Restart

Processes are automatically restarted when they crash. The failure counter resets after running successfully for `failure_reset_seconds`.

### Broken State

After `max_consecutive_failures`, a process is marked as **broken** and auto-restart is disabled. Use the **Restart** button to manually reset and restart.

### Log Rotation

When a log file exceeds `max_size_mb`, it's copied to `{name}.log.1` and truncated. This uses the copytruncate method, so processes keep writing without interruption.

### Process Persistence

Process IDs are saved to `process_manager.pids.json`. When the manager restarts:
- It checks if processes are still running
- Reconnects to running processes
- Starts stopped processes if enabled

## File Structure

```
.
├── process_manager.py          # Main application
├── process_manager.yaml        # Configuration file
├── requirements.txt            # Python dependencies
├── process_manager.pids.json   # Saved process states (auto-generated)
├── {program_name}.log          # Process log files (auto-generated)
└── {program_name}.log.1        # Rotated log files (auto-generated)
```

## Advanced Usage

### Custom Virtual Environments

Use different Python environments for different programs:

```yaml
programs:
  - name: "Legacy App"
    script: old_app.py
    venv_path: ".venv-python37"  # Python 3.7 environment

  - name: "Modern App"
    script: new_app.py
    venv_path: ".venv-python311" # Python 3.11 environment
```

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
ExecStart=/path/to/.venv/bin/python process_manager.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable process-manager
sudo systemctl start process-manager
```

#### Using screen/tmux

```bash
screen -dmS process-manager python3 process_manager.py
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
2. Verify the script path in `process_manager.yaml`
3. Ensure the venv exists and has required dependencies
4. Check file permissions

### Manager Can't Connect to Running Process

The manager uses PID files to reconnect. If a process was killed externally:
1. The manager will detect it's gone
2. Start a new instance if enabled
3. Update the PID file

### Web UI Not Accessible

1. Check the configured port isn't already in use
2. Verify firewall settings allow the port
3. Check the host binding (`0.0.0.0` vs `127.0.0.1`)

## Dependencies

- **pyyaml** - YAML configuration parsing
- **psutil** - CPU monitoring (optional, degrades gracefully if missing)

Standard library only for core functionality!

## License

MIT License - feel free to use and modify for your projects.

## Contributing

Contributions welcome! This is a lightweight, single-file tool designed to be easy to understand and modify.
