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
import os
import re
import shutil
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


class ProcessManager:
    def __init__(self, config_path: str = "process_manager.yaml"):
        self.base_dir = Path(__file__).parent.parent.resolve()
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
