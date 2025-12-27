"""
Web UI template for Process Manager.

Copyright (C) 2025 Andreas Vogler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""


def get_html(title: str = "Process Manager") -> str:
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
            max-width: 1400px;
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
            flex-wrap: wrap;
            gap: 15px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.2s ease;
        }
        .process:hover {
            background: rgba(13, 20, 33, 0.8);
            border-color: rgba(0, 212, 255, 0.2);
            transform: translateY(-1px);
        }
        .process-info { flex: 1; min-width: 250px; }
        .process-name { font-weight: 600; font-size: 1.05em; color: #fff; }
        .process-script { color: #666; font-size: 0.85em; margin-top: 2px; }
        .process-meta { font-size: 0.8em; color: #888; margin-top: 6px; }
        .process-controls { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }

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
        .status.installing { background: rgba(156, 39, 176, 0.2); color: #9c27b0; border: 1px solid rgba(156, 39, 176, 0.3); }
        .status.error { background: rgba(255, 152, 0, 0.2); color: #ff9800; border: 1px solid rgba(255, 152, 0, 0.3); }

        /* Buttons */
        .actions { display: flex; gap: 6px; flex-wrap: wrap; }
        .btn {
            padding: 6px 12px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.8em;
            font-weight: 500;
            transition: all 0.2s ease;
            white-space: nowrap;
        }
        .btn-placeholder { visibility: hidden; pointer-events: none; }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); }
        .btn:active { transform: translateY(0); }
        .btn:disabled { background: #444; cursor: not-allowed; opacity: 0.5; transform: none; box-shadow: none; }
        .btn-start { background: linear-gradient(135deg, #4caf50, #45a049); color: white; }
        .btn-stop { background: linear-gradient(135deg, #f44336, #d32f2f); color: white; }
        .btn-restart { background: linear-gradient(135deg, #2196f3, #1976d2); color: white; }
        .btn-logs { background: linear-gradient(135deg, #9c27b0, #7b1fa2); color: white; }
        .btn-remove { background: linear-gradient(135deg, #ff5722, #e64a19); color: white; }
        .btn-update { background: linear-gradient(135deg, #ff9800, #f57c00); color: white; }
        .btn-upload-header { background: linear-gradient(135deg, #00bcd4, #0097a7); color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9em; font-weight: 600; transition: all 0.2s ease; }
        .btn-upload-header:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0, 188, 212, 0.4); }
        .btn-reload-config { background: linear-gradient(135deg, #ff9800, #f57c00); color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9em; font-weight: 600; transition: all 0.2s ease; }
        .btn-reload-config:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(255, 152, 0, 0.4); }
        .btn-reload-config:disabled { background: #444; cursor: not-allowed; transform: none; box-shadow: none; }
        .btn-view-toggle { background: linear-gradient(135deg, #673ab7, #512da8); color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9em; font-weight: 600; transition: all 0.2s ease; }
        .btn-view-toggle:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(103, 58, 183, 0.4); }

        /* Table View */
        .process-table {
            width: 100%;
            border-collapse: collapse;
        }
        .process-table thead {
            background: rgba(0, 212, 255, 0.1);
            border-bottom: 2px solid rgba(0, 212, 255, 0.3);
        }
        .process-table th {
            padding: 12px 15px;
            text-align: left;
            color: #00d4ff;
            font-weight: 600;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .process-table td {
            padding: 10px 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 0.9em;
        }
        .process-table tbody tr {
            background: rgba(13, 20, 33, 0.4);
            transition: background 0.2s ease;
        }
        .process-table tbody tr:hover {
            background: rgba(13, 20, 33, 0.7);
        }
        .table-name { font-weight: 600; color: #fff; }
        .table-info { color: #888; font-size: 0.85em; }
        .table-actions { white-space: nowrap; }
        .table-actions .actions { gap: 4px; }
        .table-actions .btn { padding: 4px 10px; font-size: 0.75em; }
        .view-card .process-table { display: none; }
        .view-table .process-list .process { display: none; }
        .view-table .process-table { display: table; }

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

        /* Upload Modal Styles */
        .upload-modal { max-width: 600px; height: auto; max-height: 80vh; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; color: #00d4ff; font-weight: 500; font-size: 0.9em; }
        .form-group input[type="text"], .form-group input[type="file"], .form-group textarea { width: 100%; padding: 10px; background: rgba(13, 20, 33, 0.8); border: 1px solid rgba(0, 212, 255, 0.3); border-radius: 6px; color: #eee; font-size: 0.9em; font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace; }
        .form-group input[type="text"]:focus, .form-group input[type="file"]:focus, .form-group textarea:focus { outline: none; border-color: rgba(0, 212, 255, 0.6); }
        .form-group textarea { resize: vertical; min-height: 80px; line-height: 1.5; }
        .form-group input[type="checkbox"] { margin-right: 8px; }
        .form-group .hint { font-size: 0.8em; color: #888; margin-top: 4px; }
        .upload-form-body { padding: 25px; max-height: 60vh; overflow-y: auto; }
        .upload-status { padding: 15px; margin-top: 15px; border-radius: 6px; font-size: 0.9em; display: none; }
        .upload-status.success { background: rgba(76, 175, 80, 0.2); color: #4caf50; border: 1px solid rgba(76, 175, 80, 0.3); }
        .upload-status.error { background: rgba(244, 67, 54, 0.2); color: #f44336; border: 1px solid rgba(244, 67, 54, 0.3); }
        .btn-submit { background: linear-gradient(135deg, #4caf50, #45a049); color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-size: 1em; font-weight: 600; transition: all 0.2s; width: 100%; }
        .btn-submit:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4); }
        .btn-submit:disabled { background: #444; cursor: not-allowed; transform: none; }

        /* Responsive Design */
        @media (max-width: 1200px) {
            .container { max-width: 95%; margin: 10px auto; }
        }

        @media (max-width: 900px) {
            .process-controls { width: 100%; justify-content: flex-start; }
            .cpu-container { order: 1; }
            .status { order: 2; }
            .actions { order: 3; width: 100%; }
        }

        @media (max-width: 600px) {
            .header { flex-direction: column; gap: 15px; align-items: flex-start; }
            .process { padding: 12px 15px; }
            .process-info { min-width: 100%; }
            .btn { padding: 5px 10px; font-size: 0.75em; }
            .cpu-container { display: none; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Process Manager</h1>
                <span class="header-subtitle">{{TITLE}}</span>
            </div>
            <div style="display: flex; gap: 15px; align-items: center;">
                <button class="btn btn-view-toggle" onclick="toggleView()" id="btnViewToggle">Table View</button>
                <button class="btn btn-reload-config" onclick="reloadConfig()" id="btnReloadConfig">Reload Configuration</button>
                <button class="btn btn-upload-header" onclick="openUploadModal()">+ Upload Program</button>
                <div class="header-status" id="headerStatus">
                    <span class="dot"></span>
                    <span>Loading...</span>
                </div>
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

    <!-- Upload Program Modal -->
    <div id="uploadModal" class="modal-overlay">
        <div class="modal upload-modal">
            <div class="modal-header">
                <h2 id="uploadModalTitle">Upload Program</h2>
                <button class="modal-close" onclick="closeUploadModal()">Close</button>
            </div>
            <div class="upload-form-body">
                <form id="uploadForm" onsubmit="handleUpload(event)">
                    <div class="form-group">
                        <label for="programName">Program Name *</label>
                        <input type="text" id="programName" name="name" required placeholder="My Application">
                        <div class="hint">Unique name for this program</div>
                    </div>
                    <div class="form-group">
                        <label for="scriptFile">Entry Script *</label>
                        <input type="text" id="scriptFile" name="script" required placeholder="main.py">
                        <div class="hint">Python script to execute (e.g., main.py, app.py)</div>
                    </div>
                    <div class="form-group">
                        <label for="zipFile">ZIP File *</label>
                        <input type="file" id="zipFile" name="zipfile" accept=".zip" required>
                        <div class="hint">ZIP archive containing your Python program (max 50MB)</div>
                    </div>
                    <div class="form-group">
                        <label for="programArgs">Arguments (optional)</label>
                        <input type="text" id="programArgs" name="args" placeholder="--port 8000 --debug">
                        <div class="hint">Space-separated command-line arguments</div>
                    </div>
                    <div class="form-group">
                        <label for="programEnvironment">Environment Variables (optional)</label>
                        <textarea id="programEnvironment" name="environment" rows="4" placeholder="PYTHONUNBUFFERED=TRUE&#10;DTU_HOST=192.168.1.132&#10;UPDATE_EVERY=45"></textarea>
                        <div class="hint">One environment variable per line in KEY=VALUE format</div>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="programEnabled" name="enabled" checked>
                            Start automatically after upload
                        </label>
                    </div>
                    <div class="upload-status" id="uploadStatus"></div>
                    <button type="submit" class="btn-submit" id="uploadBtn">Upload Program</button>
                </form>
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

            // Card view (existing)
            const cardHtml = processes.map(p => `
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
                    <div class="process-controls">
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
                            ${p.uploaded ? `
                                ${p.status === 'stopped' ? `<button class="btn btn-update" onclick="openUpdateModal('${p.name}')">Update</button>` : `<button class="btn btn-update btn-placeholder">Update</button>`}
                                ${p.status === 'stopped' ? `<button class="btn btn-remove" onclick="removeProgram('${p.name}')">Remove</button>` : `<button class="btn btn-remove btn-placeholder">Remove</button>`}
                            ` : `
                                <button class="btn btn-update btn-placeholder">Update</button>
                                <button class="btn btn-remove btn-placeholder">Remove</button>
                            `}
                        </div>
                    </div>
                </div>
            `).join('');

            // Table view (compact)
            const tableHtml = `
                <table class="process-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Status</th>
                            <th>PID / Uptime</th>
                            <th>CPU</th>
                            <th>Restarts</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${processes.map(p => `
                            <tr>
                                <td>
                                    <div class="table-name">${p.name}</div>
                                    ${p.log_size_display ? `<div class="table-info">Log: ${p.log_size_display}</div>` : ''}
                                </td>
                                <td><span class="status ${p.status}">${p.status}</span></td>
                                <td class="table-info">
                                    ${p.pid ? `PID: ${p.pid}` : '-'}<br>
                                    ${p.uptime || '-'}
                                </td>
                                <td>
                                    <div class="cpu-container">
                                        <div class="cpu-chart">${renderSparkline(p.cpu_history)}</div>
                                        <span class="cpu-value">${p.cpu_current.toFixed(1)}%</span>
                                    </div>
                                </td>
                                <td class="table-info">${p.total_restarts || 0}${p.is_broken ? ` (${p.consecutive_failures} fails)` : ''}</td>
                                <td class="table-actions">
                                    <div class="actions">
                                        ${p.status === 'stopped' || p.is_broken ?
                                            `<button class="btn btn-start" onclick="action('start', '${p.name}')">Start</button>` :
                                            `<button class="btn btn-stop" onclick="action('stop', '${p.name}')" ${p.status === 'stopping' ? 'disabled' : ''}>Stop</button>`}
                                        <button class="btn btn-restart" onclick="action('restart', '${p.name}')" ${p.status === 'stopping' || p.status === 'restarting' ? 'disabled' : ''}>Restart</button>
                                        <button class="btn btn-logs" onclick="openLogModal('${p.name}')">Logs</button>
                                        ${p.uploaded ? `
                                            ${p.status === 'stopped' ? `<button class="btn btn-update" onclick="openUpdateModal('${p.name}')">Update</button>` : ''}
                                            ${p.status === 'stopped' ? `<button class="btn btn-remove" onclick="removeProgram('${p.name}')">Remove</button>` : ''}
                                        ` : ''}
                                    </div>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;

            container.innerHTML = cardHtml + tableHtml;

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
            if (e.key === 'Escape') {
                if (document.getElementById('logModal').classList.contains('active')) {
                    closeLogModal();
                }
                if (document.getElementById('uploadModal').classList.contains('active')) {
                    closeUploadModal();
                }
            }
        });

        // Upload Modal Functions
        let isUpdateMode = false;
        let updateProgramName = null;

        function openUploadModal() {
            isUpdateMode = false;
            updateProgramName = null;
            document.getElementById('uploadModalTitle').textContent = 'Upload Program';
            document.getElementById('uploadForm').reset();
            document.getElementById('programName').disabled = false;
            document.getElementById('scriptFile').disabled = false;
            document.getElementById('uploadBtn').textContent = 'Upload Program';
            document.getElementById('uploadStatus').style.display = 'none';
            document.getElementById('uploadModal').classList.add('active');
        }

        function openUpdateModal(name) {
            isUpdateMode = true;
            updateProgramName = name;
            document.getElementById('uploadModalTitle').textContent = `Update Program: ${name}`;
            document.getElementById('uploadForm').reset();
            document.getElementById('programName').value = name;
            document.getElementById('programName').disabled = true;
            document.getElementById('scriptFile').disabled = true;
            document.getElementById('uploadBtn').textContent = 'Update Program';
            document.getElementById('uploadStatus').style.display = 'none';
            document.getElementById('uploadModal').classList.add('active');
        }

        function closeUploadModal() {
            document.getElementById('uploadModal').classList.remove('active');
            isUpdateMode = false;
            updateProgramName = null;
        }

        async function handleUpload(event) {
            event.preventDefault();
            const form = event.target;
            const formData = new FormData(form);
            const uploadBtn = document.getElementById('uploadBtn');
            const statusDiv = document.getElementById('uploadStatus');

            uploadBtn.disabled = true;
            uploadBtn.textContent = isUpdateMode ? 'Updating...' : 'Uploading...';
            statusDiv.style.display = 'none';

            try {
                const url = isUpdateMode ? `/api/update/${encodeURIComponent(updateProgramName)}` : '/api/upload';
                const response = await fetch(url, {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                statusDiv.style.display = 'block';
                if (result.success) {
                    statusDiv.className = 'upload-status success';
                    statusDiv.textContent = result.message + ' The program is now installing in the background. Check logs to see progress.';
                    form.reset();
                    setTimeout(() => {
                        closeUploadModal();
                        fetchStatus();
                    }, 2000);
                } else {
                    statusDiv.className = 'upload-status error';
                    statusDiv.textContent = result.message;
                }
            } catch (error) {
                statusDiv.style.display = 'block';
                statusDiv.className = 'upload-status error';
                statusDiv.textContent = `Error: ${error.message}`;
            } finally {
                uploadBtn.disabled = false;
                uploadBtn.textContent = isUpdateMode ? 'Update Program' : 'Upload Program';
            }
        }

        async function removeProgram(name) {
            if (!confirm(`Are you sure you want to remove "${name}"? This will delete all files and cannot be undone.`)) {
                return;
            }

            try {
                const response = await fetch(`/api/remove/${encodeURIComponent(name)}`, {
                    method: 'POST'
                });

                const result = await response.json();

                if (result.success) {
                    alert(result.message);
                    fetchStatus();
                } else {
                    alert(`Failed to remove: ${result.message}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }

        async function reloadConfig() {
            const btn = document.getElementById('btnReloadConfig');
            btn.disabled = true;
            btn.textContent = 'Reloading...';

            try {
                const response = await fetch('/api/reload-config', {
                    method: 'POST'
                });

                const result = await response.json();

                if (result.success) {
                    alert(result.message);
                    fetchStatus();
                } else {
                    alert(`Failed to reload configuration: ${result.message}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Reload Configuration';
            }
        }

        function toggleView() {
            const container = document.querySelector('.container');
            const btn = document.getElementById('btnViewToggle');
            const currentView = localStorage.getItem('viewMode') || 'card';

            if (currentView === 'card') {
                container.classList.remove('view-card');
                container.classList.add('view-table');
                localStorage.setItem('viewMode', 'table');
                btn.textContent = 'Card View';
            } else {
                container.classList.remove('view-table');
                container.classList.add('view-card');
                localStorage.setItem('viewMode', 'card');
                btn.textContent = 'Table View';
            }
        }

        // Initialize view on page load
        (function initView() {
            const container = document.querySelector('.container');
            const btn = document.getElementById('btnViewToggle');
            const savedView = localStorage.getItem('viewMode') || 'card';

            if (savedView === 'table') {
                container.classList.add('view-table');
                btn.textContent = 'Card View';
            } else {
                container.classList.add('view-card');
                btn.textContent = 'Table View';
            }
        })();

        fetchStatus();
        setInterval(fetchStatus, 2000);
    </script>
</body>
</html>"""
    return html.replace("{{TITLE}}", title)
