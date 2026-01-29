"""Test to verify remote upload functionality"""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import time


class TestReportHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler to receive and validate reports"""
    
    received_reports = []
    
    def do_POST(self):
        """Handle POST requests with report data"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Parse and store the report
        report = json.loads(post_data.decode('utf-8'))
        TestReportHandler.received_reports.append(report)
        
        # Log what we received
        print(f"\n=== Received Report ===")
        print(f"Test count: {report['results']['summary']['tests']}")
        print(f"Passed: {report['results']['summary']['passed']}")
        print(f"Failed: {report['results']['summary']['failed']}")
        print(f"=====================\n")
        
        # Send success response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "success", "message": "Report received"}).encode())
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def start_test_server(port=8888):
    """Start a test HTTP server in background thread"""
    server = HTTPServer(('localhost', port), TestReportHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)  # Give server time to start
    return server


if __name__ == "__main__":
    # Start test server
    print("Starting test server on http://localhost:8888")
    server = start_test_server(8888)
    
    print("Server is running. Run pytest with:")
    print("  uv run pytest tests/test_plugin.py --custom-report --custom-report-url http://localhost:8888/reports")
    print("\nPress Ctrl+C to stop the server...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()
