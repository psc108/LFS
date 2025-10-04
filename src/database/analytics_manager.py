#!/usr/bin/env python3
"""
Advanced Analytics Manager for LFS Build System
Provides comprehensive data analysis and insights
"""

import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from .db_manager import DatabaseManager

class AnalyticsManager:
    """Advanced analytics and data insights manager"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_build_success_trends(self, days: int = 30) -> Dict:
        """Analyze build success trends over time"""
        try:
            data = self.db.execute_query("""
                SELECT 
                    DATE(start_time) as date,
                    COUNT(*) as total_builds,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                    AVG(duration_seconds) as avg_duration,
                    AVG(completed_stages) as avg_stages_completed
                FROM builds 
                WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(start_time)
                ORDER BY date
            """, (days,), fetch=True)
            
            # Calculate trends
            success_rates = []
            durations = []
            
            for row in data:
                if row['total_builds'] > 0:
                    success_rate = (row['successful'] / row['total_builds']) * 100
                    success_rates.append(success_rate)
                    durations.append(row['avg_duration'] or 0)
            
            # Calculate trend direction
            success_trend = "stable"
            duration_trend = "stable"
            
            if len(success_rates) >= 7:
                recent_success = np.mean(success_rates[-7:])
                older_success = np.mean(success_rates[:-7]) if len(success_rates) > 7 else recent_success
                
                if recent_success > older_success + 5:
                    success_trend = "improving"
                elif recent_success < older_success - 5:
                    success_trend = "declining"
                
                recent_duration = np.mean(durations[-7:])
                older_duration = np.mean(durations[:-7]) if len(durations) > 7 else recent_duration
                
                if recent_duration > older_duration * 1.1:
                    duration_trend = "slower"
                elif recent_duration < older_duration * 0.9:
                    duration_trend = "faster"
            
            return {
                'daily_data': data,
                'success_trend': success_trend,
                'duration_trend': duration_trend,
                'overall_success_rate': np.mean(success_rates) if success_rates else 0,
                'avg_build_duration': np.mean(durations) if durations else 0
            }
            
        except Exception as e:
            print(f"Failed to analyze build trends: {e}")
            return {'daily_data': [], 'success_trend': 'unknown', 'duration_trend': 'unknown'}
    
    def get_stage_performance_analysis(self, stage_name: str = None, days: int = 30) -> Dict:
        """Analyze stage performance patterns"""
        try:
            where_clause = "WHERE sp.end_time >= DATE_SUB(NOW(), INTERVAL %s DAY)"
            params = [days]
            
            if stage_name:
                where_clause += " AND sp.stage_name = %s"
                params.append(stage_name)
            
            data = self.db.execute_query(f"""
                SELECT 
                    sp.stage_name,
                    COUNT(*) as executions,
                    AVG(sp.duration_seconds) as avg_duration,
                    MIN(sp.duration_seconds) as min_duration,
                    MAX(sp.duration_seconds) as max_duration,
                    STDDEV(sp.duration_seconds) as duration_stddev,
                    AVG(sp.peak_memory_mb) as avg_memory,
                    SUM(CASE WHEN sp.exit_code = 0 THEN 1 ELSE 0 END) as successful_runs,
                    AVG(sp.warnings_count) as avg_warnings,
                    AVG(sp.errors_count) as avg_errors
                FROM stage_performance sp
                {where_clause}
                GROUP BY sp.stage_name
                ORDER BY avg_duration DESC
            """, params, fetch=True)
            
            # Identify performance outliers
            outliers = []
            for row in data:
                if row['duration_stddev'] and row['avg_duration']:
                    cv = row['duration_stddev'] / row['avg_duration']  # Coefficient of variation
                    if cv > 0.5:  # High variability
                        outliers.append({
                            'stage': row['stage_name'],
                            'variability': cv,
                            'reason': 'High duration variability'
                        })
                
                success_rate = (row['successful_runs'] / row['executions']) * 100 if row['executions'] > 0 else 0
                if success_rate < 90:
                    outliers.append({
                        'stage': row['stage_name'],
                        'success_rate': success_rate,
                        'reason': 'Low success rate'
                    })
            
            return {
                'stage_data': data,
                'outliers': outliers,
                'total_stages_analyzed': len(data)
            }
            
        except Exception as e:
            print(f"Failed to analyze stage performance: {e}")
            return {'stage_data': [], 'outliers': [], 'total_stages_analyzed': 0}
    
    def get_failure_pattern_insights(self, days: int = 30) -> Dict:
        """Analyze failure patterns and their impact"""
        try:
            # Get pattern detection frequency
            pattern_data = self.db.execute_query("""
                SELECT 
                    fp.pattern_name,
                    fp.severity,
                    fp.auto_fix_command,
                    COUNT(pd.id) as detections,
                    AVG(pd.confidence_score) as avg_confidence,
                    SUM(CASE WHEN pd.auto_fix_applied THEN 1 ELSE 0 END) as auto_fixes_applied,
                    SUM(CASE WHEN pd.fix_successful THEN 1 ELSE 0 END) as successful_fixes,
                    COUNT(DISTINCT pd.build_id) as affected_builds
                FROM failure_patterns fp
                LEFT JOIN pattern_detections pd ON fp.id = pd.pattern_id
                WHERE pd.detected_at >= DATE_SUB(NOW(), INTERVAL %s DAY) OR pd.detected_at IS NULL
                GROUP BY fp.id, fp.pattern_name, fp.severity, fp.auto_fix_command
                ORDER BY detections DESC
            """, (days,), fetch=True)
            
            # Calculate fix success rates
            for pattern in pattern_data:
                if pattern['auto_fixes_applied'] > 0:
                    pattern['fix_success_rate'] = (pattern['successful_fixes'] / pattern['auto_fixes_applied']) * 100
                else:
                    pattern['fix_success_rate'] = 0
            
            # Get stage-specific pattern distribution
            stage_patterns = self.db.execute_query("""
                SELECT 
                    pd.stage_name,
                    fp.pattern_name,
                    COUNT(*) as occurrences
                FROM pattern_detections pd
                JOIN failure_patterns fp ON pd.pattern_id = fp.id
                WHERE pd.detected_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY pd.stage_name, fp.pattern_name
                ORDER BY occurrences DESC
                LIMIT 20
            """, (days,), fetch=True)
            
            return {
                'pattern_frequency': pattern_data,
                'stage_distribution': stage_patterns,
                'total_patterns': len(pattern_data)
            }
            
        except Exception as e:
            print(f"Failed to analyze failure patterns: {e}")
            return {'pattern_frequency': [], 'stage_distribution': [], 'total_patterns': 0}
    
    def get_system_resource_analysis(self, build_id: str = None, days: int = 7) -> Dict:
        """Analyze system resource usage patterns"""
        try:
            where_clause = "WHERE timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)"
            params = [days]
            
            if build_id:
                where_clause += " AND build_id = %s"
                params.append(build_id)
            
            resource_data = self.db.execute_query(f"""
                SELECT 
                    stage_name,
                    AVG(cpu_percent) as avg_cpu,
                    MAX(cpu_percent) as peak_cpu,
                    AVG(memory_percent) as avg_memory,
                    MAX(memory_percent) as peak_memory,
                    AVG(load_average_1m) as avg_load,
                    MAX(load_average_1m) as peak_load,
                    COUNT(*) as measurements
                FROM system_metrics
                {where_clause}
                GROUP BY stage_name
                ORDER BY avg_cpu DESC
            """, params, fetch=True)
            
            # Identify resource bottlenecks
            bottlenecks = []
            for row in resource_data:
                if row['peak_cpu'] and row['peak_cpu'] > 95:
                    bottlenecks.append({
                        'stage': row['stage_name'],
                        'type': 'CPU',
                        'peak_value': row['peak_cpu'],
                        'severity': 'high' if row['peak_cpu'] > 98 else 'medium'
                    })
                
                if row['peak_memory'] and row['peak_memory'] > 90:
                    bottlenecks.append({
                        'stage': row['stage_name'],
                        'type': 'Memory',
                        'peak_value': row['peak_memory'],
                        'severity': 'high' if row['peak_memory'] > 95 else 'medium'
                    })
                
                if row['peak_load'] and row['peak_load'] > 8:
                    bottlenecks.append({
                        'stage': row['stage_name'],
                        'type': 'Load Average',
                        'peak_value': row['peak_load'],
                        'severity': 'high' if row['peak_load'] > 12 else 'medium'
                    })
            
            return {
                'resource_usage': resource_data,
                'bottlenecks': bottlenecks,
                'total_measurements': sum(row['measurements'] for row in resource_data)
            }
            
        except Exception as e:
            print(f"Failed to analyze system resources: {e}")
            return {'resource_usage': [], 'bottlenecks': [], 'total_measurements': 0}
    
    def get_mirror_performance_insights(self, days: int = 30) -> Dict:
        """Analyze mirror performance and reliability"""
        try:
            mirror_stats = self.db.execute_query("""
                SELECT 
                    mirror_url,
                    COUNT(*) as total_downloads,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_downloads,
                    AVG(download_speed_mbps) as avg_speed,
                    AVG(response_time_ms) as avg_response_time,
                    AVG(retry_count) as avg_retries,
                    COUNT(DISTINCT package_name) as packages_served
                FROM mirror_performance
                WHERE download_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY mirror_url
                ORDER BY successful_downloads DESC
            """, (days,), fetch=True)
            
            # Calculate reliability scores
            for mirror in mirror_stats:
                if mirror['total_downloads'] > 0:
                    success_rate = (mirror['successful_downloads'] / mirror['total_downloads']) * 100
                    mirror['success_rate'] = success_rate
                    
                    # Composite reliability score (0-100)
                    speed_score = min(100, (mirror['avg_speed'] or 0) * 10)  # 10 Mbps = 100 points
                    response_score = max(0, 100 - (mirror['avg_response_time'] or 1000) / 10)  # 1000ms = 0 points
                    retry_penalty = (mirror['avg_retries'] or 0) * 10
                    
                    mirror['reliability_score'] = max(0, (success_rate + speed_score + response_score - retry_penalty) / 3)
                else:
                    mirror['success_rate'] = 0
                    mirror['reliability_score'] = 0
            
            # Get package-specific performance
            package_performance = self.db.execute_query("""
                SELECT 
                    package_name,
                    COUNT(DISTINCT mirror_url) as mirrors_tried,
                    AVG(download_speed_mbps) as avg_speed,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*) * 100 as success_rate
                FROM mirror_performance
                WHERE download_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY package_name
                ORDER BY success_rate ASC
                LIMIT 10
            """, (days,), fetch=True)
            
            return {
                'mirror_stats': mirror_stats,
                'problematic_packages': package_performance,
                'total_mirrors': len(mirror_stats)
            }
            
        except Exception as e:
            print(f"Failed to analyze mirror performance: {e}")
            return {'mirror_stats': [], 'problematic_packages': [], 'total_mirrors': 0}
    
    def get_predictive_insights(self, build_id: str = None) -> Dict:
        """Get predictive analytics insights"""
        try:
            # Get prediction accuracy over time
            accuracy_data = self.db.execute_query("""
                SELECT 
                    DATE(prediction_time) as date,
                    AVG(prediction_accuracy) as avg_accuracy,
                    COUNT(*) as predictions_made,
                    AVG(risk_score) as avg_risk_score
                FROM build_predictions
                WHERE prediction_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                AND prediction_accuracy IS NOT NULL
                GROUP BY DATE(prediction_time)
                ORDER BY date
            """, fetch=True)
            
            # Get current risk factors
            if build_id:
                current_prediction = self.db.execute_query("""
                    SELECT * FROM build_predictions
                    WHERE build_id = %s
                    ORDER BY prediction_time DESC
                    LIMIT 1
                """, (build_id,), fetch=True)
            else:
                current_prediction = []
            
            # Get model performance by version
            model_performance = self.db.execute_query("""
                SELECT 
                    model_version,
                    COUNT(*) as predictions,
                    AVG(prediction_accuracy) as avg_accuracy,
                    STDDEV(prediction_accuracy) as accuracy_stddev
                FROM build_predictions
                WHERE prediction_accuracy IS NOT NULL
                GROUP BY model_version
                ORDER BY avg_accuracy DESC
            """, fetch=True)
            
            return {
                'accuracy_trends': accuracy_data,
                'current_prediction': current_prediction[0] if current_prediction else None,
                'model_performance': model_performance
            }
            
        except Exception as e:
            print(f"Failed to get predictive insights: {e}")
            return {'accuracy_trends': [], 'current_prediction': None, 'model_performance': []}
    
    def generate_build_health_report(self, days: int = 7) -> Dict:
        """Generate comprehensive build system health report"""
        try:
            # Overall system health metrics
            health_metrics = {
                'build_success_rate': 0,
                'avg_build_duration': 0,
                'system_stability': 'unknown',
                'resource_efficiency': 'unknown',
                'mirror_reliability': 'unknown'
            }
            
            # Get recent build success rate
            success_data = self.db.execute_query("""
                SELECT 
                    COUNT(*) as total_builds,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_builds,
                    AVG(duration_seconds) as avg_duration
                FROM builds
                WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (days,), fetch=True)
            
            if success_data and success_data[0]['total_builds'] > 0:
                data = success_data[0]
                health_metrics['build_success_rate'] = (data['successful_builds'] / data['total_builds']) * 100
                health_metrics['avg_build_duration'] = data['avg_duration'] or 0
                
                # Determine system stability
                if health_metrics['build_success_rate'] >= 95:
                    health_metrics['system_stability'] = 'excellent'
                elif health_metrics['build_success_rate'] >= 85:
                    health_metrics['system_stability'] = 'good'
                elif health_metrics['build_success_rate'] >= 70:
                    health_metrics['system_stability'] = 'fair'
                else:
                    health_metrics['system_stability'] = 'poor'
            
            # Get resource efficiency
            resource_data = self.db.execute_query("""
                SELECT 
                    AVG(cpu_percent) as avg_cpu,
                    AVG(memory_percent) as avg_memory,
                    MAX(cpu_percent) as peak_cpu,
                    MAX(memory_percent) as peak_memory
                FROM system_metrics
                WHERE timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (days,), fetch=True)
            
            if resource_data and resource_data[0]['avg_cpu']:
                res = resource_data[0]
                if res['peak_cpu'] < 80 and res['peak_memory'] < 80:
                    health_metrics['resource_efficiency'] = 'excellent'
                elif res['peak_cpu'] < 90 and res['peak_memory'] < 90:
                    health_metrics['resource_efficiency'] = 'good'
                else:
                    health_metrics['resource_efficiency'] = 'stressed'
            
            # Get mirror reliability
            mirror_data = self.db.execute_query("""
                SELECT 
                    COUNT(*) as total_downloads,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_downloads
                FROM mirror_performance
                WHERE download_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (days,), fetch=True)
            
            if mirror_data and mirror_data[0]['total_downloads'] > 0:
                mirror_success = (mirror_data[0]['successful_downloads'] / mirror_data[0]['total_downloads']) * 100
                if mirror_success >= 95:
                    health_metrics['mirror_reliability'] = 'excellent'
                elif mirror_success >= 85:
                    health_metrics['mirror_reliability'] = 'good'
                else:
                    health_metrics['mirror_reliability'] = 'poor'
            
            # Get top issues
            top_issues = self.db.execute_query("""
                SELECT 
                    fp.pattern_name,
                    fp.severity,
                    COUNT(pd.id) as occurrences
                FROM failure_patterns fp
                JOIN pattern_detections pd ON fp.id = pd.pattern_id
                WHERE pd.detected_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY fp.id, fp.pattern_name, fp.severity
                ORDER BY occurrences DESC
                LIMIT 5
            """, (days,), fetch=True)
            
            # Generate recommendations
            recommendations = []
            
            if health_metrics['build_success_rate'] < 90:
                recommendations.append("Build success rate is below 90%. Review recent failure patterns and consider system maintenance.")
            
            if health_metrics['resource_efficiency'] == 'stressed':
                recommendations.append("System resources are under stress. Consider upgrading hardware or optimizing build processes.")
            
            if health_metrics['mirror_reliability'] == 'poor':
                recommendations.append("Mirror reliability is poor. Review mirror configuration and consider adding backup mirrors.")
            
            if not recommendations:
                recommendations.append("System is operating within normal parameters. Continue monitoring.")
            
            return {
                'health_metrics': health_metrics,
                'top_issues': top_issues or [],
                'recommendations': recommendations,
                'report_period_days': days,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Failed to generate health report: {e}")
            return {'health_metrics': {}, 'top_issues': [], 'recommendations': ['Unable to generate health report'], 'report_period_days': days}