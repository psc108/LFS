from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path

class IntegratedFaultAnalyzer:
    """Enhanced fault analyzer with database integration for all system components"""
    
    def __init__(self, db_manager, build_engine=None, parallel_engine=None, api_server=None):
        self.db = db_manager
        self.build_engine = build_engine
        self.parallel_engine = parallel_engine
        self.api_server = api_server
        self.analysis_cache = {}
        
        # Initialize analysis tables
        self._init_analysis_tables()
    
    def start_comprehensive_analysis(self, analysis_config: dict, scope: str) -> str:
        """Start comprehensive analysis and return analysis ID"""
        import uuid
        analysis_id = f"analysis-{uuid.uuid4().hex[:8]}"
        
        # Store analysis configuration
        try:
            conn = self.db.connect()
            if conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO analysis_results 
                    (build_id, component_type, analysis_type, risk_score, findings)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    analysis_id, 'build', 'comprehensive', 0,
                    json.dumps(analysis_config)
                ))
                
                conn.commit()
                cursor.close()
            
        except Exception as e:
            print(f"Error storing analysis config: {e}")
        
        return analysis_id

    def _init_analysis_tables(self):
        """Initialize database tables for fault analysis"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Fault patterns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fault_patterns (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    pattern_name VARCHAR(255) NOT NULL,
                    pattern_type ENUM('build', 'system', 'network', 'security', 'performance') NOT NULL,
                    pattern_regex TEXT,
                    severity ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL,
                    auto_fix_command TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_pattern_type (pattern_type),
                    INDEX idx_severity (severity)
                )
            """)
            
            # Analysis results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    build_id VARCHAR(255),
                    component_type ENUM('build', 'parallel', 'api', 'security', 'deployment') NOT NULL,
                    analysis_type VARCHAR(100) NOT NULL,
                    risk_score INT DEFAULT 0,
                    findings JSON,
                    recommendations JSON,
                    auto_fixes_applied JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_build_id (build_id),
                    INDEX idx_component_type (component_type),
                    INDEX idx_risk_score (risk_score)
                )
            """)
            
            # System health metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_health_metrics (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    metric_type VARCHAR(100) NOT NULL,
                    metric_value DECIMAL(10,4),
                    threshold_warning DECIMAL(10,4),
                    threshold_critical DECIMAL(10,4),
                    status ENUM('OK', 'WARNING', 'CRITICAL') NOT NULL,
                    metadata JSON,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_metric_type (metric_type),
                    INDEX idx_status (status),
                    INDEX idx_recorded_at (recorded_at)
                )
            """)
            
            conn.commit()
            cursor.close()
            
        except Exception as e:
            print(f"Error initializing analysis tables: {e}")
    
    def analyze_build_failure(self, build_id: str, error_logs: str) -> Dict:
        """Analyze build failure with enhanced pattern recognition"""
        try:
            patterns = self._get_fault_patterns('build')
            findings = []
            risk_score = 0
            
            for pattern in patterns:
                if self._match_pattern(error_logs, pattern):
                    finding = {
                        'pattern_name': pattern['pattern_name'],
                        'severity': pattern['severity'],
                        'description': pattern['description'],
                        'auto_fix': pattern['auto_fix_command'],
                        'matched_text': self._extract_match(error_logs, pattern)
                    }
                    findings.append(finding)
                    
                    # Calculate risk score
                    severity_scores = {'LOW': 10, 'MEDIUM': 25, 'HIGH': 50, 'CRITICAL': 100}
                    risk_score += severity_scores.get(pattern['severity'], 0)
            
            # Store analysis results
            self._store_analysis_result(build_id, 'build', 'failure_analysis', 
                                      min(risk_score, 100), findings)
            
            return {
                'build_id': build_id,
                'risk_score': min(risk_score, 100),
                'findings': findings,
                'recommendations': self._generate_recommendations(findings),
                'auto_fixes': self._get_auto_fixes(findings)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_parallel_build_performance(self, task_data: List[Dict]) -> Dict:
        """Analyze parallel build performance and resource utilization"""
        try:
            findings = []
            risk_score = 0
            
            # Analyze task distribution
            total_tasks = len(task_data)
            failed_tasks = len([t for t in task_data if t.get('status') == 'failed'])
            avg_duration = sum(t.get('duration', 0) for t in task_data) / total_tasks if total_tasks > 0 else 0
            
            # Check for performance issues
            if failed_tasks / total_tasks > 0.1:  # >10% failure rate
                findings.append({
                    'type': 'high_failure_rate',
                    'severity': 'HIGH',
                    'description': f'High task failure rate: {failed_tasks}/{total_tasks} ({failed_tasks/total_tasks*100:.1f}%)',
                    'recommendation': 'Review task dependencies and resource allocation'
                })
                risk_score += 50
            
            if avg_duration > 300:  # >5 minutes average
                findings.append({
                    'type': 'slow_tasks',
                    'severity': 'MEDIUM',
                    'description': f'Slow average task duration: {avg_duration:.1f} seconds',
                    'recommendation': 'Consider optimizing build scripts or increasing resources'
                })
                risk_score += 25
            
            # Store analysis results
            self._store_analysis_result(None, 'parallel', 'performance_analysis', 
                                      min(risk_score, 100), findings)
            
            return {
                'total_tasks': total_tasks,
                'failed_tasks': failed_tasks,
                'avg_duration': avg_duration,
                'risk_score': min(risk_score, 100),
                'findings': findings
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_api_security(self, request_logs: List[Dict]) -> Dict:
        """Analyze API security and detect potential threats"""
        try:
            findings = []
            risk_score = 0
            
            # Analyze request patterns
            failed_auth_count = len([r for r in request_logs if r.get('status_code') == 401])
            suspicious_ips = self._detect_suspicious_ips(request_logs)
            rate_limit_violations = self._detect_rate_limit_violations(request_logs)
            
            if failed_auth_count > 10:
                findings.append({
                    'type': 'authentication_failures',
                    'severity': 'HIGH',
                    'description': f'High number of authentication failures: {failed_auth_count}',
                    'recommendation': 'Review authentication logs and consider IP blocking'
                })
                risk_score += 40
            
            if suspicious_ips:
                findings.append({
                    'type': 'suspicious_activity',
                    'severity': 'CRITICAL',
                    'description': f'Suspicious IP activity detected: {len(suspicious_ips)} IPs',
                    'recommendation': 'Implement IP filtering and enhanced monitoring'
                })
                risk_score += 75
            
            # Store analysis results
            self._store_analysis_result(None, 'api', 'security_analysis', 
                                      min(risk_score, 100), findings)
            
            return {
                'failed_auth_count': failed_auth_count,
                'suspicious_ips': len(suspicious_ips),
                'risk_score': min(risk_score, 100),
                'findings': findings
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_deployment_health(self, deployment_data: Dict) -> Dict:
        """Analyze deployment health and ISO generation status"""
        try:
            findings = []
            risk_score = 0
            
            # Check ISO generation success rate
            iso_success_rate = deployment_data.get('iso_success_rate', 100)
            vm_creation_errors = deployment_data.get('vm_creation_errors', 0)
            network_boot_failures = deployment_data.get('network_boot_failures', 0)
            
            if iso_success_rate < 90:
                findings.append({
                    'type': 'iso_generation_issues',
                    'severity': 'HIGH',
                    'description': f'Low ISO generation success rate: {iso_success_rate}%',
                    'recommendation': 'Check filesystem integrity and available disk space'
                })
                risk_score += 45
            
            if vm_creation_errors > 0:
                findings.append({
                    'type': 'vm_creation_failures',
                    'severity': 'MEDIUM',
                    'description': f'VM creation errors: {vm_creation_errors}',
                    'recommendation': 'Verify hypervisor compatibility and resource availability'
                })
                risk_score += 30
            
            # Store analysis results
            self._store_analysis_result(None, 'deployment', 'health_analysis', 
                                      min(risk_score, 100), findings)
            
            return {
                'iso_success_rate': iso_success_rate,
                'vm_creation_errors': vm_creation_errors,
                'network_boot_failures': network_boot_failures,
                'risk_score': min(risk_score, 100),
                'findings': findings
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_system_health_dashboard(self) -> Dict:
        """Get comprehensive system health dashboard"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Get recent analysis results
            cursor.execute("""
                SELECT component_type, analysis_type, AVG(risk_score) as avg_risk,
                       COUNT(*) as analysis_count
                FROM analysis_results 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                GROUP BY component_type, analysis_type
            """)
            
            analysis_summary = {}
            for row in cursor.fetchall():
                component = row[0]
                if component not in analysis_summary:
                    analysis_summary[component] = {}
                analysis_summary[component][row[1]] = {
                    'avg_risk_score': round(row[2], 2),
                    'analysis_count': row[3]
                }
            
            # Get system health metrics
            cursor.execute("""
                SELECT metric_type, AVG(metric_value) as avg_value, 
                       COUNT(CASE WHEN status = 'CRITICAL' THEN 1 END) as critical_count,
                       COUNT(CASE WHEN status = 'WARNING' THEN 1 END) as warning_count
                FROM system_health_metrics 
                WHERE recorded_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
                GROUP BY metric_type
            """)
            
            health_metrics = {}
            for row in cursor.fetchall():
                health_metrics[row[0]] = {
                    'avg_value': round(row[1], 2),
                    'critical_alerts': row[2],
                    'warning_alerts': row[3]
                }
            
            cursor.close()
            
            return {
                'analysis_summary': analysis_summary,
                'health_metrics': health_metrics,
                'overall_health': self._calculate_overall_health(analysis_summary, health_metrics),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_fault_patterns(self, pattern_type: str) -> List[Dict]:
        """Get fault patterns from database"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT pattern_name, pattern_regex, severity, auto_fix_command, description
                FROM fault_patterns 
                WHERE pattern_type = %s
            """, (pattern_type,))
            
            patterns = []
            for row in cursor.fetchall():
                patterns.append({
                    'pattern_name': row[0],
                    'pattern_regex': row[1],
                    'severity': row[2],
                    'auto_fix_command': row[3],
                    'description': row[4]
                })
            
            cursor.close()
            return patterns
            
        except Exception as e:
            print(f"Error getting fault patterns: {e}")
            return []
    
    def _match_pattern(self, text: str, pattern: Dict) -> bool:
        """Match text against fault pattern"""
        import re
        try:
            if pattern['pattern_regex']:
                return bool(re.search(pattern['pattern_regex'], text, re.IGNORECASE))
            return False
        except:
            return False
    
    def _extract_match(self, text: str, pattern: Dict) -> str:
        """Extract matched text from pattern"""
        import re
        try:
            if pattern['pattern_regex']:
                match = re.search(pattern['pattern_regex'], text, re.IGNORECASE)
                return match.group(0) if match else ""
            return ""
        except:
            return ""
    
    def _store_analysis_result(self, build_id: str, component_type: str, 
                             analysis_type: str, risk_score: int, findings: List[Dict]):
        """Store analysis result in database"""
        try:
            conn = self.db.connect()
            if conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO analysis_results 
                    (build_id, component_type, analysis_type, risk_score, findings, recommendations)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    build_id, component_type, analysis_type, risk_score,
                    json.dumps(findings), json.dumps(self._generate_recommendations(findings))
                ))
                
                conn.commit()
                cursor.close()
            
        except Exception as e:
            print(f"Error storing analysis result: {e}")
    
    def _generate_recommendations(self, findings: List[Dict]) -> List[str]:
        """Generate recommendations based on findings"""
        recommendations = []
        for finding in findings:
            if 'recommendation' in finding:
                recommendations.append(finding['recommendation'])
        return list(set(recommendations))  # Remove duplicates
    
    def _get_auto_fixes(self, findings: List[Dict]) -> List[str]:
        """Get auto-fix commands from findings"""
        auto_fixes = []
        for finding in findings:
            if finding.get('auto_fix'):
                auto_fixes.append(finding['auto_fix'])
        return auto_fixes
    
    def _detect_suspicious_ips(self, request_logs: List[Dict]) -> List[str]:
        """Detect suspicious IP addresses"""
        ip_counts = {}
        for log in request_logs:
            ip = log.get('ip', '')
            if ip:
                ip_counts[ip] = ip_counts.get(ip, 0) + 1
        
        # IPs with >100 requests in the analyzed period
        return [ip for ip, count in ip_counts.items() if count > 100]
    
    def _detect_rate_limit_violations(self, request_logs: List[Dict]) -> int:
        """Detect rate limit violations"""
        return len([r for r in request_logs if r.get('status_code') == 429])
    
    def _calculate_overall_health(self, analysis_summary: Dict, health_metrics: Dict) -> str:
        """Calculate overall system health status"""
        critical_issues = 0
        warning_issues = 0
        
        # Count analysis issues
        for component in analysis_summary.values():
            for analysis in component.values():
                if analysis['avg_risk_score'] > 75:
                    critical_issues += 1
                elif analysis['avg_risk_score'] > 50:
                    warning_issues += 1
        
        # Count health metric issues
        for metric in health_metrics.values():
            critical_issues += metric['critical_alerts']
            warning_issues += metric['warning_alerts']
        
        if critical_issues > 0:
            return 'CRITICAL'
        elif warning_issues > 0:
            return 'WARNING'
        else:
            return 'HEALTHY'