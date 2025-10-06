#!/usr/bin/env python3

import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict, Counter

class LogAnalyzer:
    """Advanced log analysis for root cause detection"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.error_patterns = self._load_error_patterns()
        self.root_cause_rules = self._load_root_cause_rules()
        
    def _load_error_patterns(self) -> Dict:
        """Load common error patterns for LFS builds"""
        return {
            'compilation_errors': [
                r'error: (.+)',
                r'fatal error: (.+)',
                r'undefined reference to (.+)',
                r'No such file or directory: (.+)',
                r'Permission denied: (.+)'
            ],
            'dependency_errors': [
                r'configure: error: (.+) not found',
                r'Package (.+) was not found',
                r'library (.+) not found'
            ],
            'system_errors': [
                r'out of memory',
                r'disk full',
                r'no space left on device',
                r'connection refused',
                r'timeout'
            ],
            'permission_errors': [
                r'permission denied',
                r'operation not permitted',
                r'access denied'
            ]
        }
    
    def _load_root_cause_rules(self) -> Dict:
        """Load root cause analysis rules"""
        return {
            'missing_dependencies': {
                'patterns': ['not found', 'undefined reference', 'no such file'],
                'confidence': 0.9,
                'recommendation': 'Install missing dependencies or check package configuration'
            },
            'insufficient_permissions': {
                'patterns': ['permission denied', 'access denied', 'operation not permitted'],
                'confidence': 0.95,
                'recommendation': 'Check file permissions and sudo access'
            },
            'resource_exhaustion': {
                'patterns': ['out of memory', 'disk full', 'no space left'],
                'confidence': 0.9,
                'recommendation': 'Free up system resources or increase limits'
            },
            'network_issues': {
                'patterns': ['connection refused', 'timeout', 'network unreachable'],
                'confidence': 0.8,
                'recommendation': 'Check network connectivity and firewall settings'
            },
            'configuration_errors': {
                'patterns': ['configure: error', 'invalid option', 'bad configuration'],
                'confidence': 0.85,
                'recommendation': 'Review build configuration and parameters'
            }
        }
    
    def analyze_build_logs(self, build_id: str) -> Dict:
        """Perform comprehensive log analysis for root cause detection"""
        try:
            logs = self._get_build_logs(build_id)
            if not logs:
                return {'error': 'No logs found for build'}
            
            error_analysis = self._analyze_error_patterns(logs)
            root_causes = self._detect_root_causes(logs)
            timeline_analysis = self._analyze_failure_timeline(logs)
            recommendations = self._generate_recommendations(root_causes, error_analysis)
            
            return {
                'build_id': build_id,
                'analysis_timestamp': datetime.now().isoformat(),
                'error_analysis': error_analysis,
                'root_causes': root_causes,
                'timeline_analysis': timeline_analysis,
                'recommendations': recommendations,
                'confidence_score': self._calculate_confidence(root_causes)
            }
            
        except Exception as e:
            logging.error(f"Log analysis failed for build {build_id}: {e}")
            return {'error': str(e)}
    
    def _get_build_logs(self, build_id: str) -> List[Dict]:
        """Retrieve build logs from database"""
        if not self.db_manager:
            return []
        
        try:
            # Get all log documents for the build
            logs = self.db_manager.execute_query(
                "SELECT * FROM build_documents WHERE build_id = %s AND document_type IN ('log', 'output', 'error') ORDER BY created_at",
                (build_id,), fetch=True
            )
            
            # Also get stage logs
            stage_logs = self.db_manager.execute_query(
                "SELECT stage_name as title, output_log as content, start_time as created_at, 'stage_log' as document_type FROM build_stages WHERE build_id = %s AND output_log IS NOT NULL ORDER BY start_time",
                (build_id,), fetch=True
            )
            
            # Combine all logs
            all_logs = (logs or []) + (stage_logs or [])
            return all_logs
        except Exception as e:
            logging.error(f"Failed to retrieve logs for build {build_id}: {e}")
            return []
    
    def _analyze_error_patterns(self, logs: List[Dict]) -> Dict:
        """Analyze logs for error patterns"""
        error_counts = defaultdict(int)
        error_details = []
        
        for log in logs:
            content = log.get('content', '')
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines):
                for category, patterns in self.error_patterns.items():
                    for pattern in patterns:
                        matches = re.findall(pattern, line, re.IGNORECASE)
                        if matches:
                            error_counts[category] += len(matches)
                            error_details.append({
                                'category': category,
                                'line': line.strip(),
                                'match': matches[0] if matches else '',
                                'timestamp': log.get('created_at'),
                                'line_number': line_num + 1
                            })
        
        return {
            'error_counts': dict(error_counts),
            'error_details': error_details[:20],
            'total_errors': sum(error_counts.values())
        }
    
    def _detect_root_causes(self, logs: List[Dict]) -> List[Dict]:
        """Detect potential root causes using pattern matching"""
        root_causes = []
        all_content = '\n'.join([log.get('content', '') for log in logs])
        
        for cause_name, rule in self.root_cause_rules.items():
            pattern_matches = 0
            matched_patterns = []
            
            for pattern in rule['patterns']:
                matches = re.findall(pattern, all_content, re.IGNORECASE)
                if matches:
                    pattern_matches += len(matches)
                    matched_patterns.extend(matches[:3])
            
            if pattern_matches > 0:
                root_causes.append({
                    'cause': cause_name,
                    'confidence': rule['confidence'],
                    'match_count': pattern_matches,
                    'examples': matched_patterns,
                    'recommendation': rule['recommendation']
                })
        
        root_causes.sort(key=lambda x: (x['confidence'], x['match_count']), reverse=True)
        return root_causes[:5]
    
    def _analyze_failure_timeline(self, logs: List[Dict]) -> Dict:
        """Analyze the timeline of failures"""
        timeline = []
        
        for log in logs:
            timestamp = log.get('created_at')
            content = log.get('content', '')
            
            if any(keyword in content.lower() for keyword in ['error', 'failed', 'fatal']):
                timeline.append({
                    'timestamp': timestamp,
                    'stage': log.get('title', 'Unknown'),
                    'type': 'failure_indicator'
                })
        
        return {
            'failure_points': len(timeline),
            'timeline': timeline[-10:],
            'first_failure': timeline[0]['timestamp'] if timeline else None,
            'last_failure': timeline[-1]['timestamp'] if timeline else None
        }
    
    def _generate_recommendations(self, root_causes: List[Dict], error_analysis: Dict) -> List[Dict]:
        """Generate actionable recommendations"""
        recommendations = []
        
        for cause in root_causes[:3]:
            recommendations.append({
                'type': 'root_cause',
                'priority': 'high' if cause['confidence'] > 0.8 else 'medium',
                'title': f"Address {cause['cause'].replace('_', ' ').title()}",
                'description': cause['recommendation'],
                'confidence': cause['confidence']
            })
        
        error_counts = error_analysis.get('error_counts', {})
        if error_counts.get('compilation_errors', 0) > 5:
            recommendations.append({
                'type': 'compilation',
                'priority': 'high',
                'title': 'Multiple Compilation Errors Detected',
                'description': 'Review compiler settings and source code compatibility',
                'confidence': 0.8
            })
        
        return recommendations
    
    def _calculate_confidence(self, root_causes: List[Dict]) -> float:
        """Calculate overall confidence score"""
        if not root_causes:
            return 0.0
        
        total_weight = sum(cause['confidence'] * cause['match_count'] for cause in root_causes)
        total_matches = sum(cause['match_count'] for cause in root_causes)
        
        return min(total_weight / total_matches if total_matches > 0 else 0.0, 1.0)