"""
Process Manager - A lightweight, single-package process manager with web UI.

Copyright (C) 2025 Andreas Vogler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from .manager import ProcessManager
from .models import ProcessInfo
from .web_handler import WebHandler

__version__ = "1.0.0"
__all__ = ["ProcessManager", "ProcessInfo", "WebHandler"]
