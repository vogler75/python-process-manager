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
    <meta charset="UTF-8">
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
            max-width: 1600px;
            margin: 0 auto;
            background: rgba(22, 33, 62, 0.6);
            border-radius: 16px;
            border: 1px solid rgba(0, 212, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 60px rgba(0, 212, 255, 0.1);
            backdrop-filter: blur(10px);
            overflow: hidden;
            width: 95%; /* Ensure it takes up most of the screen */
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
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 20px;
        }
        .process {
            background: rgba(13, 20, 33, 0.6);
            border-radius: 16px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.3s ease;
            position: relative;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .process:hover {
            background: rgba(13, 20, 33, 0.85);
            border-color: rgba(0, 212, 255, 0.3);
            transform: translateY(-4px);
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.4);
        }
        
        /* Card Layout Sections */
        .process-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }
        .process-title-group { flex: 1; min-width: 0; padding-right: 15px; }
        .process-name { 
            font-weight: 700; 
            font-size: 1.25em; 
            color: #fff; 
            margin-bottom: 6px;
            white-space: nowrap; 
            overflow: hidden; 
            text-overflow: ellipsis; 
        }
        .process-script {
            color: #666;
            font-size: 0.85em;
            font-family: 'Monaco', monospace;
            background: rgba(255,255,255,0.05);
            padding: 2px 6px;
            border-radius: 4px;
            display: inline-block;
        }
        .process-comment {
            color: #888;
            font-size: 0.8em;
            margin-top: 4px;
            font-style: italic;
        }

        .process-stats {
            display: grid;
            grid-template-columns: 1fr 140px;
            gap: 20px;
            align-items: center;
            background: rgba(0,0,0,0.2);
            padding: 15px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.03);
        }
        
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(2, 1fr); 
            gap: 12px;
        }
        .stat-item { display: flex; flex-direction: column; gap: 2px; }
        .stat-label { color: #555; font-size: 0.75em; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; }
        .stat-value { color: #ccc; font-family: 'Monaco', monospace; font-size: 0.9em; }
        
        .cpu-group { 
            display: flex; 
            flex-direction: column; 
            align-items: flex-end; 
            gap: 5px; 
            padding-left: 15px;
            border-left: 1px solid rgba(255,255,255,0.05);
        }
        .cpu-val-display { font-size: 1.4em; font-weight: 700; color: #4caf50; letter-spacing: -0.5px; }
        .cpu-label-mini { font-size: 0.7em; color: #666; text-transform: uppercase; }
        .cpu-chart-mini {
            width: 100%;
            height: 35px;
            opacity: 0.8;
        }
        .cpu-chart-mini svg { display: block; width: 100%; height: 100%; }

        .process-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 10px;
        }
        .action-group { display: flex; gap: 8px; }
        
        /* Larger buttons for the main card view */
        .process-actions .btn {
            padding: 8px 14px;
            height: 36px;
        }

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
        .btn {
            padding: 6px 12px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 600;
            transition: all 0.2s ease;
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 36px;
            height: 36px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .btn svg {
            width: 18px;
            height: 18px;
            fill: currentColor;
            display: block;
            margin-right: 6px;
        }
        .process-table .btn svg { margin-right: 0; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4); filter: brightness(1.1); }
        .btn:active { transform: translateY(0); }
        .btn:disabled { background: #444; cursor: not-allowed; opacity: 0.5; transform: none; box-shadow: none; color: #888; }
        
        /* Gradient Button Styles */
        .btn-start { background: linear-gradient(135deg, #4caf50, #2e7d32); color: white; }
        .btn-stop { background: linear-gradient(135deg, #f44336, #c62828); color: white; }
        .btn-restart { background: linear-gradient(135deg, #2196f3, #1565c0); color: white; }
        .btn-logs { background: linear-gradient(135deg, #9c27b0, #7b1fa2); color: white; }
        .btn-remove { background: linear-gradient(135deg, #ff5722, #d84315); color: white; }
        .btn-update { background: linear-gradient(135deg, #ff9800, #ef6c00); color: white; }
        .btn-edit { background: linear-gradient(135deg, #607d8b, #455a64); color: white; }
        .btn-add { background: linear-gradient(135deg, #00bcd4, #0097a7); color: white; }
        
        .process-footer {
            padding: 12px 16px;
            background: rgba(0, 0, 0, 0.2);
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .process-footer .btn {
            padding: 4px 10px;
            font-size: 0.75em;
            height: 30px;
            min-width: 0;
            border-radius: 4px;
        }
        .process-footer .btn svg {
            width: 14px;
            height: 14px;
            margin-right: 4px;
        }
        .action-group { display: flex; gap: 6px; }

        /* Responsive Button Labels */
        @media (max-width: 1200px) {
            .process-footer .btn-text { display: none; }
            .process-footer .btn svg { margin-right: 0; }
            .process-footer .btn { padding: 4px; width: 32px; height: 32px; }
        }
        
        .btn-reload-config { background: linear-gradient(135deg, #ff9800, #f57c00); color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9em; font-weight: 600; transition: all 0.2s ease; }
        .btn-reload-config:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(255, 152, 0, 0.4); }
        .btn-reload-config:disabled { background: #444; cursor: not-allowed; transform: none; box-shadow: none; }
        .btn-view-toggle { background: linear-gradient(135deg, #673ab7, #512da8); color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9em; font-weight: 600; transition: all 0.2s ease; }
        .btn-view-toggle:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(103, 58, 183, 0.4); }

        /* Table View */
        .process-table {
            width: 100%;
            border-collapse: collapse;
            table-layout: auto; /* Let columns adjust */
        }
        .process-table thead {
            background: rgba(0, 212, 255, 0.1);
            border-bottom: 2px solid rgba(0, 212, 255, 0.3);
        }
        .process-table th {
            padding: 6px 12px;
            text-align: left;
            color: #00d4ff;
            font-weight: 600;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .process-table td {
            padding: 4px 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 0.9em;
            vertical-align: middle;
            white-space: nowrap; /* Force single line */
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
        .table-actions .btn { padding: 4px; font-size: 0.75em; min-width: 28px; height: 28px; }
        .table-actions .btn svg { width: 14px; height: 14px; margin-right: 0; }
        .view-card .process-table { display: none; }
        .view-table .process-list .process { display: none; }
        .view-table .process-table { display: table; }
        .view-table .process-list { display: block; padding: 0; }

        .container.view-table {
            max-width: none;
            width: 100%;
            margin: 0;
            border-radius: 0;
            border: none;
            min-height: 100vh;
            padding: 0 10px;
        }

        /* Footer */
        .footer {
            padding: 10px 25px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            color: #666;
            font-size: 0.8em;
            text-align: center;
        }

        .log-size { color: #666; font-size: 0.75em; margin-left: 8px; }

        /* Removed old CPU chart styles */

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
            .container { max-width: 98%; margin: 10px auto; }
        }

        @media (max-width: 900px) {
            .process-list {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 600px) {
            .header { padding: 15px; flex-direction: column; gap: 15px; align-items: stretch; }
            .header > div { width: 100%; }
            .header div[style*="display: flex"] { flex-wrap: wrap; justify-content: center; }
            .process { padding: 15px; }
            .process-controls { flex-direction: column; gap: 12px; padding: 12px; }
            .actions { width: 100%; justify-content: center; }
            .cpu-container { width: 100%; justify-content: center; }
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
                <button class="btn btn-add" onclick="openAddModal()">+ New Program</button>
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

    <!-- Edit Program Modal -->
    <div id="editModal" class="modal-overlay">
        <div class="modal upload-modal">
            <div class="modal-header">
                <h2 id="editModalTitle">Edit Program</h2>
                <button class="modal-close" onclick="closeEditModal()">Close</button>
            </div>
            <div class="upload-form-body">
                <form id="editForm" onsubmit="handleEdit(event)">
                    <input type="hidden" id="editOriginalName">
                    <div class="form-group">
                        <label for="editProgramName">Program Name *</label>
                        <input type="text" id="editProgramName" name="name" required>
                        <div class="hint">Changing the name will rename the program</div>
                    </div>
                    <div class="form-group">
                        <label for="editScript">Entry Script *</label>
                        <input type="text" id="editScript" name="script" required>
                    </div>
                    <div class="form-group">
                        <label for="editComment">Comment (optional)</label>
                        <textarea id="editComment" name="comment" rows="2" placeholder="Description or notes about this program"></textarea>
                    </div>
                    <div class="form-group">
                        <label for="editVenv">Virtual Environment (optional)</label>
                        <input type="text" id="editVenv" name="venv" placeholder=".venv or /path/to/venv">
                        <div class="hint">Leave empty to use global venv</div>
                    </div>
                    <div class="form-group">
                        <label for="editCwd">Working Directory (optional)</label>
                        <input type="text" id="editCwd" name="cwd" placeholder="/path/to/directory">
                        <div class="hint">Leave empty to use global cwd</div>
                    </div>
                    <div class="form-group">
                        <label for="editArgs">Arguments (optional)</label>
                        <input type="text" id="editArgs" name="args" placeholder="--port 8000 --debug">
                    </div>
                    <div class="form-group">
                        <label for="editEnvironment">Environment Variables (optional)</label>
                        <textarea id="editEnvironment" name="environment" rows="3" placeholder="KEY=VALUE (one per line)"></textarea>
                    </div>
                    <div class="form-group" id="editZipGroup" style="display: none;">
                        <label for="editZipFile">Update Code (optional)</label>
                        <input type="file" id="editZipFile" name="zipfile" accept=".zip">
                        <div class="hint">Upload a new ZIP to replace the program files (keeps venv)</div>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="editEnabled" name="enabled">
                            Enabled (auto-start when manager starts)
                        </label>
                    </div>
                    <div class="upload-status" id="editStatus"></div>
                    <button type="submit" class="btn-submit" id="editBtn">Save Changes</button>
                </form>
            </div>
        </div>
    </div>

    <!-- New Program Modal -->
    <div id="addModal" class="modal-overlay">
        <div class="modal upload-modal">
            <div class="modal-header">
                <h2>New Program</h2>
                <button class="modal-close" onclick="closeAddModal()">Close</button>
            </div>
            <div class="upload-form-body">
                <form id="addForm" onsubmit="handleAdd(event)">
                    <div class="form-group">
                        <label for="addProgramName">Program Name *</label>
                        <input type="text" id="addProgramName" name="name" required placeholder="My Application">
                        <div class="hint">Unique name for this program</div>
                    </div>
                    <div class="form-group">
                        <label for="addScript">Entry Script *</label>
                        <input type="text" id="addScript" name="script" required placeholder="main.py or /path/to/script.py">
                        <div class="hint">Python script to execute</div>
                    </div>
                    <div class="form-group">
                        <label for="addZipFile">ZIP File (optional)</label>
                        <input type="file" id="addZipFile" name="zipfile" accept=".zip">
                        <div class="hint">If provided, extracts files and creates isolated venv with requirements.txt</div>
                    </div>
                    <div class="form-group">
                        <label for="addComment">Comment (optional)</label>
                        <textarea id="addComment" name="comment" rows="2" placeholder="Description or notes about this program"></textarea>
                    </div>
                    <div class="form-group" id="addVenvGroup">
                        <label for="addVenv">Virtual Environment (optional)</label>
                        <input type="text" id="addVenv" name="venv" placeholder=".venv or /path/to/venv">
                        <div class="hint">Leave empty to use global venv (ignored if ZIP provided)</div>
                    </div>
                    <div class="form-group" id="addCwdGroup">
                        <label for="addCwd">Working Directory (optional)</label>
                        <input type="text" id="addCwd" name="cwd" placeholder="/path/to/directory">
                        <div class="hint">Leave empty to use global cwd (ignored if ZIP provided)</div>
                    </div>
                    <div class="form-group">
                        <label for="addArgs">Arguments (optional)</label>
                        <input type="text" id="addArgs" name="args" placeholder="--port 8000 --debug">
                    </div>
                    <div class="form-group">
                        <label for="addEnvironment">Environment Variables (optional)</label>
                        <textarea id="addEnvironment" name="environment" rows="3" placeholder="KEY=VALUE (one per line)"></textarea>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="addEnabled" name="enabled" checked>
                            Start automatically after adding
                        </label>
                    </div>
                    <div class="upload-status" id="addStatus"></div>
                    <button type="submit" class="btn-submit" id="addBtn">Create Program</button>
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

        function getCPUColor(data) {
            if (!data || data.length === 0) return '#4caf50';
            const displayData = data.slice(-300);
            const avg = displayData.reduce((a, b) => a + b, 0) / displayData.length;
            if (avg > 80) return '#f44336';
            if (avg > 50) return '#ff9800';
            return '#4caf50';
        }

        function renderSparkline(data, width = 400, height = 60) {
            if (!data || data.length === 0) {
                return `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none"></svg>`;
            }

            const padding = 1;
            const maxVal = Math.max(...data, 10);

            // Decimate data to match display width for a cleaner "finer" line
            let displayData = data.slice(-300);
            if (displayData.length > width) {
                const sampled = [];
                const bucketSize = displayData.length / width;
                for (let i = 0; i < width; i++) {
                    const start = Math.floor(i * bucketSize);
                    const end = Math.floor((i + 1) * bucketSize);
                    const slice = displayData.slice(start, Math.max(start + 1, end));
                    sampled.push(Math.max(...slice)); // Use max for visibility of spikes
                }
                displayData = sampled;
            }

            const stepX = width / Math.max(displayData.length - 1, 1);
            const points = displayData.map((val, i) => {
                const x = i * stepX;
                const y = height - padding - ((val / maxVal) * (height - padding * 2));
                return `${x},${y}`;
            });

            const polylinePoints = points.join(' ');
            const areaPoints = `${points[0].split(',')[0]},${height} ${polylinePoints} ${points[points.length-1].split(',')[0]},${height}`;

            const color = getCPUColor(data);

            return `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" style="display: block; width: 100%; height: 100%;">
                <polyline fill="${color}" fill-opacity="0.15" points="${areaPoints}"/>
                <polyline fill="none" stroke="${color}" stroke-width="1.2" stroke-linejoin="round" points="${polylinePoints}"/>
            </svg>`;
        }

        const ICONS = {
            start: '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>',
            stop: '<svg viewBox="0 0 24 24"><path d="M6 6h12v12H6z"/></svg>',
            restart: '<svg viewBox="0 0 24 24"><path d="M17.65 6.35A7.958 7.958 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>',
            logs: '<svg viewBox="0 0 24 24"><path d="M19 3h-4.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm2 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>',
            update: '<svg viewBox="0 0 24 24"><path d="M4 12l1.41 1.41L11 7.83V20h2V7.83l5.58 5.59L20 12l-8-8-8 8z"/></svg>',
            remove: '<svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>',
            edit: '<svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>',
            add: '<svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>'
        };

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
                    <div class="process-top">
                        <div class="process-title-group">
                            <div class="process-name" title="${p.name}">${p.name}</div>
                            <div class="process-script">${p.script}</div>
                            ${p.comment ? `<div class="process-comment">${p.comment}</div>` : ''}
                        </div>
                        <span class="status ${p.status}">${p.status}</span>
                    </div>

                    <div class="process-stats">
                        <div class="stats-grid">
                            <div class="stat-item">
                                <span class="stat-label">PID</span>
                                <span class="stat-value">${p.pid || '-'}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Uptime</span>
                                <span class="stat-value">${p.uptime || '-'}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Restarts</span>
                                <span class="stat-value">${p.total_restarts}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Log</span>
                                <span class="stat-value">${p.log_size_display || '0 B'}</span>
                            </div>
                        </div>
                        <div class="cpu-group">
                            <div class="cpu-val-display" style="color: ${getCPUColor(p.cpu_history)}">${p.cpu_current.toFixed(1)}%</div>
                            <div class="cpu-chart-mini">${renderSparkline(p.cpu_history, 120, 35)}</div>
                        </div>
                    </div>

                    <div class="process-footer">
                        <div class="action-group">
                            <button class="btn btn-logs" onclick="openLogModal('${p.name}')" title="Logs">${ICONS.logs} <span class="btn-text">Logs</span></button>
                            <button class="btn btn-edit" onclick="openEditModal('${p.name}')" title="Edit">${ICONS.edit} <span class="btn-text">Edit</span></button>
                            <button class="btn btn-remove" onclick="removeProgram('${p.name}')" ${p.status !== 'stopped' ? 'disabled' : ''} title="Remove">${ICONS.remove} <span class="btn-text">Remove</span></button>
                        </div>
                        <div class="action-group">
                            <button class="btn btn-restart" onclick="action('restart', '${p.name}')" ${p.status === 'stopping' || p.status === 'restarting' ? 'disabled' : ''} title="Restart">${ICONS.restart} <span class="btn-text">Restart</span></button>
                            ${p.status === 'stopped' || p.is_broken ?
                                `<button class="btn btn-start" onclick="action('start', '${p.name}')" title="Start">${ICONS.start} <span class="btn-text">Start</span></button>` :
                                `<button class="btn btn-stop" onclick="action('stop', '${p.name}')" ${p.status === 'stopping' ? 'disabled' : ''} title="Stop">${ICONS.stop} <span class="btn-text">Stop</span></button>`}
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
                            <th>PID</th>
                            <th>Uptime</th>
                            <th>Log Size</th>
                            <th>CPU</th>
                            <th>Restarts</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${processes.map(p => `
                            <tr>
                                <td><span class="table-name">${p.name}</span></td>
                                <td><span class="status ${p.status}">${p.status}</span></td>
                                <td class="table-info">${p.pid || '-'}</td>
                                <td class="table-info">${p.uptime || '-'}</td>
                                <td class="table-info">${p.log_size_display || '-'}</td>
                                 <td>
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <div style="width: 100px; height: 24px; background: rgba(0,0,0,0.2); border-radius: 4px; overflow: hidden; flex-shrink: 0;">
                                            ${renderSparkline(p.cpu_history, 100, 24)}
                                        </div>
                                        <div style="font-size: 0.9em; font-weight: 700; color: ${getCPUColor(p.cpu_history)}; min-width: 50px;">
                                            ${p.cpu_current.toFixed(1)}%
                                        </div>
                                    </div>
                                </td>
                                <td class="table-info">${p.total_restarts || 0}${p.is_broken ? ` (${p.consecutive_failures} fails)` : ''}</td>
                                 <td class="table-actions">
                                    <div class="actions">
                                        ${p.status === 'stopped' || p.is_broken ?
                                            `<button class="btn btn-start" onclick="action('start', '${p.name}')" title="Start">${ICONS.start}</button>` :
                                            `<button class="btn btn-stop" onclick="action('stop', '${p.name}')" ${p.status === 'stopping' ? 'disabled' : ''} title="Stop">${ICONS.stop}</button>`}
                                        <button class="btn btn-restart" onclick="action('restart', '${p.name}')" ${p.status === 'stopping' || p.status === 'restarting' ? 'disabled' : ''} title="Restart">${ICONS.restart}</button>
                                        <button class="btn btn-logs" onclick="openLogModal('${p.name}')" title="Logs">${ICONS.logs}</button>
                                        <button class="btn btn-edit" onclick="openEditModal('${p.name}')" title="Edit">${ICONS.edit}</button>
                                        <button class="btn btn-remove" onclick="removeProgram('${p.name}')" ${p.status !== 'stopped' ? 'disabled' : ''} title="Remove">${ICONS.remove}</button>
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
                if (document.getElementById('editModal').classList.contains('active')) {
                    closeEditModal();
                }
                if (document.getElementById('addModal').classList.contains('active')) {
                    closeAddModal();
                }
            }
        });

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

        // Edit Modal Functions
        let editingProgram = null;

        async function openEditModal(name) {
            editingProgram = name;

            // Always fetch fresh data
            const res = await fetch('/api/status');
            const programs = await res.json();
            const program = programs.find(p => p.name === name);

            if (!program) {
                alert('Program not found');
                return;
            }

            // Populate form
            document.getElementById('editOriginalName').value = name;
            document.getElementById('editProgramName').value = program.name;
            document.getElementById('editScript').value = program.script;
            document.getElementById('editComment').value = program.comment || '';
            document.getElementById('editVenv').value = program.venv || '';
            document.getElementById('editCwd').value = program.cwd || '';
            document.getElementById('editArgs').value = program.args ? program.args.join(' ') : '';
            document.getElementById('editEnvironment').value = program.environment ? program.environment.join('\\n') : '';
            document.getElementById('editEnabled').checked = program.enabled;
            document.getElementById('editZipFile').value = '';  // Clear any previous file selection

            // Show ZIP upload field only for uploaded programs
            document.getElementById('editZipGroup').style.display = program.uploaded ? 'block' : 'none';

            document.getElementById('editModalTitle').textContent = `Edit: ${name}`;
            document.getElementById('editStatus').style.display = 'none';
            document.getElementById('editModal').classList.add('active');
        }

        function closeEditModal() {
            document.getElementById('editModal').classList.remove('active');
            editingProgram = null;
        }

        async function handleEdit(event) {
            event.preventDefault();
            const btn = document.getElementById('editBtn');
            const statusDiv = document.getElementById('editStatus');

            btn.disabled = true;
            btn.textContent = 'Saving...';
            statusDiv.style.display = 'none';

            const originalName = document.getElementById('editOriginalName').value;
            const argsStr = document.getElementById('editArgs').value.trim();
            const envStr = document.getElementById('editEnvironment').value.trim();
            const zipFile = document.getElementById('editZipFile').files[0];

            try {
                // Save the configuration FIRST (before ZIP upload changes status)
                statusDiv.style.display = 'block';
                statusDiv.className = 'upload-status';
                statusDiv.style.background = 'rgba(33, 150, 243, 0.2)';
                statusDiv.style.color = '#2196f3';
                statusDiv.style.border = '1px solid rgba(33, 150, 243, 0.3)';
                statusDiv.textContent = 'Saving configuration...';

                const updates = {
                    new_name: document.getElementById('editProgramName').value,
                    script: document.getElementById('editScript').value,
                    comment: document.getElementById('editComment').value || null,
                    venv: document.getElementById('editVenv').value || null,
                    cwd: document.getElementById('editCwd').value || null,
                    args: argsStr ? argsStr.split(/\\s+/) : null,
                    environment: envStr ? envStr.split('\\n').map(l => l.trim()).filter(l => l) : null,
                    enabled: document.getElementById('editEnabled').checked
                };

                const response = await fetch(`/api/edit/${encodeURIComponent(originalName)}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(updates)
                });

                const result = await response.json();

                if (!result.success) {
                    statusDiv.className = 'upload-status error';
                    statusDiv.textContent = result.message;
                    btn.disabled = false;
                    btn.textContent = 'Save Changes';
                    return;
                }

                // Use the new name for subsequent operations if renamed
                const programName = updates.new_name || originalName;

                // If ZIP file is provided, upload it after config is saved
                if (zipFile) {
                    statusDiv.textContent = 'Configuration saved. Uploading ZIP file...';

                    const formData = new FormData();
                    formData.append('zipfile', zipFile);

                    const updateResponse = await fetch(`/api/update/${encodeURIComponent(programName)}`, {
                        method: 'POST',
                        body: formData
                    });

                    const updateResult = await updateResponse.json();

                    if (!updateResult.success) {
                        statusDiv.className = 'upload-status error';
                        statusDiv.textContent = `Config saved but ZIP upload failed: ${updateResult.message}`;
                        btn.disabled = false;
                        btn.textContent = 'Save Changes';
                        return;
                    }

                    statusDiv.className = 'upload-status success';
                    statusDiv.textContent = 'Configuration saved and code updated!';
                } else {
                    statusDiv.className = 'upload-status success';
                    statusDiv.textContent = result.message;
                }

                setTimeout(() => {
                    closeEditModal();
                    fetchStatus();
                }, 1500);
            } catch (error) {
                statusDiv.style.display = 'block';
                statusDiv.className = 'upload-status error';
                statusDiv.textContent = `Error: ${error.message}`;
            } finally {
                btn.disabled = false;
                btn.textContent = 'Save Changes';
            }
        }

        // New Program Modal Functions
        function openAddModal() {
            document.getElementById('addForm').reset();
            document.getElementById('addZipFile').value = '';  // Ensure file input is cleared
            document.getElementById('addEnabled').checked = true;
            document.getElementById('addStatus').style.display = 'none';
            document.getElementById('addModal').classList.add('active');
        }

        function closeAddModal() {
            document.getElementById('addModal').classList.remove('active');
        }

        async function handleAdd(event) {
            event.preventDefault();
            const btn = document.getElementById('addBtn');
            const statusDiv = document.getElementById('addStatus');

            btn.disabled = true;
            statusDiv.style.display = 'none';

            const zipFile = document.getElementById('addZipFile').files[0];
            const argsStr = document.getElementById('addArgs').value.trim();
            const envStr = document.getElementById('addEnvironment').value.trim();

            try {
                let response, result;

                if (zipFile) {
                    // Use upload API with FormData for ZIP files
                    btn.textContent = 'Uploading...';
                    const formData = new FormData();
                    formData.append('name', document.getElementById('addProgramName').value);
                    formData.append('script', document.getElementById('addScript').value);
                    formData.append('zipfile', zipFile);
                    formData.append('comment', document.getElementById('addComment').value || '');
                    formData.append('args', argsStr);
                    formData.append('environment', envStr);
                    if (document.getElementById('addEnabled').checked) {
                        formData.append('enabled', 'on');
                    }

                    response = await fetch('/api/upload', {
                        method: 'POST',
                        body: formData
                    });
                } else {
                    // Use add API with JSON for manual programs
                    btn.textContent = 'Creating...';
                    const data = {
                        name: document.getElementById('addProgramName').value,
                        script: document.getElementById('addScript').value,
                        comment: document.getElementById('addComment').value || null,
                        venv: document.getElementById('addVenv').value || null,
                        cwd: document.getElementById('addCwd').value || null,
                        args: argsStr ? argsStr.split(/\\s+/) : null,
                        environment: envStr ? envStr.split('\\n').map(l => l.trim()).filter(l => l) : null,
                        enabled: document.getElementById('addEnabled').checked
                    };

                    response = await fetch('/api/add', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });
                }

                result = await response.json();

                statusDiv.style.display = 'block';
                if (result.success) {
                    statusDiv.className = 'upload-status success';
                    statusDiv.textContent = zipFile
                        ? result.message + ' Installing in background. Check logs for progress.'
                        : result.message;
                    setTimeout(() => {
                        closeAddModal();
                        fetchStatus();
                    }, 1500);
                } else {
                    statusDiv.className = 'upload-status error';
                    statusDiv.textContent = result.message;
                }
            } catch (error) {
                statusDiv.style.display = 'block';
                statusDiv.className = 'upload-status error';
                statusDiv.textContent = `Error: ${error.message}`;
            } finally {
                btn.disabled = false;
                btn.textContent = 'Create Program';
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
