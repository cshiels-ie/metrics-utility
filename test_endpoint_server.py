#!/usr/bin/env python3
"""
Simple test HTTP server to receive JSON reports.
"""

import json
import time

from http.server import BaseHTTPRequestHandler, HTTPServer


class ReportReceiver(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            json_data = json.loads(post_data.decode('utf-8'))

            print(f'📥 Received report from {self.client_address[0]}')
            print(f'📊 Report type: {json_data.get("report_metadata", {}).get("report_type", "unknown")}')
            print(f'📏 Data size: {len(post_data)} bytes')
            print(f'🔍 Headers: {dict(self.headers)}')

            # Show some metrics summary
            metadata = json_data.get('report_metadata', {})
            print(f'📅 Generated at: {metadata.get("generated_at", "unknown")}')
            print(f'📋 Total JSON files: {metadata.get("total_json_files", 0)}')

            # Return success response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            response = {
                'status': 'success',
                'message': 'Report received successfully',
                'received_at': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'size': len(post_data),
            }

            self.wfile.write(json.dumps(response).encode('utf-8'))

        except json.JSONDecodeError:
            print(f'❌ Invalid JSON received from {self.client_address[0]}')
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid JSON"}')
        except Exception as e:
            print(f'❌ Error processing request: {e}')
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Internal server error"}')

    def log_message(self, format, *args):
        # Suppress default logging
        pass


def start_test_server(port=8080):
    """Start the test server."""
    print(f'🚀 Starting test endpoint server on port {port}')
    print(f'📡 Endpoint URL: http://localhost:{port}/reports')
    print('🔄 Waiting for reports...')
    print()

    server = HTTPServer(('localhost', port), ReportReceiver)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n🛑 Server stopped')
        server.shutdown()


if __name__ == '__main__':
    start_test_server()
