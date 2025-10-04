from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import json
from datetime import datetime
from typing import Dict, List

class LFSBuildAPI:
    def __init__(self, build_engine, db_manager, repo_manager, fault_analyzer=None):
        self.app = Flask(__name__)
        CORS(self.app)
        self.build_engine = build_engine
        self.db = db_manager
        self.repo = repo_manager
        self.fault_analyzer = fault_analyzer
        self.request_logs = []
        self.setup_routes()
        self.setup_request_logging()
    
    def setup_routes(self):
        @self.app.route('/api/builds', methods=['GET'])
        def list_builds():
            try:
                builds = self.db.get_all_builds()
                return jsonify({'success': True, 'builds': builds})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/builds', methods=['POST'])
        def create_build():
            try:
                data = request.get_json()
                config_name = data.get('config_name')
                config_content = data.get('config_content')
                
                if not config_name or not config_content:
                    return jsonify({'success': False, 'error': 'Missing config_name or config_content'}), 400
                
                config_path = self.repo.add_build_config(config_name, config_content)
                build_id = self.build_engine.start_build(config_path)
                
                return jsonify({'success': True, 'build_id': build_id})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/builds/<build_id>', methods=['GET'])
        def get_build(build_id):
            try:
                build_details = self.build_engine.get_build_status(build_id)
                return jsonify({'success': True, 'build': build_details})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/builds/<build_id>/cancel', methods=['POST'])
        def cancel_build(build_id):
            try:
                self.build_engine.cancel_build(build_id)
                return jsonify({'success': True, 'message': 'Build cancelled'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/system/status', methods=['GET'])
        def get_system_status():
            try:
                import psutil
                
                status = {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory': dict(psutil.virtual_memory()._asdict()),
                    'disk': dict(psutil.disk_usage('/')._asdict()),
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify({'success': True, 'status': status})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/analysis/health', methods=['GET'])
        def get_health_analysis():
            try:
                if self.fault_analyzer:
                    health_data = self.fault_analyzer.get_system_health_dashboard()
                    return jsonify({'success': True, 'health': health_data})
                else:
                    return jsonify({'success': False, 'error': 'Fault analyzer not available'}), 503
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/analysis/security', methods=['GET'])
        def get_security_analysis():
            try:
                if self.fault_analyzer:
                    security_data = self.fault_analyzer.analyze_api_security(self.request_logs[-1000:])
                    return jsonify({'success': True, 'security': security_data})
                else:
                    return jsonify({'success': False, 'error': 'Fault analyzer not available'}), 503
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
    
    def setup_request_logging(self):
        @self.app.before_request
        def log_request():
            request_data = {
                'ip': request.remote_addr,
                'method': request.method,
                'path': request.path,
                'timestamp': datetime.now().isoformat(),
                'user_agent': request.headers.get('User-Agent', '')
            }
            self.request_logs.append(request_data)
            
            # Keep only last 10000 requests
            if len(self.request_logs) > 10000:
                self.request_logs = self.request_logs[-5000:]
        
        @self.app.after_request
        def log_response(response):
            if self.request_logs:
                self.request_logs[-1]['status_code'] = response.status_code
            return response
    
    def run_async(self, host='0.0.0.0', port=5000):
        def run_server():
            self.app.run(host=host, port=port, debug=False, threaded=True)
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        return thread