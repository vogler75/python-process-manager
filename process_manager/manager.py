"""
Process Manager - Core process lifecycle and monitoring logic.

Copyright (C) 2025 Andreas Vogler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import subprocess
import threading
import time
import signal
import sys
import os
import re
import shutil
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime
import json
import yaml

from .models import ProcessInfo

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not installed, CPU monitoring disabled")

# Constants for uploaded programs
UPLOADED_PROGRAMS_DIR = "uploaded_programs"
MAX_UPLOAD_SIZE_MB = 50


class ProcessManager:
    def __init__(self, config_path: str = "process_manager.yaml"):
        self.base_dir = Path(__file__).parent.parent.resolve()
        self.config_path = self.base_dir / config_path
        self.uploaded_config_path = self.base_dir / "uploaded_programs.yaml"
        self.pid_file = self.base_dir / "process_manager.pids.json"
        self.uploaded_dir = self.base_dir / UPLOADED_PROGRAMS_DIR
        self.log_dir = self.base_dir / "log"
        self.processes: dict[str, ProcessInfo] = {}
        self.running = True
        self.lock = threading.Lock()
        self.config = {}
        self.uploaded_config = {}
        self.venv_python = None  # Will be set in load_config()
        self.global_cwd = None  # Will be set in load_config()

        # Create uploaded programs directory if it doesn't exist
        self.uploaded_dir.mkdir(exist_ok=True)
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(exist_ok=True)

        self.load_config()
        self.restore_processes()

    def reload_config(self) -> dict:
        """Reload configuration from disk without restarting processes.
        Returns: {"success": bool, "message": str}
        """
        with self.lock:
            try:
                # Re-load the configuration
                self.load_config()
                return {"success": True, "message": "Configuration reloaded successfully"}
            except Exception as e:
                return {"success": False, "message": f"Failed to reload configuration: {str(e)}"}

    def load_config(self):
        # Load main configuration
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

        # Load uploaded programs configuration (may not exist yet)
        if self.uploaded_config_path.exists():
            with open(self.uploaded_config_path) as f:
                self.uploaded_config = yaml.safe_load(f) or {}
        else:
            self.uploaded_config = {}

        # Load manual programs from main config
        for prog in self.config.get("programs", []):
            name = prog["name"]
            program_venv_path = prog.get("venv_path")
            program_cwd = prog.get("cwd")
            program_args = prog.get("args")
            program_environment = prog.get("environment")
            # Ensure args is a list
            if program_args is not None and not isinstance(program_args, list):
                program_args = [str(program_args)]
            # Ensure environment is a list
            if program_environment is not None and not isinstance(program_environment, list):
                program_environment = [str(program_environment)]
            if name not in self.processes:
                self.processes[name] = ProcessInfo(
                    name=name,
                    script=prog["script"],
                    enabled=prog.get("enabled", True),
                    uploaded=False,  # Manual programs are not uploaded
                    venv_path=program_venv_path,
                    cwd=program_cwd,
                    args=program_args,
                    environment=program_environment
                )
            else:
                self.processes[name].script = prog["script"]
                self.processes[name].enabled = prog.get("enabled", True)
                self.processes[name].uploaded = False
                self.processes[name].venv_path = program_venv_path
                self.processes[name].cwd = program_cwd
                self.processes[name].args = program_args
                self.processes[name].environment = program_environment

        # Load uploaded programs from uploaded_programs.yaml
        for prog in self.uploaded_config.get("programs", []):
            name = prog["name"]
            program_venv_path = prog.get("venv_path")
            program_cwd = prog.get("cwd")
            program_args = prog.get("args")
            program_environment = prog.get("environment")
            # Ensure args is a list
            if program_args is not None and not isinstance(program_args, list):
                program_args = [str(program_args)]
            # Ensure environment is a list
            if program_environment is not None and not isinstance(program_environment, list):
                program_environment = [str(program_environment)]
            if name not in self.processes:
                self.processes[name] = ProcessInfo(
                    name=name,
                    script=prog["script"],
                    enabled=prog.get("enabled", True),
                    uploaded=True,  # All programs from uploaded config are uploaded
                    venv_path=program_venv_path,
                    cwd=program_cwd,
                    args=program_args,
                    environment=program_environment
                )
            else:
                # Update existing process (shouldn't happen, but handle it)
                self.processes[name].script = prog["script"]
                self.processes[name].enabled = prog.get("enabled", True)
                self.processes[name].uploaded = True
                self.processes[name].venv_path = program_venv_path
                self.processes[name].cwd = program_cwd
                self.processes[name].args = program_args
                self.processes[name].environment = program_environment

    def save_config(self):
        """Save manual (non-uploaded) programs to main config file."""
        programs_config = []
        with self.lock:
            for info in self.processes.values():
                # Skip uploaded programs - they go in uploaded_programs.yaml
                if info.uploaded:
                    continue

                prog = {
                    "name": info.name,
                    "script": info.script,
                    "enabled": info.enabled,
                }
                if info.venv_path:
                    prog["venv_path"] = info.venv_path
                if info.cwd:
                    prog["cwd"] = info.cwd
                if info.args:
                    prog["args"] = info.args
                if info.environment:
                    prog["environment"] = info.environment
                programs_config.append(prog)

        self.config["programs"] = programs_config

        try:
            with open(self.config_path, "w") as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            print(f"Failed to save config: {e}")
            raise

    def save_uploaded_config(self):
        """Save uploaded programs to uploaded_programs.yaml."""
        programs_config = []
        with self.lock:
            for info in self.processes.values():
                # Only save uploaded programs
                if not info.uploaded:
                    continue

                prog = {
                    "name": info.name,
                    "script": info.script,
                    "enabled": info.enabled,
                }
                if info.venv_path:
                    prog["venv_path"] = info.venv_path
                if info.cwd:
                    prog["cwd"] = info.cwd
                if info.args:
                    prog["args"] = info.args
                if info.environment:
                    prog["environment"] = info.environment
                programs_config.append(prog)

        self.uploaded_config["programs"] = programs_config

        try:
            with open(self.uploaded_config_path, "w") as f:
                yaml.dump(self.uploaded_config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            print(f"Failed to save uploaded config: {e}")
            raise

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
        log_file = self.log_dir / f"{self.sanitize_filename(info.name)}.log"
        if not log_file.exists():
            return

        try:
            size_bytes = log_file.stat().st_size
            size_mb = size_bytes / (1024 * 1024)

            if size_mb < self.max_log_size_mb:
                return

            # Rotate: copy to .log.1 then truncate original
            backup_file = self.log_dir / f"{self.sanitize_filename(info.name)}.log.1"

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

        log_file = self.log_dir / f"{self.sanitize_filename(info.name)}.log"
        venv_python = self.get_venv_python(info)

        # Build command with optional arguments
        cmd = [str(venv_python), "-u", str(script_path)]
        if info.args:
            cmd.extend([str(arg) for arg in info.args])

        # Build environment variables
        env = os.environ.copy()
        if info.environment:
            for env_var in info.environment:
                if '=' in env_var:
                    key, value = env_var.split('=', 1)
                    env[key] = value

        try:
            with open(log_file, "a") as log:
                info.process = subprocess.Popen(
                    cmd,
                    cwd=work_dir,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    env=env,
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
        pid_save_counter = 0
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

                # Periodically save PIDs (every 10 seconds) to ensure persistence
                pid_save_counter += 1
                if pid_save_counter >= 10:
                    self.save_pids()
                    pid_save_counter = 0

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
                log_file = self.log_dir / f"{self.sanitize_filename(info.name)}.log"
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
                    "uploaded": info.uploaded,
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

        log_file = self.log_dir / f"{self.sanitize_filename(name)}.log"
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

    def upload_program(self, name: str, zip_data: bytes, script: str, enabled: bool = True, args: list = None, environment: list = None) -> dict:
        """Upload a new program from ZIP file.

        Returns: {"success": bool, "message": str}
        """
        with self.lock:
            # Check for duplicate name
            if name in self.processes:
                return {"success": False, "message": f"Program '{name}' already exists. Use update to modify it."}

            # Validate ZIP size
            size_mb = len(zip_data) / (1024 * 1024)
            if size_mb > MAX_UPLOAD_SIZE_MB:
                return {"success": False, "message": f"ZIP file too large ({size_mb:.1f}MB). Maximum is {MAX_UPLOAD_SIZE_MB}MB."}

        # Create program directory
        program_dir = self.uploaded_dir / self.sanitize_filename(name)
        try:
            program_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            return {"success": False, "message": f"Directory for '{name}' already exists."}

        try:
            # Extract ZIP file first (quick operation)
            result = self._extract_zip(zip_data, program_dir)
            if not result["success"]:
                shutil.rmtree(program_dir, ignore_errors=True)
                return result

            # Add to processes immediately with "installing" status
            with self.lock:
                self.processes[name] = ProcessInfo(
                    name=name,
                    script=script,
                    enabled=enabled,
                    uploaded=True,
                    venv_path=str(program_dir / ".venv"),
                    cwd=str(program_dir),
                    args=args,
                    environment=environment,
                    status="installing"
                )
            # Save config outside lock to avoid deadlock
            self.save_uploaded_config()

            # Run installation in background thread
            threading.Thread(
                target=self._install_program_async,
                args=(name, program_dir, enabled),
                daemon=True
            ).start()

            return {"success": True, "message": f"Program '{name}' is being installed. Check logs for progress."}

        except Exception as e:
            shutil.rmtree(program_dir, ignore_errors=True)
            return {"success": False, "message": f"Upload failed: {str(e)}"}

    def _install_program_async(self, name: str, program_dir: Path, should_start: bool):
        """Install program (venv + dependencies) in background thread."""
        log_file = self.log_dir / f"{self.sanitize_filename(name)}.log"

        try:
            # Write initial log message
            with open(log_file, "a") as log:
                log.write(f"\n{'='*70}\n")
                log.write(f"Program Upload: {name}\n")
                log.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                log.write(f"Directory: {program_dir}\n")
                log.write(f"{'='*70}\n\n")

            # Create virtual environment
            result = self._create_venv(program_dir, log_file)
            if not result["success"]:
                with self.lock:
                    if name in self.processes:
                        self.processes[name].status = "error"
                with open(log_file, "a") as log:
                    log.write(f"\n[FAILED] Installation failed: {result['message']}\n")
                return

            # Install dependencies if requirements.txt exists
            requirements_file = program_dir / "requirements.txt"
            if requirements_file.exists():
                result = self._install_requirements(program_dir, log_file)
                if not result["success"]:
                    with self.lock:
                        if name in self.processes:
                            self.processes[name].status = "error"
                    with open(log_file, "a") as log:
                        log.write(f"\n[FAILED] Installation failed: {result['message']}\n")
                    return
            else:
                with open(log_file, "a") as log:
                    log.write(f"No requirements.txt found, skipping dependency installation.\n\n")

            # Installation successful
            with open(log_file, "a") as log:
                log.write(f"\n{'='*70}\n")
                log.write(f"[SUCCESS] Installation completed successfully!\n")
                log.write(f"{'='*70}\n\n")

            # Start the program if enabled
            with self.lock:
                if name in self.processes:
                    info = self.processes[name]
                    if should_start and info.enabled:
                        self.start_process(info)
                    else:
                        info.status = "stopped"

        except Exception as e:
            with self.lock:
                if name in self.processes:
                    self.processes[name].status = "error"
            with open(log_file, "a") as log:
                log.write(f"\n[ERROR] Installation exception: {str(e)}\n")

    def update_program(self, name: str, zip_data: bytes) -> dict:
        """Update an existing uploaded program.

        Returns: {"success": bool, "message": str}
        """
        with self.lock:
            # Check if program exists
            if name not in self.processes:
                return {"success": False, "message": f"Program '{name}' not found."}

            info = self.processes[name]

            # Check if it's an uploaded program
            if not info.uploaded:
                return {"success": False, "message": f"Program '{name}' is not an uploaded program. Cannot update."}

            # Check if it's stopped
            if info.status != "stopped":
                return {"success": False, "message": f"Program '{name}' must be stopped before updating."}

            # Validate ZIP size
            size_mb = len(zip_data) / (1024 * 1024)
            if size_mb > MAX_UPLOAD_SIZE_MB:
                return {"success": False, "message": f"ZIP file too large ({size_mb:.1f}MB). Maximum is {MAX_UPLOAD_SIZE_MB}MB."}

        program_dir = self.uploaded_dir / self.sanitize_filename(name)

        try:
            # Backup current directory
            backup_dir = program_dir.parent / f"{program_dir.name}.backup"
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.copytree(program_dir, backup_dir)

            # Clear existing files (except .venv)
            venv_dir = program_dir / ".venv"
            venv_backup = None
            if venv_dir.exists():
                venv_backup = program_dir.parent / f"{program_dir.name}.venv.backup"
                if venv_backup.exists():
                    shutil.rmtree(venv_backup)
                shutil.move(str(venv_dir), str(venv_backup))

            # Remove old files
            for item in program_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

            # Restore .venv if it was backed up
            if venv_backup and venv_backup.exists():
                shutil.move(str(venv_backup), str(venv_dir))

            # Extract new ZIP
            result = self._extract_zip(zip_data, program_dir)
            if not result["success"]:
                # Restore backup
                shutil.rmtree(program_dir, ignore_errors=True)
                shutil.move(str(backup_dir), str(program_dir))
                return result

            # Set status to installing
            with self.lock:
                if name in self.processes:
                    self.processes[name].status = "installing"

            # Run installation in background (only if requirements.txt exists)
            requirements_file = program_dir / "requirements.txt"
            if requirements_file.exists():
                threading.Thread(
                    target=self._update_program_async,
                    args=(name, program_dir, backup_dir),
                    daemon=True
                ).start()

                return {"success": True, "message": f"Program '{name}' is being updated. Check logs for progress."}
            else:
                # No requirements.txt, update complete
                shutil.rmtree(backup_dir, ignore_errors=True)
                with self.lock:
                    if name in self.processes:
                        self.processes[name].status = "stopped"
                return {"success": True, "message": f"Program '{name}' updated successfully (no dependencies to install)."}

        except Exception as e:
            # Restore backup if it exists
            if backup_dir.exists():
                shutil.rmtree(program_dir, ignore_errors=True)
                shutil.move(str(backup_dir), str(program_dir))
            return {"success": False, "message": f"Update failed: {str(e)}"}

    def _update_program_async(self, name: str, program_dir: Path, backup_dir: Path):
        """Update program dependencies in background thread."""
        log_file = self.log_dir / f"{self.sanitize_filename(name)}.log"

        try:
            # Write initial log message
            with open(log_file, "a") as log:
                log.write(f"\n{'='*70}\n")
                log.write(f"Program Update: {name}\n")
                log.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                log.write(f"{'='*70}\n\n")

            # Install dependencies
            result = self._install_requirements(program_dir, log_file)
            if not result["success"]:
                # Restore backup
                with open(log_file, "a") as log:
                    log.write(f"\n[FAILED] Update failed, restoring backup...\n")
                shutil.rmtree(program_dir, ignore_errors=True)
                shutil.move(str(backup_dir), str(program_dir))
                with self.lock:
                    if name in self.processes:
                        self.processes[name].status = "error"
                return

            # Update successful
            with open(log_file, "a") as log:
                log.write(f"\n{'='*70}\n")
                log.write(f"[SUCCESS] Update completed successfully!\n")
                log.write(f"{'='*70}\n\n")

            # Remove backup
            shutil.rmtree(backup_dir, ignore_errors=True)

            # Set status to stopped
            with self.lock:
                if name in self.processes:
                    self.processes[name].status = "stopped"

        except Exception as e:
            # Restore backup if it exists
            if backup_dir.exists():
                with open(log_file, "a") as log:
                    log.write(f"\n[ERROR] Update exception, restoring backup: {str(e)}\n")
                shutil.rmtree(program_dir, ignore_errors=True)
                shutil.move(str(backup_dir), str(program_dir))
            with self.lock:
                if name in self.processes:
                    self.processes[name].status = "error"

    def remove_program(self, name: str) -> dict:
        """Remove an uploaded program.

        Returns: {"success": bool, "message": str}
        """
        with self.lock:
            # Check if program exists
            if name not in self.processes:
                return {"success": False, "message": f"Program '{name}' not found."}

            info = self.processes[name]

            # Check if it's an uploaded program
            if not info.uploaded:
                return {"success": False, "message": f"Program '{name}' is not an uploaded program. Cannot remove."}

            # Check if it's stopped
            if info.status != "stopped":
                return {"success": False, "message": f"Program '{name}' must be stopped before removal."}

            # Remove from processes
            del self.processes[name]

        # Save config outside lock to avoid deadlock
        self.save_uploaded_config()

        # Remove program directory
        program_dir = self.uploaded_dir / self.sanitize_filename(name)
        try:
            if program_dir.exists():
                shutil.rmtree(program_dir)
            return {"success": True, "message": f"Program '{name}' removed successfully."}
        except Exception as e:
            return {"success": False, "message": f"Failed to remove directory: {str(e)}"}

    def _extract_zip(self, zip_data: bytes, target_dir: Path) -> dict:
        """Extract ZIP file to target directory with security checks.

        Automatically handles both ZIP structures:
        - Files directly in ZIP root
        - Single top-level directory containing all files (flattens automatically)
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
                tmp_file.write(zip_data)
                tmp_path = tmp_file.name

            try:
                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                    # Security check: prevent path traversal
                    for member in zip_ref.namelist():
                        if member.startswith('/') or '..' in member:
                            return {"success": False, "message": "Invalid ZIP file: contains unsafe paths."}

                    # Extract all files
                    zip_ref.extractall(target_dir)

                # Check if there's a single top-level directory and flatten if needed
                items = list(target_dir.iterdir())
                if len(items) == 1 and items[0].is_dir():
                    # Single directory - move contents up one level
                    inner_dir = items[0]
                    for item in inner_dir.iterdir():
                        shutil.move(str(item), str(target_dir / item.name))
                    # Remove now-empty directory
                    inner_dir.rmdir()

                return {"success": True, "message": "Extraction successful."}
            finally:
                os.unlink(tmp_path)

        except zipfile.BadZipFile:
            return {"success": False, "message": "Invalid ZIP file."}
        except Exception as e:
            return {"success": False, "message": f"Extraction failed: {str(e)}"}

    def _create_venv(self, program_dir: Path, log_file: Path = None) -> dict:
        """Create a virtual environment for the program."""
        venv_dir = program_dir / ".venv"
        try:
            if log_file:
                with open(log_file, "a") as log:
                    log.write(f"\n{'='*60}\n")
                    log.write(f"Creating virtual environment...\n")
                    log.write(f"Command: {sys.executable} -m venv {venv_dir}\n")
                    log.write(f"{'='*60}\n")
                    log.flush()

                    result = subprocess.run(
                        [sys.executable, "-m", "venv", str(venv_dir)],
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=60
                    )
            else:
                result = subprocess.run(
                    [sys.executable, "-m", "venv", str(venv_dir)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

            if result.returncode != 0:
                msg = "venv creation failed (see logs for details)" if log_file else f"venv creation failed: {result.stderr}"
                if log_file:
                    with open(log_file, "a") as log:
                        log.write(f"\n[ERROR] venv creation failed with code {result.returncode}\n")
                return {"success": False, "message": msg}

            if log_file:
                with open(log_file, "a") as log:
                    log.write(f"\n[SUCCESS] Virtual environment created successfully\n\n")

            return {"success": True, "message": "Virtual environment created."}
        except subprocess.TimeoutExpired:
            if log_file:
                with open(log_file, "a") as log:
                    log.write(f"\n[ERROR] venv creation timed out after 60 seconds\n")
            return {"success": False, "message": "venv creation timed out."}
        except Exception as e:
            if log_file:
                with open(log_file, "a") as log:
                    log.write(f"\n[ERROR] venv creation failed: {str(e)}\n")
            return {"success": False, "message": f"venv creation failed: {str(e)}"}

    def _install_requirements(self, program_dir: Path, log_file: Path = None) -> dict:
        """Install requirements.txt in the program's virtual environment."""
        venv_python = program_dir / ".venv" / "bin" / "python"
        requirements_file = program_dir / "requirements.txt"

        if not venv_python.exists():
            return {"success": False, "message": "Virtual environment not found."}

        try:
            if log_file:
                with open(log_file, "a") as log:
                    log.write(f"{'='*60}\n")
                    log.write(f"Installing dependencies from requirements.txt...\n")
                    log.write(f"Command: {venv_python} -m pip install -r {requirements_file}\n")
                    log.write(f"{'='*60}\n")
                    log.flush()

                    result = subprocess.run(
                        [str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)],
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=300,  # 5 minutes max
                        cwd=program_dir
                    )
            else:
                result = subprocess.run(
                    [str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=program_dir
                )

            if result.returncode != 0:
                msg = "pip install failed (see logs for details)" if log_file else f"pip install failed: {result.stderr}"
                if log_file:
                    with open(log_file, "a") as log:
                        log.write(f"\n[ERROR] pip install failed with code {result.returncode}\n")
                return {"success": False, "message": msg}

            if log_file:
                with open(log_file, "a") as log:
                    log.write(f"\n[SUCCESS] Dependencies installed successfully\n")
                    log.write(f"{'='*60}\n\n")

            return {"success": True, "message": "Requirements installed."}
        except subprocess.TimeoutExpired:
            if log_file:
                with open(log_file, "a") as log:
                    log.write(f"\n[ERROR] pip install timed out after 5 minutes\n")
            return {"success": False, "message": "pip install timed out (>5 minutes)."}
        except Exception as e:
            if log_file:
                with open(log_file, "a") as log:
                    log.write(f"\n[ERROR] pip install failed: {str(e)}\n")
            return {"success": False, "message": f"pip install failed: {str(e)}"}

    def shutdown(self):
        """Shutdown the process manager without stopping managed processes."""
        print("\nShutting down process manager...")
        self.running = False
        with self.lock:
            self.save_pids()  # Save current state for next startup
        print("Process manager stopped. Managed processes continue running.")
