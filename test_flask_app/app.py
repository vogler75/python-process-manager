#!/usr/bin/env python3
"""
Simple Flask test application for Process Manager upload testing.
"""
import argparse
import time
from datetime import datetime
from flask import Flask, jsonify
import requests

app = Flask(__name__)

# Global counter
request_counter = 0


@app.route('/')
def home():
    global request_counter
    request_counter += 1
    return jsonify({
        'message': 'Hello from uploaded Flask app!',
        'timestamp': datetime.now().isoformat(),
        'request_count': request_counter,
        'status': 'running'
    })


@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'uptime': time.process_time(),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/test-requests')
def test_requests():
    """Test the requests library dependency."""
    try:
        response = requests.get('https://httpbin.org/json', timeout=5)
        return jsonify({
            'message': 'Successfully used requests library',
            'status_code': response.status_code,
            'content_type': response.headers.get('Content-Type')
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


def main():
    parser = argparse.ArgumentParser(description='Flask Test App')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on (default: 5000)')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    print(f"Starting Flask test app...")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Debug: {args.debug}")
    print(f"Started at: {datetime.now().isoformat()}")
    print("-" * 50)

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
