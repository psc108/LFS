#!/usr/bin/env python3

import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

class MaintenanceAdvisor:
    """Predictive maintenance recommendations"""
    
    def __init__(self, db_manager=None, log_analyzer=None, anomaly_detector=None):
        self.db_manager = db_manager
        self.log_analyzer = log_analyzer
        self.anomaly_detector = anomaly_detector
        self.maintenance_rules = self._load_maintenance_rules()
        
    def _load_maintenance_rules(self) -> Dict:
        """Load predictive maintenance rules"""
        return {
            'build_failure_patterns': {
                'threshold': 3,  # 3 failures in pattern
                'timeframe_hours': 24,
                'recommendation': 'Investigate recurring build issues and update dependencies'
            },
            'system_resource_trends': {
                'cpu_trend_threshold': 5.0,  # 5% increase per day
                'memory_trend_threshold': 3.0,  # 3% increase per day
                'disk_trend_threshold': 2.0,  # 2% increase per day
                'recommendation': 'Plan system resource upgrades'
            },
            'error_frequency_increase': {
                'threshold_multiplier': 2.0,  # 2x normal error rate
                'timeframe_days': 7,
                'recommendation': 'Review system configuration and update software'
            },
            'performance_degradation': {
                'build_time_increase': 1.5,  # 50% increase in build times
                'timeframe_days': 14,
                'recommendation': 'Optimize build environment and clean up system'
            }
        }
    
    def generate_maintenance_recommendations(self) -> Dict:
        """Generate comprehensive maintenance recommendations"""
        try:
            recommendations = []
            
            # Analyze build patterns
            build_recommendations = self._analyze_build_patterns()
            recommendations.extend(build_recommendations)
            
            # Analyze system health trends
            system_recommendations = self._analyze_system_trends()
            recommendations.extend(system_recommendations)
            
            # Analyze error patterns
            error_recommendations = self._analyze_error_patterns()
            recommendations.extend(error_recommendations)
            
            # Analyze performance trends
            performance_recommendations = self._analyze_performance_trends()
            recommendations.extend(performance_recommendations)
            
            # Generate scheduled maintenance
            scheduled_maintenance = self._generate_scheduled_maintenance()
            recommendations.extend(scheduled_maintenance)
            
            # Prioritize recommendations
            prioritized_recommendations = self._prioritize_recommendations(recommendations)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'recommendations': prioritized_recommendations,
                'total_recommendations': len(prioritized_recommendations),
                'priority_counts': self._count_by_priority(prioritized_recommendations),
                'next_maintenance_window': self._suggest_maintenance_window()
            }
            
        except Exception as e:
            logging.error(f"Failed to generate maintenance recommendations: {e}")
            return {'error': str(e)}
    
    def _analyze_build_patterns(self) -> List[Dict]:
        """Analyze build failure patterns"""
        recommendations = []
        
        if not self.db_manager:
            return recommendations
        
        try:
            # Get recent build failures
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            failed_builds = self.db_manager.execute_query(
                "SELECT build_id, start_time, config_name FROM builds WHERE status IN ('failed', 'cancelled') AND start_time >= %s",
                (cutoff_time,), fetch=True
            )
            
            if len(failed_builds) >= self.maintenance_rules['build_failure_patterns']['threshold']:
                # Analyze failure patterns
                config_failures = defaultdict(int)
                stage_failures = defaultdict(int)
                
                for build in failed_builds:
                    config_name = build.get('config_name', 'unknown')
                    config_failures[config_name] += 1
                    
                    # Get failed stages for this build
                    failed_stages = self.db_manager.execute_query(
                        "SELECT stage_name FROM build_stages WHERE build_id = %s AND status = 'failed'",
                        (build['build_id'],), fetch=True
                    )
                    
                    for stage in failed_stages:
                        stage_failures[stage['stage_name']] += 1
                
                # Find most problematic configurations
                for config, count in config_failures.items():
                    if count >= 2:
                        recommendations.append({
                            'type': 'build_pattern',
                            'priority': 'high',
                            'title': f'Recurring Failures in {config}',
                            'description': f'{count} failures in last 24 hours for configuration {config}',
                            'recommendation': 'Review configuration settings and dependencies',
                            'urgency': 'immediate',
                            'estimated_effort': 'medium'
                        })
                
                # Find problematic stages
                for stage, count in stage_failures.items():
                    if count >= 2:
                        recommendations.append({
                            'type': 'stage_pattern',
                            'priority': 'medium',
                            'title': f'Recurring Stage Failures: {stage}',
                            'description': f'{count} failures in stage {stage} in last 24 hours',
                            'recommendation': f'Investigate {stage} stage configuration and dependencies',
                            'urgency': 'scheduled',
                            'estimated_effort': 'medium'
                        })
            
        except Exception as e:
            logging.error(f"Build pattern analysis failed: {e}")
        
        return recommendations
    
    def _analyze_system_trends(self) -> List[Dict]:
        """Analyze system resource trends"""
        recommendations = []
        
        if not self.anomaly_detector:
            return recommendations
        
        try:
            # Get system health summary
            health_summary = self.anomaly_detector.get_health_summary()
            
            if 'error' in health_summary:
                return recommendations
            
            # Check for critical anomalies
            anomalies = health_summary.get('anomalies', {}).get('anomalies', [])
            critical_anomalies = [a for a in anomalies if a.get('severity') == 'critical']
            
            if critical_anomalies:
                recommendations.append({
                    'type': 'system_critical',
                    'priority': 'critical',
                    'title': 'Critical System Issues Detected',
                    'description': f'{len(critical_anomalies)} critical system anomalies found',
                    'recommendation': 'Immediate system maintenance required',
                    'urgency': 'immediate',
                    'estimated_effort': 'high'
                })
            
            # Check system health score
            health_score = health_summary.get('anomalies', {}).get('system_health_score', 100)
            if health_score < 70:
                recommendations.append({
                    'type': 'system_health',
                    'priority': 'medium',
                    'title': 'System Health Degradation',
                    'description': f'System health score: {health_score:.1f}/100',
                    'recommendation': 'Schedule system optimization and cleanup',
                    'urgency': 'scheduled',
                    'estimated_effort': 'medium'
                })
            
        except Exception as e:
            logging.error(f"System trend analysis failed: {e}")
        
        return recommendations
    
    def _analyze_error_patterns(self) -> List[Dict]:
        """Analyze error frequency patterns"""
        recommendations = []
        
        if not self.db_manager:
            return recommendations
        
        try:
            # Get error documents from last week
            cutoff_time = datetime.now() - timedelta(days=7)
            
            error_docs = self.db_manager.execute_query(
                "SELECT created_at, content, build_id FROM build_documents WHERE document_type IN ('error', 'log') AND created_at >= %s AND content LIKE '%error%'",
                (cutoff_time,), fetch=True
            )
            
            # Also check stage failures
            failed_stages = self.db_manager.execute_query(
                "SELECT stage_name, output_log FROM build_stages WHERE status = 'failed' AND start_time >= %s",
                (cutoff_time,), fetch=True
            )
            
            total_errors = len(error_docs) + len(failed_stages)
            
            if total_errors > 20:  # High error frequency
                # Analyze error types
                error_types = defaultdict(int)
                for doc in error_docs:
                    content = doc.get('content', '').lower()
                    if 'permission denied' in content:
                        error_types['permission'] += 1
                    elif 'not found' in content or 'no such file' in content:
                        error_types['missing_files'] += 1
                    elif 'compilation' in content or 'gcc' in content:
                        error_types['compilation'] += 1
                    else:
                        error_types['other'] += 1
                
                recommendations.append({
                    'type': 'error_frequency',
                    'priority': 'medium',
                    'title': 'High Error Frequency Detected',
                    'description': f'{total_errors} errors in last 7 days (docs: {len(error_docs)}, stages: {len(failed_stages)})',
                    'recommendation': f'Review system logs and address common error types: {dict(error_types)}',
                    'urgency': 'scheduled',
                    'estimated_effort': 'medium'
                })
            
        except Exception as e:
            logging.error(f"Error pattern analysis failed: {e}")
        
        return recommendations
    
    def _analyze_performance_trends(self) -> List[Dict]:
        """Analyze build performance trends"""
        recommendations = []
        
        if not self.db_manager:
            return recommendations
        
        try:
            # Get recent successful builds
            cutoff_time = datetime.now() - timedelta(days=14)
            
            builds = self.db_manager.execute_query(
                "SELECT build_id, start_time, end_time, TIMESTAMPDIFF(MINUTE, start_time, end_time) as duration_minutes FROM builds WHERE status = 'success' AND start_time >= %s AND end_time IS NOT NULL",
                (cutoff_time,), fetch=True
            )
            
            if len(builds) >= 5:
                durations = [build['duration_minutes'] for build in builds if build['duration_minutes']]
                
                if durations:
                    avg_duration = np.mean(durations)
                    recent_duration = np.mean(durations[-3:]) if len(durations) >= 3 else avg_duration
                    
                    # Check for performance degradation
                    if recent_duration > avg_duration * 1.3:  # 30% increase
                        recommendations.append({
                            'type': 'performance_degradation',
                            'priority': 'medium',
                            'title': 'Build Performance Degradation',
                            'description': f'Recent builds taking {recent_duration:.1f} min vs {avg_duration:.1f} min average',
                            'recommendation': 'Optimize build environment and clean temporary files',
                            'urgency': 'scheduled',
                            'estimated_effort': 'low'
                        })
            
        except Exception as e:
            logging.error(f"Performance trend analysis failed: {e}")
        
        return recommendations
    
    def _generate_scheduled_maintenance(self) -> List[Dict]:
        """Generate routine scheduled maintenance recommendations"""
        recommendations = []
        
        # Weekly maintenance
        recommendations.append({
            'type': 'scheduled_weekly',
            'priority': 'low',
            'title': 'Weekly System Cleanup',
            'description': 'Routine system maintenance and cleanup',
            'recommendation': 'Clear temporary files, update package cache, check disk space',
            'urgency': 'scheduled',
            'estimated_effort': 'low',
            'frequency': 'weekly'
        })
        
        # Monthly maintenance
        recommendations.append({
            'type': 'scheduled_monthly',
            'priority': 'low',
            'title': 'Monthly Security Updates',
            'description': 'Apply security patches and system updates',
            'recommendation': 'Update system packages, review security settings, backup configurations',
            'urgency': 'scheduled',
            'estimated_effort': 'medium',
            'frequency': 'monthly'
        })
        
        # Quarterly maintenance
        recommendations.append({
            'type': 'scheduled_quarterly',
            'priority': 'low',
            'title': 'Quarterly System Review',
            'description': 'Comprehensive system review and optimization',
            'recommendation': 'Review system performance, update documentation, plan capacity upgrades',
            'urgency': 'scheduled',
            'estimated_effort': 'high',
            'frequency': 'quarterly'
        })
        
        return recommendations
    
    def _prioritize_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """Prioritize recommendations by urgency and impact"""
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        urgency_order = {'immediate': 0, 'scheduled': 1}
        
        def sort_key(rec):
            priority = priority_order.get(rec.get('priority', 'low'), 3)
            urgency = urgency_order.get(rec.get('urgency', 'scheduled'), 1)
            return (priority, urgency)
        
        return sorted(recommendations, key=sort_key)
    
    def _count_by_priority(self, recommendations: List[Dict]) -> Dict:
        """Count recommendations by priority"""
        counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for rec in recommendations:
            priority = rec.get('priority', 'low')
            counts[priority] = counts.get(priority, 0) + 1
        return counts
    
    def _suggest_maintenance_window(self) -> Dict:
        """Suggest optimal maintenance window"""
        # Simple heuristic: suggest weekend maintenance
        now = datetime.now()
        days_until_weekend = (5 - now.weekday()) % 7  # Saturday = 5
        if days_until_weekend == 0:
            days_until_weekend = 7  # Next weekend if today is weekend
        
        maintenance_date = now + timedelta(days=days_until_weekend)
        maintenance_date = maintenance_date.replace(hour=2, minute=0, second=0, microsecond=0)
        
        return {
            'suggested_date': maintenance_date.isoformat(),
            'day_of_week': maintenance_date.strftime('%A'),
            'rationale': 'Weekend maintenance window to minimize disruption'
        }
    
    def get_maintenance_checklist(self, priority: str = 'all') -> Dict:
        """Generate maintenance checklist"""
        recommendations = self.generate_maintenance_recommendations()
        
        if 'error' in recommendations:
            return recommendations
        
        # Filter by priority if specified
        if priority != 'all':
            filtered_recs = [r for r in recommendations['recommendations'] if r.get('priority') == priority]
        else:
            filtered_recs = recommendations['recommendations']
        
        # Group by type
        checklist = defaultdict(list)
        for rec in filtered_recs:
            rec_type = rec.get('type', 'general')
            checklist[rec_type].append({
                'title': rec.get('title'),
                'description': rec.get('description'),
                'recommendation': rec.get('recommendation'),
                'estimated_effort': rec.get('estimated_effort', 'unknown'),
                'completed': False
            })
        
        return {
            'timestamp': datetime.now().isoformat(),
            'priority_filter': priority,
            'checklist': dict(checklist),
            'total_items': len(filtered_recs)
        }