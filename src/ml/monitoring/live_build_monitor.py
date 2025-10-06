#!/usr/bin/env python3

import threading
import time
import re
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime

class LiveBuildMonitor:
    """Real-time build monitoring with ML-driven corrections and internet searches"""
    
    def __init__(self, db_manager, ml_engine):
        self.db_manager = db_manager
        self.ml_engine = ml_engine
        self.logger = logging.getLogger(__name__)
        
        self.active_monitors = {}
        self.error_patterns = [
            r'error:\s*(.+?)(?:\n|$)',
            r'fatal error:\s*(.+?)(?:\n|$)',
            r'undefined reference to\s*[`\'"](.+?)[`\'"]',
            r'No such file or directory:\s*(.+?)(?:\n|$)',
            r'command not found:\s*(.+?)(?:\n|$)',
            r'configure:\s*error:\s*(.+?)(?:\n|$)',
            r'make.*Error\s+(\d+)',
            r'compilation terminated'
        ]
        
        self.correction_callbacks = []
    
    def start_monitoring(self, build_id: str, stage_name: str = None):
        """Start real-time monitoring for a build"""
        if build_id in self.active_monitors:
            return
        
        monitor_thread = threading.Thread(
            target=self._monitor_build_logs,
            args=(build_id, stage_name),
            daemon=True
        )
        
        self.active_monitors[build_id] = {
            'thread': monitor_thread,
            'active': True,
            'last_position': 0,
            'errors_detected': [],
            'corrections_attempted': []
        }
        
        monitor_thread.start()
        self.logger.info(f"Started live monitoring for build {build_id}")
    
    def stop_monitoring(self, build_id: str):
        """Stop monitoring for a build"""
        if build_id in self.active_monitors:
            self.active_monitors[build_id]['active'] = False
            del self.active_monitors[build_id]
            self.logger.info(f"Stopped monitoring for build {build_id}")
    
    def _monitor_build_logs(self, build_id: str, stage_name: str):
        """Monitor build logs in real-time"""
        while self.active_monitors.get(build_id, {}).get('active', False):
            try:
                # Get latest log entries
                new_logs = self._get_new_log_entries(build_id)
                
                if new_logs:
                    # Analyze logs for errors
                    errors = self._detect_errors(new_logs)
                    
                    for error in errors:
                        self._handle_detected_error(build_id, stage_name, error, new_logs)
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                self.logger.error(f"Error monitoring build {build_id}: {e}")
                time.sleep(5)
    
    def _get_new_log_entries(self, build_id: str) -> List[str]:
        """Get new log entries since last check"""
        try:
            # Get latest build documents (logs)
            result = self.db_manager.execute_query("""
                SELECT content FROM build_documents 
                WHERE build_id = %s AND document_type = 'log'
                ORDER BY created_at DESC LIMIT 1
            """, (build_id,), fetch=True)
            
            if not result:
                return []
            
            log_content = result[0]['content']
            monitor_info = self.active_monitors.get(build_id, {})
            last_pos = monitor_info.get('last_position', 0)
            
            if len(log_content) > last_pos:
                new_content = log_content[last_pos:]
                self.active_monitors[build_id]['last_position'] = len(log_content)
                return new_content.split('\n')
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get new log entries: {e}")
            return []
    
    def _detect_errors(self, log_lines: List[str]) -> List[Dict]:
        """Detect errors in log lines"""
        errors = []
        
        for line in log_lines:
            for pattern in self.error_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    error = {
                        'line': line.strip(),
                        'pattern': pattern,
                        'match': match.group(1) if match.groups() else match.group(0),
                        'timestamp': datetime.now().isoformat(),
                        'severity': self._assess_error_severity(line)
                    }
                    errors.append(error)
                    break
        
        return errors
    
    def _assess_error_severity(self, error_line: str) -> str:
        """Assess error severity"""
        if any(word in error_line.lower() for word in ['fatal', 'critical', 'abort']):
            return 'critical'
        elif any(word in error_line.lower() for word in ['error', 'failed', 'undefined']):
            return 'high'
        elif any(word in error_line.lower() for word in ['warning', 'deprecated']):
            return 'medium'
        else:
            return 'low'
    
    def _handle_detected_error(self, build_id: str, stage_name: str, error: Dict, context_logs: List[str]):
        """Handle detected error with ML-driven response"""
        try:
            error_key = f"{error['match'][:50]}_{error['severity']}"
            
            # Avoid duplicate processing
            if error_key in self.active_monitors[build_id]['errors_detected']:
                return
            
            self.active_monitors[build_id]['errors_detected'].append(error_key)
            
            self.logger.warning(f"Detected {error['severity']} error in build {build_id}: {error['match']}")
            
            # Only attempt corrections for high/critical errors
            if error['severity'] in ['high', 'critical']:
                self._attempt_error_correction(build_id, stage_name, error, context_logs)
            
        except Exception as e:
            self.logger.error(f"Error handling detected error: {e}")
    
    def _attempt_error_correction(self, build_id: str, stage_name: str, error: Dict, context_logs: List[str]):
        """Attempt to correct error using ML and internet search"""
        try:
            # Search for solutions
            solutions = self.ml_engine.search_error_solutions(
                error['line'], 
                stage_name or 'unknown',
                self._extract_package_name(context_logs)
            )
            
            if solutions:
                self.logger.info(f"Found {len(solutions)} potential solutions for error")
                
                # Store correction attempt
                correction = {
                    'build_id': build_id,
                    'error': error,
                    'solutions_found': len(solutions),
                    'timestamp': datetime.now().isoformat(),
                    'top_solution': solutions[0] if solutions else None
                }
                
                self.active_monitors[build_id]['corrections_attempted'].append(correction)
                
                # Notify correction callbacks
                for callback in self.correction_callbacks:
                    try:
                        callback(build_id, error, solutions)
                    except Exception as e:
                        self.logger.error(f"Correction callback failed: {e}")
                
                # Store in database
                self._store_live_correction(build_id, correction)
            
        except Exception as e:
            self.logger.error(f"Error correction attempt failed: {e}")
    
    def _extract_package_name(self, context_logs: List[str]) -> Optional[str]:
        """Extract package name from context logs"""
        for line in context_logs[-10:]:  # Check last 10 lines
            # Look for common package patterns
            patterns = [
                r'Building\s+(\w+)',
                r'Configuring\s+(\w+)',
                r'Making\s+(\w+)',
                r'/([^/\s]+)\.tar\.',
                r'cd\s+([^/\s]+)-[\d\.]+'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    return match.group(1)
        
        return None
    
    def _store_live_correction(self, build_id: str, correction: Dict):
        """Store live correction attempt in database"""
        try:
            # Create table if not exists
            self.db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS ml_live_corrections (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    build_id VARCHAR(50) NOT NULL,
                    error_message TEXT,
                    error_severity VARCHAR(20),
                    solutions_found INT DEFAULT 0,
                    correction_data JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_build_id (build_id)
                )
            """)
            
            # Insert correction data
            self.db_manager.execute_query("""
                INSERT INTO ml_live_corrections 
                (build_id, error_message, error_severity, solutions_found, correction_data)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                build_id,
                correction['error']['line'][:500],
                correction['error']['severity'],
                correction['solutions_found'],
                self._safe_json_dumps(correction)
            ))
            
        except Exception as e:
            self.logger.error(f"Failed to store live correction: {e}")
    
    def _safe_json_dumps(self, data):
        """Safe JSON serialization"""
        try:
            import json
            return json.dumps(data, default=str)
        except:
            return str(data)
    
    def register_correction_callback(self, callback: Callable):
        """Register callback for when corrections are found"""
        self.correction_callbacks.append(callback)
    
    def get_monitoring_status(self) -> Dict:
        """Get current monitoring status"""
        return {
            'active_builds': list(self.active_monitors.keys()),
            'total_monitors': len(self.active_monitors),
            'monitoring_stats': {
                build_id: {
                    'errors_detected': len(info['errors_detected']),
                    'corrections_attempted': len(info['corrections_attempted'])
                }
                for build_id, info in self.active_monitors.items()
            }
        }