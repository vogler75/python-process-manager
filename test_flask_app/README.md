# Flask Test Application

A simple Flask web application for testing the Process Manager upload functionality.

## Features

- Simple HTTP server with multiple endpoints
- Uses external dependencies (Flask, requests)
- Supports command-line arguments
- Demonstrates a realistic Python web application

## Endpoints

- `GET /` - Returns a JSON greeting with request counter
- `GET /health` - Health check endpoint
- `GET /test-requests` - Tests the requests library

## Usage

```bash
python app.py --port 5000 --host 127.0.0.1
```

## Arguments

- `--port` - Port to run on (default: 5000)
- `--host` - Host to bind to (default: 127.0.0.1)
- `--debug` - Enable Flask debug mode
