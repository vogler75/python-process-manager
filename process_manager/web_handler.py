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
from email import message_from_bytes
from email.policy import default

from .web_template import get_html


class WebHandler(BaseHTTPRequestHandler):
    manager = None  # Will be set by main()

    def log_message(self, format, *args):
        pass

    def _parse_multipart(self, body: bytes, content_type: str) -> dict:
        """Parse multipart/form-data using email module."""
        # Create a proper MIME message
        headers = f"Content-Type: {content_type}\r\n\r\n".encode() + body
        msg = message_from_bytes(headers, policy=default)

        fields = {}
        files = {}

        if msg.is_multipart():
            for part in msg.iter_parts():
                content_disposition = part.get('Content-Disposition', '')
                if 'name=' in content_disposition:
                    # Extract field name
                    name_start = content_disposition.find('name="') + 6
                    name_end = content_disposition.find('"', name_start)
                    field_name = content_disposition[name_start:name_end]

                    # Check if it's a file
                    if 'filename=' in content_disposition:
                        filename_start = content_disposition.find('filename="') + 10
                        filename_end = content_disposition.find('"', filename_start)
                        filename = content_disposition[filename_start:filename_end]
                        files[field_name] = {
                            'filename': filename,
                            'data': part.get_payload(decode=True)
                        }
                    else:
                        # Regular field
                        fields[field_name] = part.get_payload(decode=True).decode('utf-8', errors='replace').strip()

        return {'fields': fields, 'files': files}

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
        if self.path == "/api/upload":
            self._handle_upload()
        elif self.path.startswith("/api/update/"):
            parts = self.path.split("/")
            if len(parts) >= 4:
                name = unquote(parts[3])
                self._handle_update(name)
            else:
                self.send_response(400)
                self.end_headers()
        elif self.path.startswith("/api/remove/"):
            parts = self.path.split("/")
            if len(parts) >= 4:
                name = unquote(parts[3])
                result = self.manager.remove_program(name)
                self.send_response(200 if result["success"] else 400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            else:
                self.send_response(400)
                self.end_headers()
        elif self.path.startswith("/api/"):
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

        else:
            self.send_response(404)
            self.end_headers()

    def _handle_upload(self):
        """Handle program upload via multipart form data."""
        try:
            content_type = self.headers.get('Content-Type')
            if not content_type or not content_type.startswith('multipart/form-data'):
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "message": "Invalid content type"}).encode())
                return

            # Parse multipart form data
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            # Parse using email module
            parsed = self._parse_multipart(body, content_type)
            fields = parsed['fields']
            files = parsed['files']

            # Extract fields
            name = fields.get('name')
            script = fields.get('script')
            # Checkbox only sends value when checked, nothing when unchecked
            enabled = 'enabled' in fields
            args_str = fields.get('args', '')
            args = [arg.strip() for arg in args_str.split() if arg.strip()] if args_str else None

            # Get ZIP file
            if 'zipfile' not in files:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "message": "No ZIP file provided"}).encode())
                return

            zip_data = files['zipfile']['data']

            # Validate required fields
            if not name or not script:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "message": "Name and script are required"}).encode())
                return

            # Upload program
            result = self.manager.upload_program(name, zip_data, script, enabled, args)

            self.send_response(200 if result["success"] else 400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "message": f"Upload error: {str(e)}"}).encode())

    def _handle_update(self, name: str):
        """Handle program update via multipart form data."""
        try:
            content_type = self.headers.get('Content-Type')
            if not content_type or not content_type.startswith('multipart/form-data'):
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "message": "Invalid content type"}).encode())
                return

            # Parse multipart form data
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            # Parse using email module
            parsed = self._parse_multipart(body, content_type)
            files = parsed['files']

            # Get ZIP file
            if 'zipfile' not in files:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "message": "No ZIP file provided"}).encode())
                return

            zip_data = files['zipfile']['data']

            # Update program
            result = self.manager.update_program(name, zip_data)

            self.send_response(200 if result["success"] else 400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "message": f"Update error: {str(e)}"}).encode())
