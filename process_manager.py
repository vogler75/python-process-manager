#!/usr/bin/env python3
"""
Process Manager - Runs and monitors Python programs with a lightweight web UI.

Copyright (C) 2026 Andreas Vogler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import subprocess
import threading
import time
import signal
import sys
import os
import re
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import deque
import json
import yaml

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not installed, CPU monitoring disabled")

# Number of CPU history points to keep (at 1 sample per second = 60 seconds of history)
CPU_HISTORY_SIZE = 60


@dataclass
class ProcessInfo:
    name: str
    script: str
    enabled: bool = True
    venv_path: str = None  # Optional: program-specific venv path
    cwd: str = None  # Optional: working directory for the process
    args: list = None  # Optional: command-line arguments
    process: subprocess.Popen = None
    pid: int = None  # Store PID separately for persistence
    status: str = "stopped"
    consecutive_failures: int = 0
    is_broken: bool = False
    start_time: datetime = None
    last_restart: datetime = None
    total_restarts: int = 0
    _user_action_in_progress: bool = False  # Flag to prevent monitor interference during explicit actions
    cpu_history: deque = field(default_factory=lambda: deque(maxlen=CPU_HISTORY_SIZE))
    _psutil_process: object = None  # Cache psutil.Process object


class ProcessManager:
    def __init__(self, config_path: str = "process_manager.yaml"):
        self.base_dir = Path(__file__).parent.resolve()
        self.config_path = self.base_dir / config_path
        self.pid_file = self.base_dir / "process_manager.pids.json"
        self.processes: dict[str, ProcessInfo] = {}
        self.running = True
        self.lock = threading.Lock()
        self.config = {}
        self.venv_python = None  # Will be set in load_config()
        self.global_cwd = None  # Will be set in load_config()

        self.load_config()
        self.restore_processes()

    def load_config(self):
        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)

        self.restart_delay = self.config.get("restart", {}).get("delay_seconds", 1)
        self.max_failures = self.config.get("restart", {}).get("max_consecutive_failures", 10)
        self.failure_reset_seconds = self.config.get("restart", {}).get("failure_reset_seconds", 60)
        self.web_host = self.config.get("web_ui", {}).get("host", "0.0.0.0")
        self.web_port = self.config.get("web_ui", {}).get("port", 8080)
        self.web_title = self.config.get("web_ui", {}).get("title", "Process Manager")
        self.max_log_size_mb = self.config.get("logging", {}).get("max_size_mb", 10)

        # Load venv path from config
        venv_path = self.config.get("venv_path", ".venv")
        venv_path_obj = Path(venv_path)

        # If relative path, resolve relative to base_dir; otherwise use as-is
        if not venv_path_obj.is_absolute():
            venv_path_obj = self.base_dir / venv_path_obj

        self.venv_python = venv_path_obj / "bin" / "python"

        # Verify venv exists
        if not self.venv_python.exists():
            print(f"Warning: venv not found at {self.venv_python}")
            print(f"         Configure 'venv_path' in {self.config_path}")

        # Load global cwd from config (optional)
        global_cwd = self.config.get("cwd")
        if global_cwd:
            global_cwd_path = Path(global_cwd)
            if not global_cwd_path.is_absolute():
                global_cwd_path = self.base_dir / global_cwd_path
            self.global_cwd = global_cwd_path
        else:
            self.global_cwd = None

        for prog in self.config.get("programs", []):
            name = prog["name"]
            program_venv_path = prog.get("venv_path")  # Can be None
            program_cwd = prog.get("cwd")  # Can be None
            program_args = prog.get("args")  # Can be None or list
            # Ensure args is a list
            if program_args is not None and not isinstance(program_args, list):
                program_args = [str(program_args)]
            if name not in self.processes:
                self.processes[name] = ProcessInfo(
                    name=name,
                    script=prog["script"],
                    enabled=prog.get("enabled", True),
                    venv_path=program_venv_path,
                    cwd=program_cwd,
                    args=program_args
                )
            else:
                self.processes[name].script = prog["script"]
                self.processes[name].enabled = prog.get("enabled", True)
                self.processes[name].venv_path = program_venv_path
                self.processes[name].cwd = program_cwd
                self.processes[name].args = program_args

    def save_pids(self):
        """Save current process PIDs to file for persistence."""
        data = {}
        for name, info in self.processes.items():
            if info.pid and self.is_process_alive(info.pid):
                data[name] = {
                    "pid": info.pid,
                    "start_time": info.start_time.isoformat() if info.start_time else None,
                    "total_restarts": info.total_restarts
                }
        try:
            with open(self.pid_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save PID file: {e}")

    def restore_processes(self):
        """Restore process state from PID file and check if processes are still alive."""
        if not self.pid_file.exists():
            return

        try:
            with open(self.pid_file, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Failed to load PID file: {e}")
            return

        for name, saved in data.items():
            if name not in self.processes:
                continue

            pid = saved.get("pid")
            if pid and self.is_process_alive(pid):
                info = self.processes[name]
                info.pid = pid
                info.status = "running"
                if saved.get("start_time"):
                    try:
                        info.start_time = datetime.fromisoformat(saved["start_time"])
                    except:
                        info.start_time = datetime.now()
                else:
                    info.start_time = datetime.now()
                info.total_restarts = saved.get("total_restarts", 0)
                print(f"[{name}] Restored running process with PID {pid}")
            else:
                print(f"[{name}] Previous process (PID {pid}) is no longer running")

    def sanitize_filename(self, name: str) -> str:
        """Sanitize a name for use in filenames - replace spaces and special chars with underscore."""
        # Replace spaces and non-alphanumeric chars (except - and _) with underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        # Collapse multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        return sanitized.strip('_')

    def is_process_alive(self, pid: int) -> bool:
        """Check if a process with the given PID is still alive."""
        if pid is None:
            return False
        try:
            os.kill(pid, 0)  # Signal 0 doesn't kill, just checks if process exists
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # Process exists but we don't have permission (shouldn't happen for our own processes)
            return True

    def get_venv_python(self, info: ProcessInfo) -> Path:
        """Get the Python executable path for a process.
        Uses program-specific venv if set, otherwise falls back to global venv."""
        if info.venv_path:
            # Program has its own venv_path
            venv_path_obj = Path(info.venv_path)
            if not venv_path_obj.is_absolute():
                venv_path_obj = self.base_dir / venv_path_obj
            return venv_path_obj / "bin" / "python"
        else:
            # Use global venv
            return self.venv_python

    def collect_cpu_usage(self, info: ProcessInfo):
        """Collect CPU usage for a process and add to history."""
        if not PSUTIL_AVAILABLE:
            return

        pid = info.pid
        if not pid or not self.is_process_alive(pid):
            info._psutil_process = None
            info.cpu_history.append(0.0)
            return

        try:
            # Get or create psutil.Process object
            if info._psutil_process is None or info._psutil_process.pid != pid:
                info._psutil_process = psutil.Process(pid)

            # Get CPU percent (since last call, non-blocking)
            cpu_percent = info._psutil_process.cpu_percent(interval=None)
            info.cpu_history.append(cpu_percent)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            info._psutil_process = None
            info.cpu_history.append(0.0)

    def rotate_log_if_needed(self, info: ProcessInfo):
        """Check log file size and rotate if needed using copytruncate method.

        This copies the log to .log.1 and truncates the original file.
        The subprocess keeps writing to the same fd, now at position 0.
        """
        log_file = self.base_dir / f"{self.sanitize_filename(info.name)}.log"
        if not log_file.exists():
            return

        try:
            size_bytes = log_file.stat().st_size
            size_mb = size_bytes / (1024 * 1024)

            if size_mb < self.max_log_size_mb:
                return

            # Rotate: copy to .log.1 then truncate original
            backup_file = self.base_dir / f"{self.sanitize_filename(info.name)}.log.1"

            # Copy current log to backup (overwrites existing backup)
            shutil.copy2(log_file, backup_file)

            # Truncate the original file in place (keeps same inode/fd)
            os.truncate(log_file, 0)

            print(f"[{info.name}] Log rotated: {size_mb:.1f}MB -> {backup_file.name}")
        except Exception as e:
            print(f"[{info.name}] Failed to rotate log: {e}")

    def start_process(self, info: ProcessInfo):
        if info.is_broken:
            print(f"[{info.name}] Marked as broken, not starting")
            return

        if not info.enabled:
            print(f"[{info.name}] Disabled, not starting")
            return

        # Determine working directory: program cwd > global cwd > base_dir
        if info.cwd:
            cwd_path = Path(info.cwd)
            if not cwd_path.is_absolute():
                cwd_path = self.base_dir / cwd_path
            work_dir = cwd_path
        elif self.global_cwd:
            work_dir = self.global_cwd
        else:
            work_dir = self.base_dir

        # Resolve script path relative to cwd (if set) or base_dir
        script_path = work_dir / info.script
        if not script_path.exists():
            print(f"[{info.name}] Script not found: {script_path}")
            info.status = "error"
            return

        log_file = self.base_dir / f"{self.sanitize_filename(info.name)}.log"
        venv_python = self.get_venv_python(info)

        # Build command with optional arguments
        cmd = [str(venv_python), str(script_path)]
        if info.args:
            cmd.extend([str(arg) for arg in info.args])

        try:
            with open(log_file, "a") as log:
                info.process = subprocess.Popen(
                    cmd,
                    cwd=work_dir,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
            info.pid = info.process.pid
            info.status = "running"
            info.start_time = datetime.now()
            print(f"[{info.name}] Started with PID {info.process.pid} using {venv_python}")
            self.save_pids()  # Persist PIDs after starting
        except Exception as e:
            print(f"[{info.name}] Failed to start: {e}")
            info.status = "error"

    def stop_process(self, info: ProcessInfo):
        pid_to_stop = info.process.pid if info.process else info.pid

        if pid_to_stop and self.is_process_alive(pid_to_stop):
            info.status = "stopping"  # Show stopping status while waiting
            try:
                os.killpg(os.getpgid(pid_to_stop), signal.SIGTERM)
                # Wait for process to terminate
                for _ in range(50):  # 5 seconds max
                    if not self.is_process_alive(pid_to_stop):
                        break
                    time.sleep(0.1)
                else:
                    # Force kill if still alive
                    try:
                        os.killpg(os.getpgid(pid_to_stop), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            except ProcessLookupError:
                pass

        info.process = None
        info.pid = None
        info.status = "stopped"
        self.save_pids()  # Update PID file after stopping

    def monitor_processes(self):
        while self.running:
            with self.lock:
                for info in self.processes.values():
                    if not info.enabled or info.is_broken:
                        continue

                    # Check if process is running (either via Popen or restored PID)
                    is_running = False
                    if info.process is not None:
                        # We have a Popen object, use poll()
                        retcode = info.process.poll()
                        is_running = (retcode is None)
                    elif info.pid is not None:
                        # Restored process, check by PID
                        is_running = self.is_process_alive(info.pid)

                    if not is_running and (info.process is not None or info.pid is not None):
                        # Skip if a user-initiated action (stop/restart) is in progress
                        if info._user_action_in_progress:
                            continue

                        # Process died
                        print(f"[{info.name}] Process died (PID {info.pid})")
                        info.status = "restarting"
                        info.consecutive_failures += 1
                        info.total_restarts += 1
                        info.last_restart = datetime.now()
                        info.process = None
                        info.pid = None

                        if info.consecutive_failures >= self.max_failures:
                            print(f"[{info.name}] Marked as BROKEN after {self.max_failures} consecutive failures")
                            info.is_broken = True
                            info.status = "broken"
                            self.save_pids()
                            continue

                        print(f"[{info.name}] Restarting in {self.restart_delay}s (failure {info.consecutive_failures}/{self.max_failures})")
                        time.sleep(self.restart_delay)
                        self.start_process(info)
                    elif is_running:
                        # Process is running fine - reset failures only after stable period
                        if info.start_time and info.consecutive_failures > 0:
                            uptime_seconds = (datetime.now() - info.start_time).total_seconds()
                            if uptime_seconds >= self.failure_reset_seconds:
                                info.consecutive_failures = 0
                    elif not info._user_action_in_progress:
                        # No process running and no user action in progress, need to start
                        self.start_process(info)

                # Collect CPU usage and check log rotation for all processes
                for info in self.processes.values():
                    self.collect_cpu_usage(info)
                    self.rotate_log_if_needed(info)

            time.sleep(1)

    def get_status(self) -> list[dict]:
        status = []
        with self.lock:
            for info in self.processes.values():
                pid = info.pid  # Use stored PID (works for both Popen and restored processes)
                uptime = None
                if info.start_time and info.status == "running":
                    uptime = str(datetime.now() - info.start_time).split(".")[0]

                # Get log file size
                log_file = self.base_dir / f"{self.sanitize_filename(info.name)}.log"
                log_size = None
                log_size_display = None
                if log_file.exists():
                    log_size = log_file.stat().st_size
                    if log_size < 1024:
                        log_size_display = f"{log_size} B"
                    elif log_size < 1024 * 1024:
                        log_size_display = f"{log_size / 1024:.1f} KB"
                    else:
                        log_size_display = f"{log_size / (1024 * 1024):.1f} MB"

                # Get CPU data
                cpu_history = list(info.cpu_history)
                cpu_current = cpu_history[-1] if cpu_history else 0.0

                status.append({
                    "name": info.name,
                    "script": info.script,
                    "enabled": info.enabled,
                    "status": info.status,
                    "pid": pid,
                    "uptime": uptime,
                    "consecutive_failures": info.consecutive_failures,
                    "total_restarts": info.total_restarts,
                    "is_broken": info.is_broken,
                    "last_restart": info.last_restart.isoformat() if info.last_restart else None,
                    "log_size": log_size,
                    "log_size_display": log_size_display,
                    "cpu_current": round(cpu_current, 1),
                    "cpu_history": [round(x, 1) for x in cpu_history]
                })
        return status

    def restart_program(self, name: str) -> bool:
        with self.lock:
            if name in self.processes:
                info = self.processes[name]
                if info.status == "stopping" or info.status == "restarting":
                    return True  # Already in progress
                info.status = "restarting"
                info._user_action_in_progress = True  # Prevent monitor interference
                # Run actual restart in background thread
                threading.Thread(
                    target=self._restart_process_async,
                    args=(info,),
                    daemon=True
                ).start()
                return True
        return False

    def _restart_process_async(self, info: ProcessInfo):
        """Restart process in background thread."""
        pid_to_stop = info.process.pid if info.process else info.pid

        if pid_to_stop and self.is_process_alive(pid_to_stop):
            try:
                os.killpg(os.getpgid(pid_to_stop), signal.SIGTERM)
                for _ in range(50):
                    if not self.is_process_alive(pid_to_stop):
                        break
                    time.sleep(0.1)
                else:
                    try:
                        os.killpg(os.getpgid(pid_to_stop), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            except ProcessLookupError:
                pass

        with self.lock:
            info.process = None
            info.pid = None
            info.is_broken = False
            info.consecutive_failures = 0

        time.sleep(self.restart_delay)

        with self.lock:
            self.start_process(info)
            info._user_action_in_progress = False  # Clear flag to allow monitor to resume

    def stop_program(self, name: str) -> bool:
        with self.lock:
            if name in self.processes:
                info = self.processes[name]
                if info.status == "stopping":
                    return True  # Already stopping
                info.enabled = False
                info.status = "stopping"
                info._user_action_in_progress = True  # Prevent monitor interference
                # Run actual stop in background thread
                threading.Thread(
                    target=self._stop_process_async,
                    args=(info,),
                    daemon=True
                ).start()
                return True
        return False

    def _stop_process_async(self, info: ProcessInfo):
        """Stop process in background thread."""
        pid_to_stop = info.process.pid if info.process else info.pid

        if pid_to_stop and self.is_process_alive(pid_to_stop):
            try:
                os.killpg(os.getpgid(pid_to_stop), signal.SIGTERM)
                # Wait for process to terminate
                for _ in range(50):  # 5 seconds max
                    if not self.is_process_alive(pid_to_stop):
                        break
                    time.sleep(0.1)
                else:
                    # Force kill if still alive
                    try:
                        os.killpg(os.getpgid(pid_to_stop), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            except ProcessLookupError:
                pass

        with self.lock:
            info.process = None
            info.pid = None
            info.status = "stopped"
            info._user_action_in_progress = False  # Clear flag to allow monitor to resume
            self.save_pids()

    def start_program(self, name: str) -> bool:
        with self.lock:
            if name in self.processes:
                info = self.processes[name]
                info.enabled = True
                info.is_broken = False
                info.consecutive_failures = 0
                self.start_process(info)
                return True
        return False

    def get_log_content(self, name: str, lines: int = 100, offset: int = 0) -> dict:
        """Get log content for a process using tail-like behavior."""
        if name not in self.processes:
            return {"error": "Process not found", "content": None}

        log_file = self.base_dir / f"{self.sanitize_filename(name)}.log"
        if not log_file.exists():
            return {"error": "Log file not found", "content": None, "total_lines": 0}

        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)

            # Calculate start position for tail with offset
            # offset=0 means last 'lines' lines, offset=100 means 100 lines before that, etc.
            end_pos = total_lines - offset
            start_pos = max(0, end_pos - lines)
            end_pos = max(0, end_pos)

            selected_lines = all_lines[start_pos:end_pos]

            return {
                "content": "".join(selected_lines),
                "total_lines": total_lines,
                "start_line": start_pos + 1,
                "end_line": end_pos,
                "has_more": start_pos > 0
            }
        except Exception as e:
            return {"error": str(e), "content": None}

    def shutdown(self):
        """Shutdown the process manager without stopping managed processes."""
        print("\nShutting down process manager...")
        self.running = False
        with self.lock:
            self.save_pids()  # Save current state for next startup
        print("Process manager stopped. Managed processes continue running.")


class WebHandler(BaseHTTPRequestHandler):
    manager: ProcessManager = None

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.get_html(self.manager.web_title).encode())
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.manager.get_status()).encode())
        elif self.path.startswith("/api/logs/"):
            # Parse: /api/logs/{name}?lines=100&offset=0
            from urllib.parse import urlparse, parse_qs, unquote
            parsed = urlparse(self.path)
            parts = parsed.path.split("/")
            if len(parts) >= 4:
                name = unquote(parts[3])  # Decode URL-encoded name
                params = parse_qs(parsed.query)
                lines = int(params.get("lines", [100])[0])
                offset = int(params.get("offset", [0])[0])

                result = self.manager.get_log_content(name, lines, offset)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            else:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith("/api/"):
            from urllib.parse import unquote
            parts = self.path.split("/")
            if len(parts) >= 4:
                action = parts[2]
                name = unquote(parts[3])  # Decode URL-encoded name (e.g., spaces)

                success = False
                if action == "restart":
                    success = self.manager.restart_program(name)
                elif action == "stop":
                    success = self.manager.stop_program(name)
                elif action == "start":
                    success = self.manager.start_program(name)

                self.send_response(200 if success else 404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": success}).encode())
                return

        self.send_response(404)
        self.end_headers()

    def get_html(self, title: str = "Process Manager") -> str:
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Process Manager - {{TITLE}}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
            background-attachment: fixed;
            color: #eee;
            padding: 20px;
            min-height: 100vh;
        }

        /* Main Frame */
        .container {
            max-width: 950px;
            margin: 0 auto;
            background: rgba(22, 33, 62, 0.6);
            border-radius: 16px;
            border: 1px solid rgba(0, 212, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 60px rgba(0, 212, 255, 0.1);
            backdrop-filter: blur(10px);
            overflow: hidden;
        }

        /* Header */
        .header {
            background: linear-gradient(90deg, rgba(0, 212, 255, 0.15) 0%, rgba(0, 212, 255, 0.05) 100%);
            padding: 20px 25px;
            border-bottom: 1px solid rgba(0, 212, 255, 0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            color: #00d4ff;
            font-size: 1.5em;
            text-shadow: 0 0 20px rgba(0, 212, 255, 0.4);
            margin: 0;
        }
        .header-subtitle {
            color: #888;
            font-size: 0.85em;
        }
        .header-status {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #4caf50;
            font-size: 0.85em;
        }
        .header-status .dot {
            width: 8px;
            height: 8px;
            background: #4caf50;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        .header-status.warning { color: #ff9800; }
        .header-status.warning .dot { background: #ff9800; animation: pulse-warning 2s infinite; }
        .header-status.error { color: #f44336; }
        .header-status.error .dot { background: #f44336; animation: pulse-error 2s infinite; }
        @keyframes pulse {
            0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.4); }
            50% { opacity: 0.8; box-shadow: 0 0 0 6px rgba(76, 175, 80, 0); }
        }
        @keyframes pulse-warning {
            0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(255, 152, 0, 0.4); }
            50% { opacity: 0.8; box-shadow: 0 0 0 6px rgba(255, 152, 0, 0); }
        }
        @keyframes pulse-error {
            0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.4); }
            50% { opacity: 0.8; box-shadow: 0 0 0 6px rgba(244, 67, 54, 0); }
        }

        /* Process List */
        .process-list {
            padding: 20px;
        }
        .process {
            background: rgba(13, 20, 33, 0.6);
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.2s ease;
        }
        .process:hover {
            background: rgba(13, 20, 33, 0.8);
            border-color: rgba(0, 212, 255, 0.2);
            transform: translateY(-1px);
        }
        .process-info { flex: 1; min-width: 200px; }
        .process-name { font-weight: 600; font-size: 1.1em; color: #fff; }
        .process-script { color: #666; font-size: 0.85em; margin-top: 2px; }
        .process-meta { font-size: 0.8em; color: #888; margin-top: 6px; }

        /* Status Badges */
        .status {
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .status.running { background: rgba(76, 175, 80, 0.2); color: #4caf50; border: 1px solid rgba(76, 175, 80, 0.3); }
        .status.stopped { background: rgba(244, 67, 54, 0.2); color: #f44336; border: 1px solid rgba(244, 67, 54, 0.3); }
        .status.stopping { background: rgba(255, 152, 0, 0.2); color: #ff9800; border: 1px solid rgba(255, 152, 0, 0.3); }
        .status.broken { background: rgba(244, 67, 54, 0.2); color: #f44336; border: 1px solid rgba(244, 67, 54, 0.3); }
        .status.restarting { background: rgba(33, 150, 243, 0.2); color: #2196f3; border: 1px solid rgba(33, 150, 243, 0.3); }
        .status.error { background: rgba(255, 152, 0, 0.2); color: #ff9800; border: 1px solid rgba(255, 152, 0, 0.3); }

        /* Buttons */
        .actions { display: flex; gap: 8px; flex-wrap: wrap; }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85em;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); }
        .btn:active { transform: translateY(0); }
        .btn:disabled { background: #444; cursor: not-allowed; opacity: 0.5; transform: none; box-shadow: none; }
        .btn-start { background: linear-gradient(135deg, #4caf50, #45a049); color: white; }
        .btn-stop { background: linear-gradient(135deg, #f44336, #d32f2f); color: white; }
        .btn-restart { background: linear-gradient(135deg, #2196f3, #1976d2); color: white; }
        .btn-logs { background: linear-gradient(135deg, #9c27b0, #7b1fa2); color: white; }

        /* Footer */
        .footer {
            padding: 15px 25px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            color: #666;
            font-size: 0.8em;
            text-align: center;
        }

        .log-size { color: #666; font-size: 0.75em; margin-left: 8px; }

        /* CPU Chart Styles */
        .cpu-container { display: flex; align-items: center; gap: 10px; min-width: 150px; }
        .cpu-chart {
            width: 80px;
            height: 28px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .cpu-chart svg { display: block; }
        .cpu-value { font-size: 0.9em; color: #4caf50; font-weight: 600; min-width: 50px; text-align: right; }

        /* Log Modal Styles */
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 1000; backdrop-filter: blur(4px); }
        .modal-overlay.active { display: flex; justify-content: center; align-items: center; }
        .modal {
            background: rgba(22, 33, 62, 0.95);
            border-radius: 16px;
            width: 90%;
            max-width: 1200px;
            height: 80vh;
            display: flex;
            flex-direction: column;
            border: 1px solid rgba(0, 212, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 60px rgba(0, 212, 255, 0.1);
        }
        .modal-header {
            padding: 18px 25px;
            border-bottom: 1px solid rgba(0, 212, 255, 0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(90deg, rgba(0, 212, 255, 0.1) 0%, transparent 100%);
        }
        .modal-header h2 { color: #00d4ff; font-size: 1.2em; text-shadow: 0 0 20px rgba(0, 212, 255, 0.3); }
        .modal-close { background: linear-gradient(135deg, #f44336, #d32f2f); color: white; border: none; padding: 8px 18px; border-radius: 6px; cursor: pointer; font-size: 0.9em; font-weight: 500; transition: all 0.2s; }
        .modal-close:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(244, 67, 54, 0.4); }
        .modal-controls { padding: 12px 25px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); display: flex; gap: 10px; align-items: center; flex-wrap: wrap; background: rgba(0, 0, 0, 0.2); }
        .modal-controls button { padding: 7px 14px; border: none; border-radius: 5px; cursor: pointer; font-size: 0.85em; font-weight: 500; transition: all 0.2s; }
        .modal-controls button:hover { transform: translateY(-1px); }
        .modal-controls .nav-btn { background: linear-gradient(135deg, #2196f3, #1976d2); color: white; }
        .modal-controls .nav-btn:disabled { background: #444; cursor: not-allowed; transform: none; }
        .modal-controls .refresh-btn { background: linear-gradient(135deg, #4caf50, #45a049); color: white; }
        .modal-controls .tail-btn { background: linear-gradient(135deg, #ff9800, #f57c00); color: white; }
        .modal-controls .tail-btn.active { background: linear-gradient(135deg, #e65100, #bf360c); }
        .modal-info { color: #888; font-size: 0.85em; margin-left: auto; }
        .modal-body { flex: 1; overflow: auto; padding: 0; }
        .log-content { font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace; font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-wrap: break-word; padding: 20px; margin: 0; background: rgba(13, 20, 33, 0.8); color: #e0e0e0; min-height: 100%; }
        .log-loading { color: #888; padding: 20px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Process Manager</h1>
                <span class="header-subtitle">{{TITLE}}</span>
            </div>
            <div class="header-status" id="headerStatus">
                <span class="dot"></span>
                <span>Loading...</span>
            </div>
        </div>
        <div class="process-list" id="processes"></div>
        <div class="footer">
            Auto-refreshes every 2 seconds
        </div>
    </div>

    <!-- Log Viewer Modal -->
    <div id="logModal" class="modal-overlay">
        <div class="modal">
            <div class="modal-header">
                <h2 id="logModalTitle">Logs</h2>
                <button class="modal-close" onclick="closeLogModal()">Close</button>
            </div>
            <div class="modal-controls">
                <button class="nav-btn" id="btnOlder" onclick="loadOlder()">Older</button>
                <button class="nav-btn" id="btnNewer" onclick="loadNewer()">Newer</button>
                <button class="refresh-btn" onclick="refreshLogs()">Refresh</button>
                <button class="tail-btn" id="btnTail" onclick="toggleTail()">Auto-refresh: OFF</button>
                <span class="modal-info" id="logInfo"></span>
            </div>
            <div class="modal-body">
                <pre class="log-content" id="logContent"></pre>
            </div>
        </div>
    </div>

    <script>
        let currentLogProcess = null;
        let currentOffset = 0;
        let linesPerPage = 200;
        let totalLines = 0;
        let tailInterval = null;

        function renderSparkline(data) {
            if (!data || data.length === 0) {
                return '<svg width="80" height="24"></svg>';
            }

            const width = 80;
            const height = 24;
            const padding = 2;
            const maxVal = Math.max(...data, 10); // At least 10% scale for visibility

            // Take last 30 points for display (30 seconds of history)
            const displayData = data.slice(-30);
            const stepX = (width - padding * 2) / Math.max(displayData.length - 1, 1);

            // Generate path points
            const points = displayData.map((val, i) => {
                const x = padding + i * stepX;
                const y = height - padding - ((val / maxVal) * (height - padding * 2));
                return `${x},${y}`;
            }).join(' ');

            // Color based on average CPU usage
            const avg = displayData.reduce((a, b) => a + b, 0) / displayData.length;
            let color = '#4caf50'; // Green
            if (avg > 50) color = '#ff9800'; // Orange
            if (avg > 80) color = '#f44336'; // Red

            return `<svg width="${width}" height="${height}">
                <polyline fill="none" stroke="${color}" stroke-width="1.5" points="${points}"/>
            </svg>`;
        }

        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                render(data);
            } catch (e) {
                console.error('Failed to fetch status:', e);
            }
        }

        function render(processes) {
            const container = document.getElementById('processes');
            container.innerHTML = processes.map(p => `
                <div class="process">
                    <div class="process-info">
                        <div class="process-name">${p.name}${p.log_size_display ? `<span class="log-size">(Log: ${p.log_size_display})</span>` : ''}</div>
                        <div class="process-script">${p.script}</div>
                        <div class="process-meta">
                            ${p.pid ? `PID: ${p.pid}` : ''}
                            ${p.uptime ? ` | Uptime: ${p.uptime}` : ''}
                            ${p.total_restarts ? ` | Restarts: ${p.total_restarts}` : ''}
                            ${p.is_broken ? ` | Failures: ${p.consecutive_failures}` : ''}
                        </div>
                    </div>
                    <div class="cpu-container">
                        <div class="cpu-chart">${renderSparkline(p.cpu_history)}</div>
                        <span class="cpu-value">${p.cpu_current.toFixed(1)}%</span>
                    </div>
                    <span class="status ${p.status}">${p.status}</span>
                    <div class="actions">
                        ${p.status === 'stopped' || p.is_broken ?
                            `<button class="btn btn-start" onclick="action('start', '${p.name}')">Start</button>` :
                            `<button class="btn btn-stop" onclick="action('stop', '${p.name}')" ${p.status === 'stopping' ? 'disabled' : ''}>Stop</button>`}
                        <button class="btn btn-restart" onclick="action('restart', '${p.name}')" ${p.status === 'stopping' || p.status === 'restarting' ? 'disabled' : ''}>Restart</button>
                        <button class="btn btn-logs" onclick="openLogModal('${p.name}')">Logs</button>
                    </div>
                </div>
            `).join('');

            // Update header status
            updateHeaderStatus(processes);
        }

        function updateHeaderStatus(processes) {
            const header = document.getElementById('headerStatus');
            const total = processes.length;
            const running = processes.filter(p => p.status === 'running').length;
            const broken = processes.filter(p => p.is_broken).length;

            let statusClass = '';
            let statusText = '';

            if (broken > 0) {
                statusClass = 'error';
                statusText = `${broken} Broken`;
            } else if (running === total && total > 0) {
                statusClass = '';
                statusText = `All Running (${running}/${total})`;
            } else if (running > 0) {
                statusClass = 'warning';
                statusText = `${running}/${total} Running`;
            } else {
                statusClass = 'error';
                statusText = 'All Stopped';
            }

            header.className = 'header-status ' + statusClass;
            header.innerHTML = `<span class="dot"></span><span>${statusText}</span>`;
        }

        async function action(type, name) {
            await fetch(`/api/${type}/${encodeURIComponent(name)}`, { method: 'POST' });
            fetchStatus();
        }

        function openLogModal(name) {
            currentLogProcess = name;
            currentOffset = 0;
            document.getElementById('logModal').classList.add('active');
            document.getElementById('logModalTitle').textContent = `Logs: ${name}`;
            loadLogs();
        }

        function closeLogModal() {
            document.getElementById('logModal').classList.remove('active');
            currentLogProcess = null;
            stopTail();
        }

        async function loadLogs() {
            const content = document.getElementById('logContent');
            const info = document.getElementById('logInfo');
            content.textContent = 'Loading...';

            try {
                const res = await fetch(`/api/logs/${encodeURIComponent(currentLogProcess)}?lines=${linesPerPage}&offset=${currentOffset}`);
                const data = await res.json();

                if (data.error) {
                    content.textContent = `Error: ${data.error}`;
                    return;
                }

                totalLines = data.total_lines;
                content.textContent = data.content || '(empty log)';
                info.textContent = `Lines ${data.start_line}-${data.end_line} of ${data.total_lines}`;

                document.getElementById('btnOlder').disabled = !data.has_more;
                document.getElementById('btnNewer').disabled = currentOffset === 0;

                // Scroll to bottom when viewing latest logs
                if (currentOffset === 0) {
                    const body = document.querySelector('.modal-body');
                    body.scrollTop = body.scrollHeight;
                }
            } catch (e) {
                content.textContent = `Failed to load logs: ${e.message}`;
            }
        }

        function loadOlder() {
            currentOffset += linesPerPage;
            if (currentOffset > totalLines - linesPerPage) {
                currentOffset = Math.max(0, totalLines - linesPerPage);
            }
            loadLogs();
        }

        function loadNewer() {
            currentOffset -= linesPerPage;
            if (currentOffset < 0) currentOffset = 0;
            loadLogs();
        }

        function refreshLogs() {
            currentOffset = 0;
            loadLogs();
        }

        function toggleTail() {
            const btn = document.getElementById('btnTail');
            if (tailInterval) {
                stopTail();
            } else {
                tailInterval = setInterval(() => {
                    if (currentOffset === 0) {
                        loadLogs();
                    }
                }, 2000);
                btn.textContent = 'Auto-refresh: ON';
                btn.classList.add('active');
            }
        }

        function stopTail() {
            if (tailInterval) {
                clearInterval(tailInterval);
                tailInterval = null;
            }
            const btn = document.getElementById('btnTail');
            btn.textContent = 'Auto-refresh: OFF';
            btn.classList.remove('active');
        }

        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && document.getElementById('logModal').classList.contains('active')) {
                closeLogModal();
            }
        });

        fetchStatus();
        setInterval(fetchStatus, 2000);
    </script>
</body>
</html>"""
        return html.replace("{{TITLE}}", title)


def main():
    manager = ProcessManager()
    WebHandler.manager = manager

    def signal_handler(sig, frame):
        manager.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    monitor_thread = threading.Thread(target=manager.monitor_processes, daemon=True)
    monitor_thread.start()

    server = HTTPServer((manager.web_host, manager.web_port), WebHandler)
    print(f"Process Manager started")
    print(f"Web UI available at http://{manager.web_host}:{manager.web_port}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        manager.shutdown()


if __name__ == "__main__":
    main()
