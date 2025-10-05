import json
import socket
import threading
from datetime import datetime
from typing import Dict, List
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs

class SimpleAPIHandler(http.server.BaseHTTPRequestHandler):
    """Simple HTTP handler for basic API functionality"""
    
    def __init__(self, api_instance, *args, **kwargs):
        self.api = api_instance
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
            if path == '/api/status':
                response = self.api.get_system_status()
            elif path == '/api/builds':
                response = self.api.get_builds_summary()
            elif path == '/api/health':
                response = self.api.get_health_summary()
            else:
                response = {'error': 'Endpoint not found'}
                self.send_response(404)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

class LFSBuildAPI:
    """Lightweight API for LFS build system status and monitoring"""
    
    def __init__(self, build_engine=None, db_manager=None, repo_manager=None, fault_analyzer=None):
        self.build_engine = build_engine
        self.db = db_manager
        self.repo = repo_manager
        self.fault_analyzer = fault_analyzer
        self.request_logs = []
    
    def get_system_status(self) -> Dict:
        """Get basic system status"""
        try:
            import psutil
            return {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'timestamp': datetime.now().isoformat(),
                'status': 'running'
            }
        except Exception as e:
            return {'error': str(e), 'status': 'error'}
    
    def get_builds_summary(self) -> Dict:
        """Get builds summary"""
        try:
            if self.db:
                builds = self.db.get_all_builds()
                return {
                    'total_builds': len(builds),
                    'recent_builds': builds[-5:] if builds else [],
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'total_builds': 0, 'recent_builds': []}
        except Exception as e:
            return {'error': str(e)}
    
    def get_health_summary(self) -> Dict:
        """Get health summary"""
        try:
            if self.fault_analyzer:
                health_data = self.fault_analyzer.get_system_health_dashboard()
                return {
                    'overall_health': health_data.get('overall_health', 'UNKNOWN'),
                    'analysis_count': len(health_data.get('analysis_summary', {})),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'overall_health': 'NO_ANALYZER', 'analysis_count': 0}
        except Exception as e:
            return {'error': str(e)}

class APIServer:
    """Lightweight API server for monitoring and status"""
    
    def __init__(self):
        self.api_instance = None
        self.server = None
        self.server_thread = None
        self.port = 5000
        self.running = False
    
    def start_server(self, port: int = 5000) -> int:
        """Start the lightweight API server"""
        if self.running:
            return self.port
        
        try:
            # Create API instance (no heavy dependencies needed)
            self.api_instance = LFSBuildAPI()
            self.port = port
            
            # Create simple HTTP server
            handler = lambda *args, **kwargs: SimpleAPIHandler(self.api_instance, *args, **kwargs)
            
            # Find available port
            for attempt_port in range(port, port + 10):
                try:
                    self.server = socketserver.TCPServer(("", attempt_port), handler)
                    self.port = attempt_port
                    break
                except OSError:
                    continue
            
            if not self.server:
                raise Exception("No available ports found")
            
            # Start server in background thread
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.running = True
            
            return self.port
            
        except Exception as e:
            raise Exception(f"Failed to start API server: {str(e)}")
    
    def stop_server(self):
        """Stop the API server"""
        if self.running and self.server:
            self.server.shutdown()
            self.server.server_close()
            self.running = False
    
    def is_running(self) -> bool:
        """Check if server is running"""
        return self.running
    
    def get_status(self) -> dict:
        """Get server status"""
        return {
            'running': self.running,
            'port': self.port if self.running else None,
            'type': 'lightweight_http',
            'endpoints': [
                'GET /api/status - System status',
                'GET /api/builds - Builds summary', 
                'GET /api/health - Health summary'
            ] if self.running else []
        }