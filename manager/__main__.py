#!/usr/bin/env python3
"""
Process Manager - Entry point.

Copyright (C) 2025 Andreas Vogler

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

import signal
import sys
import threading
from http.server import HTTPServer

from .manager import ProcessManager
from .web_handler import WebHandler


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
