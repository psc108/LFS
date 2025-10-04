#!/usr/bin/env python3
"""
Performance Analysis and Correlation for LFS Build System
Analyzes build performance patterns and correlates with failures
"""

import statistics
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

class PerformanceAnalyzer:
    def __init__(self, db_manager):
        self.db = db_manager
        self.performance_thresholds = {
            'build_time_degradation': 2.0,  # 2x slower than average
            'memory_spike_threshold': 0.8,   # 80% memory usage
            'cpu_sustained_threshold': 0.9,  # 90% CPU for extended period
            'stage_timeout_multiplier': 3.0  # 3x longer than average
        }
    
    def analyze_performance_correlation(self, days: int = 30) -> Dict:
        """Analyze correlation between performance metrics and build failures"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get builds with performance data
            builds_data = self._get_builds_with_performance(cutoff_date)
            
            if not builds_data:
                return {'error': 'No performance data available for analysis'}
            
            # Separate successful and failed builds
            successful_builds = [b for b in builds_data if b['status'] == 'completed']
            failed_builds = [b for b in builds_data if b['status'] in ['failed', 'cancelled']]
            
            # Analyze performance patterns
            duration_analysis = self._analyze_build_duration_patterns(successful_builds, failed_builds)
            stage_analysis = self._analyze_stage_performance_patterns(cutoff_date)
            resource_analysis = self._analyze_resource_correlation(cutoff_date)
            degradation_analysis = self._analyze_performance_degradation(builds_data)
            
            # Generate performance insights
            insights = self._generate_performance_insights(
                duration_analysis, stage_analysis, resource_analysis, degradation_analysis
            )
            
            return {
                'analysis_period': f'Last {days} days',
                'total_builds_analyzed': len(builds_data),
                'successful_builds': len(successful_builds),
                'failed_builds': len(failed_builds),
                'duration_analysis': duration_analysis,
                'stage_analysis': stage_analysis,
                'resource_analysis': resource_analysis,
                'degradation_analysis': degradation_analysis,
                'performance_insights': insights,
                'analysis_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': f'Performance analysis failed: {str(e)}'}
    
    def _get_builds_with_performance(self, cutoff_date: datetime) -> List[Dict]:
        """Get builds with performance metrics"""
        try:
            builds = self.db.execute_query("""
                SELECT build_id, status, start_time, end_time,
                       TIMESTAMPDIFF(SECOND, start_time, end_time) as duration_seconds
                FROM builds 
                WHERE start_time >= %s 
                AND end_time IS NOT NULL
                ORDER BY start_time DESC
            """, (cutoff_date,), fetch=True)
            
            return builds or []
            
        except Exception as e:
            return []
    
    def _analyze_build_duration_patterns(self, successful_builds: List[Dict], failed_builds: List[Dict]) -> Dict:
        """Analyze build duration patterns between successful and failed builds"""
        
        # Calculate duration statistics for successful builds
        successful_durations = [b['duration_seconds'] for b in successful_builds if b['duration_seconds']]
        failed_durations = [b['duration_seconds'] for b in failed_builds if b['duration_seconds']]
        
        analysis = {
            'successful_builds_stats': {},
            'failed_builds_stats': {},
            'correlation_findings': []
        }
        
        if successful_durations:
            analysis['successful_builds_stats'] = {
                'count': len(successful_durations),
                'avg_duration': round(statistics.mean(successful_durations), 1),
                'median_duration': round(statistics.median(successful_durations), 1),
                'std_deviation': round(statistics.stdev(successful_durations), 1) if len(successful_durations) > 1 else 0,
                'min_duration': min(successful_durations),
                'max_duration': max(successful_durations)
            }
        
        if failed_durations:
            analysis['failed_builds_stats'] = {
                'count': len(failed_durations),
                'avg_duration': round(statistics.mean(failed_durations), 1),
                'median_duration': round(statistics.median(failed_durations), 1),
                'std_deviation': round(statistics.stdev(failed_durations), 1) if len(failed_durations) > 1 else 0,
                'min_duration': min(failed_durations),
                'max_duration': max(failed_durations)
            }
        
        # Compare patterns
        if successful_durations and failed_durations:
            successful_avg = statistics.mean(successful_durations)
            failed_avg = statistics.mean(failed_durations)
            
            if failed_avg > successful_avg * 1.5:
                analysis['correlation_findings'].append({
                    'type': 'duration_correlation',
                    'finding': 'Failed builds take significantly longer on average',
                    'successful_avg': round(successful_avg, 1),
                    'failed_avg': round(failed_avg, 1),
                    'ratio': round(failed_avg / successful_avg, 2),
                    'significance': 'high'
                })
            elif failed_avg < successful_avg * 0.5:
                analysis['correlation_findings'].append({
                    'type': 'early_failure',
                    'finding': 'Failed builds fail quickly (early stage failures)',
                    'successful_avg': round(successful_avg, 1),
                    'failed_avg': round(failed_avg, 1),
                    'ratio': round(failed_avg / successful_avg, 2),
                    'significance': 'medium'
                })
        
        return analysis
    
    def _analyze_stage_performance_patterns(self, cutoff_date: datetime) -> Dict:
        """Analyze performance patterns at the stage level"""
        try:
            # Get stage performance data
            stage_data = self.db.execute_query("""
                SELECT bs.stage_name, bs.status,
                       TIMESTAMPDIFF(SECOND, bs.start_time, bs.end_time) as duration,
                       b.status as build_status
                FROM build_stages bs
                JOIN builds b ON bs.build_id = b.build_id
                WHERE bs.start_time >= %s 
                AND bs.end_time IS NOT NULL
                AND bs.start_time IS NOT NULL
            """, (cutoff_date,), fetch=True)
            
            if not stage_data:
                return {'error': 'No stage performance data available'}
            
            # Group by stage and status
            stage_stats = defaultdict(lambda: {'successful': [], 'failed': []})
            
            for stage in stage_data:
                stage_name = stage['stage_name']
                duration = stage['duration']
                
                if stage['status'] in ['completed', 'success']:
                    stage_stats[stage_name]['successful'].append(duration)
                elif stage['status'] == 'failed':
                    stage_stats[stage_name]['failed'].append(duration)
            
            # Calculate statistics for each stage
            stage_analysis = {}
            performance_issues = []
            
            for stage_name, data in stage_stats.items():
                successful_times = data['successful']
                failed_times = data['failed']
                
                stage_info = {
                    'successful_count': len(successful_times),
                    'failed_count': len(failed_times)
                }
                
                if successful_times:
                    stage_info['successful_avg'] = round(statistics.mean(successful_times), 1)
                    stage_info['successful_median'] = round(statistics.median(successful_times), 1)
                    stage_info['successful_std'] = round(statistics.stdev(successful_times), 1) if len(successful_times) > 1 else 0
                
                if failed_times:
                    stage_info['failed_avg'] = round(statistics.mean(failed_times), 1)
                    stage_info['failed_median'] = round(statistics.median(failed_times), 1)
                
                # Check for performance anomalies
                if successful_times and failed_times:
                    successful_avg = statistics.mean(successful_times)
                    failed_avg = statistics.mean(failed_times)
                    
                    if failed_avg > successful_avg * self.performance_thresholds['stage_timeout_multiplier']:
                        performance_issues.append({
                            'stage': stage_name,
                            'issue': 'timeout_pattern',
                            'description': f'Failed attempts take {failed_avg/successful_avg:.1f}x longer than successful ones',
                            'successful_avg': round(successful_avg, 1),
                            'failed_avg': round(failed_avg, 1),
                            'severity': 'high'
                        })
                
                stage_analysis[stage_name] = stage_info
            
            return {
                'stage_statistics': stage_analysis,
                'performance_issues': performance_issues,
                'slowest_stages': self._identify_slowest_stages(stage_analysis),
                'most_variable_stages': self._identify_variable_stages(stage_analysis)
            }
            
        except Exception as e:
            return {'error': f'Stage performance analysis failed: {str(e)}'}
    
    def _analyze_resource_correlation(self, cutoff_date: datetime) -> Dict:
        """Analyze correlation between resource usage and build outcomes"""
        # This would require system resource monitoring data
        # For now, analyze resource-related errors from documents
        
        try:
            resource_errors = self.db.execute_query("""
                SELECT bd.build_id, bd.content, b.status, b.start_time
                FROM build_documents bd
                JOIN builds b ON bd.build_id = b.build_id
                WHERE bd.created_at >= %s
                AND bd.document_type = 'error'
                AND (bd.content LIKE '%memory%' OR bd.content LIKE '%disk%' OR bd.content LIKE '%cpu%')
            """, (cutoff_date,), fetch=True)
            
            resource_patterns = {
                'memory_issues': 0,
                'disk_issues': 0,
                'cpu_issues': 0
            }
            
            builds_with_resource_issues = set()
            
            for error in resource_errors:
                content = error['content'].lower()
                build_id = error['build_id']
                
                if any(keyword in content for keyword in ['memory', 'malloc', 'out of memory']):
                    resource_patterns['memory_issues'] += 1
                    builds_with_resource_issues.add(build_id)
                
                if any(keyword in content for keyword in ['disk', 'space', 'no space left']):
                    resource_patterns['disk_issues'] += 1
                    builds_with_resource_issues.add(build_id)
                
                if any(keyword in content for keyword in ['cpu', 'load', 'overload']):
                    resource_patterns['cpu_issues'] += 1
                    builds_with_resource_issues.add(build_id)
            
            return {
                'resource_error_patterns': resource_patterns,
                'builds_with_resource_issues': len(builds_with_resource_issues),
                'total_resource_errors': len(resource_errors),
                'resource_correlation': len(builds_with_resource_issues) / max(1, len(resource_errors)) * 100
            }
            
        except Exception as e:
            return {'error': f'Resource correlation analysis failed: {str(e)}'}
    
    def _analyze_performance_degradation(self, builds_data: List[Dict]) -> Dict:
        """Analyze performance degradation trends over time"""
        
        if len(builds_data) < 5:
            return {'error': 'Insufficient data for degradation analysis'}
        
        # Sort builds by time
        builds_sorted = sorted(builds_data, key=lambda x: x['start_time'])
        
        # Calculate rolling averages
        window_size = 5
        rolling_averages = []
        
        for i in range(len(builds_sorted) - window_size + 1):
            window_builds = builds_sorted[i:i + window_size]
            durations = [b['duration_seconds'] for b in window_builds if b['duration_seconds']]
            
            if durations:
                avg_duration = statistics.mean(durations)
                rolling_averages.append({
                    'window_start': window_builds[0]['start_time'],
                    'window_end': window_builds[-1]['start_time'],
                    'avg_duration': avg_duration,
                    'build_count': len(durations)
                })
        
        # Detect trends
        degradation_detected = False
        improvement_detected = False
        
        if len(rolling_averages) >= 3:
            recent_avg = statistics.mean([ra['avg_duration'] for ra in rolling_averages[-3:]])
            early_avg = statistics.mean([ra['avg_duration'] for ra in rolling_averages[:3]])
            
            degradation_ratio = recent_avg / early_avg
            
            if degradation_ratio > self.performance_thresholds['build_time_degradation']:
                degradation_detected = True
            elif degradation_ratio < 0.8:  # 20% improvement
                improvement_detected = True
        
        return {
            'rolling_averages': rolling_averages,
            'degradation_detected': degradation_detected,
            'improvement_detected': improvement_detected,
            'trend_analysis': {
                'recent_performance': rolling_averages[-3:] if len(rolling_averages) >= 3 else [],
                'early_performance': rolling_averages[:3] if len(rolling_averages) >= 3 else [],
                'performance_ratio': recent_avg / early_avg if len(rolling_averages) >= 3 else 1.0
            }
        }
    
    def _identify_slowest_stages(self, stage_analysis: Dict) -> List[Dict]:
        """Identify the slowest performing stages"""
        stage_speeds = []
        
        for stage_name, stats in stage_analysis.items():
            if 'successful_avg' in stats:
                stage_speeds.append({
                    'stage': stage_name,
                    'avg_duration': stats['successful_avg'],
                    'success_count': stats['successful_count']
                })
        
        # Sort by average duration (descending)
        stage_speeds.sort(key=lambda x: x['avg_duration'], reverse=True)
        
        return stage_speeds[:5]  # Top 5 slowest stages
    
    def _identify_variable_stages(self, stage_analysis: Dict) -> List[Dict]:
        """Identify stages with high performance variability"""
        variable_stages = []
        
        for stage_name, stats in stage_analysis.items():
            if 'successful_std' in stats and 'successful_avg' in stats:
                if stats['successful_avg'] > 0:
                    coefficient_of_variation = stats['successful_std'] / stats['successful_avg']
                    
                    if coefficient_of_variation > 0.5:  # High variability
                        variable_stages.append({
                            'stage': stage_name,
                            'coefficient_of_variation': round(coefficient_of_variation, 3),
                            'avg_duration': stats['successful_avg'],
                            'std_deviation': stats['successful_std']
                        })
        
        # Sort by coefficient of variation (descending)
        variable_stages.sort(key=lambda x: x['coefficient_of_variation'], reverse=True)
        
        return variable_stages
    
    def _generate_performance_insights(self, duration_analysis: Dict, stage_analysis: Dict, 
                                     resource_analysis: Dict, degradation_analysis: Dict) -> List[str]:
        """Generate actionable performance insights"""
        insights = []
        
        # Duration insights
        if duration_analysis.get('correlation_findings'):
            for finding in duration_analysis['correlation_findings']:
                if finding['type'] == 'duration_correlation':
                    insights.append(f"⚠️ Failed builds take {finding['ratio']}x longer than successful ones - investigate performance bottlenecks")
                elif finding['type'] == 'early_failure':
                    insights.append(f"🔍 Failed builds fail quickly ({finding['ratio']}x faster) - focus on early stage validation")
        
        # Stage performance insights
        if stage_analysis.get('performance_issues'):
            for issue in stage_analysis['performance_issues']:
                insights.append(f"🐌 {issue['stage']} stage shows timeout patterns - failed attempts take {issue['failed_avg']/issue['successful_avg']:.1f}x longer")
        
        if stage_analysis.get('slowest_stages'):
            slowest = stage_analysis['slowest_stages'][0]
            insights.append(f"⏱️ {slowest['stage']} is the slowest stage (avg: {slowest['avg_duration']}s) - consider optimization")
        
        # Resource insights
        if resource_analysis.get('resource_error_patterns'):
            patterns = resource_analysis['resource_error_patterns']
            if patterns['memory_issues'] > 0:
                insights.append(f"💾 {patterns['memory_issues']} memory-related errors detected - consider increasing available memory")
            if patterns['disk_issues'] > 0:
                insights.append(f"💿 {patterns['disk_issues']} disk space errors detected - monitor disk usage more closely")
        
        # Degradation insights
        if degradation_analysis.get('degradation_detected'):
            insights.append("📉 Performance degradation detected over time - investigate system changes or resource constraints")
        elif degradation_analysis.get('improvement_detected'):
            insights.append("📈 Performance improvement detected - recent optimizations are working well")
        
        # General recommendations
        if not insights:
            insights.append("✅ No significant performance issues detected - build system is performing well")
        
        insights.append("💡 Regular performance monitoring helps identify issues before they impact builds")
        
        return insights
    
    def get_build_performance_score(self, build_id: str) -> Dict:
        """Calculate a performance score for a specific build"""
        try:
            build_details = self.db.get_build_details(build_id)
            if not build_details:
                return {'error': 'Build not found'}
            
            build = build_details['build']
            stages = build_details['stages']
            
            # Calculate performance metrics
            total_duration = 0
            stage_scores = []
            
            for stage in stages:
                if not isinstance(stage, dict):
                    continue
                
                start_time = stage.get('start_time')
                end_time = stage.get('end_time')
                
                if start_time and end_time:
                    duration = (end_time - start_time).total_seconds()
                    total_duration += duration
                    
                    # Get historical average for this stage
                    historical_avg = self._get_stage_historical_average(stage.get('stage_name'))
                    
                    if historical_avg > 0:
                        performance_ratio = duration / historical_avg
                        # Score: 100 = average, >100 = slower, <100 = faster
                        stage_score = max(0, min(200, 100 / performance_ratio * 100))
                    else:
                        stage_score = 100  # Default score if no historical data
                    
                    stage_scores.append({
                        'stage': stage.get('stage_name'),
                        'duration': duration,
                        'score': round(stage_score, 1),
                        'performance': 'excellent' if stage_score > 120 else 'good' if stage_score > 80 else 'poor'
                    })
            
            # Calculate overall score
            overall_score = statistics.mean([s['score'] for s in stage_scores]) if stage_scores else 0
            
            return {
                'build_id': build_id,
                'overall_score': round(overall_score, 1),
                'total_duration': total_duration,
                'stage_scores': stage_scores,
                'performance_grade': self._get_performance_grade(overall_score),
                'analysis_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': f'Performance scoring failed: {str(e)}'}
    
    def _get_stage_historical_average(self, stage_name: str) -> float:
        """Get historical average duration for a stage"""
        try:
            result = self.db.execute_query("""
                SELECT AVG(TIMESTAMPDIFF(SECOND, start_time, end_time)) as avg_duration
                FROM build_stages 
                WHERE stage_name = %s 
                AND status IN ('completed', 'success')
                AND start_time >= DATE_SUB(NOW(), INTERVAL 60 DAY)
                AND end_time IS NOT NULL
            """, (stage_name,), fetch=True)
            
            if result and result[0]['avg_duration']:
                return float(result[0]['avg_duration'])
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _get_performance_grade(self, score: float) -> str:
        """Convert performance score to letter grade"""
        if score >= 120:
            return 'A+'
        elif score >= 100:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 60:
            return 'C'
        elif score >= 40:
            return 'D'
        else:
            return 'F'