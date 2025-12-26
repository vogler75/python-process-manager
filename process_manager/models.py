"""
Data models for Process Manager.

Copyright (C) 2025 Andreas Vogler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

# Number of CPU history points to keep (at 1 sample per second = 60 seconds of history)
CPU_HISTORY_SIZE = 60


@dataclass
class ProcessInfo:
    name: str
    script: str
    enabled: bool = True
    uploaded: bool = False  # Flag to mark uploaded/managed programs (can be removed via UI)
    venv: str = None  # Optional: program-specific venv path
    cwd: str = None  # Optional: working directory for the process
    args: list = None  # Optional: command-line arguments
    environment: list = None  # Optional: environment variables as list of "KEY=VALUE" strings
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
