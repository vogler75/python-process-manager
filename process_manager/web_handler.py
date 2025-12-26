"""
Web UI handler for Process Manager.

Copyright (C) 2025 Andreas Vogler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

from .web_template import get_html


class WebHandler(BaseHTTPRequestHandler):
    manager = None  # Will be set by main()

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(get_html(self.manager.web_title).encode())
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.manager.get_status()).encode())
        elif self.path.startswith("/api/logs/"):
            # Parse: /api/logs/{name}?lines=100&offset=0
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
