#!/usr/bin/env python3
"""
Predictive Failure Analysis for LFS Build System
Analyzes patterns to predict failures before they happen
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

class PredictiveAnalyzer:
    def __init__(self, db_manager):
        self.db = db_manager
        self.warning_thresholds = {
            'critical_warnings': 5,
            'memory_warnings': 3,
            'disk_warnings': 2,
            'compilation_warnings': 10
        }
        self.risk_factors = self._initialize_risk_factors()
    
    def _initialize_risk_factors(self) -> Dict:
        """Initialize risk scoring factors"""
        return {
            'warning_patterns': [
                {'pattern': r'warning.*deprecated', 'weight': 0.1, 'category': 'compilation'},
                {'pattern': r'warning.*implicit', 'weight': 0.1, 'category': 'compilation'},
                {'pattern': r'low.*memory|memory.*low', 'weight': 0.8, 'category': 'memory'},
                {'pattern': r'disk.*full|space.*low', 'weight': 0.9, 'category': 'disk'},
                {'pattern': r'permission.*denied', 'weight': 0.7, 'category': 'permission'},
                {'pattern': r'network.*timeout|connection.*refused', 'weight': 0.5, 'category': 'network'},
                {'pattern': r'makeinfo.*missing|help2man.*not found', 'weight': 0.2, 'category': 'tools'}
            ],
            'performance_degradation': {
                'build_time_increase': 0.6,
                'memory_usage_spike': 0.7,
                'cpu_usage_sustained': 0.4
            },
            'environmental_factors': {
                'weekend_builds': 0.1,
                'night_builds': 0.2,
                'high_system_load': 0.5
            }
        }
    
    def analyze_build_risk(self, build_id: str) -> Dict:
        """Analyze risk factors for a running build"""
        try:
            # Get current build details
            build_details = self.db.get_build_details(build_id)
            if not build_details:
                return {'error': 'Build not found'}
            
            build = build_details['build']
            stages = build_details['stages']
            documents = build_details['documents']
            
            # Calculate risk score
            risk_score = 0.0
            risk_factors = []
            
            # Analyze warning accumulation
            warning_analysis = self._analyze_warning_accumulation(documents)
            risk_score += warning_analysis['risk_contribution']
            risk_factors.extend(warning_analysis['factors'])
            
            # Analyze performance trends
            performance_analysis = self._analyze_performance_trends(build_id, stages)
            risk_score += performance_analysis['risk_contribution']
            risk_factors.extend(performance_analysis['factors'])
            
            # Analyze environmental factors
            env_analysis = self._analyze_environmental_factors(build)
            risk_score += env_analysis['risk_contribution']
            risk_factors.extend(env_analysis['factors'])
            
            # Historical comparison
            historical_analysis = self._analyze_historical_patterns(build_id)
            risk_score += historical_analysis['risk_contribution']
            risk_factors.extend(historical_analysis['factors'])
            
            # Normalize risk score (0-100)
            risk_score = min(100, max(0, risk_score * 100))
            
            # Determine risk level
            if risk_score >= 80:
                risk_level = 'Critical'
                recommendation = 'Consider stopping build and investigating issues'
            elif risk_score >= 60:
                risk_level = 'High'
                recommendation = 'Monitor closely, prepare for potential failure'
            elif risk_score >= 40:
                risk_level = 'Medium'
                recommendation = 'Continue with caution, watch for warning signs'
            elif risk_score >= 20:
                risk_level = 'Low'
                recommendation = 'Build proceeding normally'
            else:
                risk_level = 'Minimal'
                recommendation = 'Build looks healthy'
            
            return {
                'build_id': build_id,
                'risk_score': round(risk_score, 1),
                'risk_level': risk_level,
                'recommendation': recommendation,
                'risk_factors': risk_factors,
                'analysis_time': datetime.now().isoformat(),
                'early_warning': risk_score >= 60
            }
            
        except Exception as e:
            return {'error': f'Risk analysis failed: {str(e)}'}
    
    def _analyze_warning_accumulation(self, documents: List[Dict]) -> Dict:
        """Analyze warning patterns in build documents"""
        warning_counts = defaultdict(int)
        total_warnings = 0
        risk_contribution = 0.0
        factors = []
        
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            content = doc.get('content', '')
            
            # Count warnings by category
            for risk_factor in self.risk_factors['warning_patterns']:
                pattern = risk_factor['pattern']
                matches = len(re.findall(pattern, content, re.IGNORECASE))
                if matches > 0:
                    category = risk_factor['category']
                    warning_counts[category] += matches
                    total_warnings += matches
                    
                    # Add to risk if threshold exceeded
                    threshold = self.warning_thresholds.get(f'{category}_warnings', 5)
                    if warning_counts[category] >= threshold:
                        risk_contribution += risk_factor['weight']
                        factors.append({
                            'type': 'warning_accumulation',
                            'category': category,
                            'count': warning_counts[category],
                            'threshold': threshold,
                            'severity': 'high' if warning_counts[category] > threshold * 2 else 'medium'
                        })
        
        # Overall warning density risk
        if total_warnings > 20:
            risk_contribution += 0.3
            factors.append({
                'type': 'warning_density',
                'count': total_warnings,
                'severity': 'high' if total_warnings > 50 else 'medium'
            })
        
        return {
            'risk_contribution': min(risk_contribution, 1.0),
            'factors': factors,
            'warning_summary': dict(warning_counts),
            'total_warnings': total_warnings
        }
    
    def _analyze_performance_trends(self, build_id: str, stages: List[Dict]) -> Dict:
        """Analyze performance degradation patterns"""
        risk_contribution = 0.0
        factors = []
        
        try:
            # Get historical performance data
            historical_times = self._get_historical_stage_times()
            
            current_times = {}
            for stage in stages:
                if not isinstance(stage, dict):
                    continue
                stage_name = stage.get('stage_name')
                start_time = stage.get('start_time')
                end_time = stage.get('end_time')
                
                if stage_name and start_time and end_time:
                    duration = (end_time - start_time).total_seconds()
                    current_times[stage_name] = duration
            
            # Compare with historical averages
            for stage_name, current_duration in current_times.items():
                if stage_name in historical_times:
                    avg_duration = historical_times[stage_name]['avg']
                    std_duration = historical_times[stage_name]['std']
                    
                    # Check for significant performance degradation
                    if std_duration > 0:
                        z_score = (current_duration - avg_duration) / std_duration
                        if z_score > 2:  # More than 2 standard deviations slower
                            risk_contribution += 0.3
                            factors.append({
                                'type': 'performance_degradation',
                                'stage': stage_name,
                                'current_duration': round(current_duration, 1),
                                'average_duration': round(avg_duration, 1),
                                'slowdown_factor': round(current_duration / avg_duration, 2),
                                'severity': 'high' if z_score > 3 else 'medium'
                            })
            
            return {
                'risk_contribution': min(risk_contribution, 0.8),
                'factors': factors
            }
            
        except Exception as e:
            return {'risk_contribution': 0.0, 'factors': []}
    
    def _analyze_environmental_factors(self, build: Dict) -> Dict:
        """Analyze environmental risk factors"""
        risk_contribution = 0.0
        factors = []
        
        if not isinstance(build, dict):
            return {'risk_contribution': 0.0, 'factors': []}
        
        start_time = build.get('start_time')
        if not start_time:
            return {'risk_contribution': 0.0, 'factors': []}
        
        # Time-based risk factors
        hour = start_time.hour
        weekday = start_time.weekday()
        
        # Weekend builds (slightly higher risk due to less monitoring)
        if weekday >= 5:  # Saturday or Sunday
            risk_contribution += self.risk_factors['environmental_factors']['weekend_builds']
            factors.append({
                'type': 'environmental',
                'factor': 'weekend_build',
                'severity': 'low'
            })
        
        # Night builds (higher risk due to less immediate attention)
        if hour < 6 or hour > 22:
            risk_contribution += self.risk_factors['environmental_factors']['night_builds']
            factors.append({
                'type': 'environmental',
                'factor': 'night_build',
                'hour': hour,
                'severity': 'low'
            })
        
        # System load analysis (if available)
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            
            if cpu_percent > 80:
                risk_contribution += self.risk_factors['environmental_factors']['high_system_load']
                factors.append({
                    'type': 'environmental',
                    'factor': 'high_cpu_load',
                    'cpu_percent': cpu_percent,
                    'severity': 'medium'
                })
            
            if memory_percent > 85:
                risk_contribution += 0.4
                factors.append({
                    'type': 'environmental',
                    'factor': 'high_memory_usage',
                    'memory_percent': memory_percent,
                    'severity': 'high'
                })
        except ImportError:
            pass  # psutil not available
        
        return {
            'risk_contribution': min(risk_contribution, 0.5),
            'factors': factors
        }
    
    def _analyze_historical_patterns(self, build_id: str) -> Dict:
        """Analyze patterns from similar historical builds"""
        risk_contribution = 0.0
        factors = []
        
        try:
            # Get recent builds for pattern analysis
            recent_builds = self.db.execute_query("""
                SELECT build_id, status, start_time, end_time 
                FROM builds 
                WHERE start_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                AND build_id != %s
                ORDER BY start_time DESC 
                LIMIT 20
            """, (build_id,), fetch=True)
            
            if not recent_builds:
                return {'risk_contribution': 0.0, 'factors': []}
            
            # Calculate recent failure rate
            total_builds = len(recent_builds)
            failed_builds = sum(1 for b in recent_builds if b['status'] in ['failed', 'cancelled'])
            failure_rate = failed_builds / total_builds if total_builds > 0 else 0
            
            # High recent failure rate increases risk
            if failure_rate > 0.5:
                risk_contribution += 0.4
                factors.append({
                    'type': 'historical_pattern',
                    'factor': 'high_recent_failure_rate',
                    'failure_rate': round(failure_rate * 100, 1),
                    'recent_builds': total_builds,
                    'severity': 'high'
                })
            elif failure_rate > 0.3:
                risk_contribution += 0.2
                factors.append({
                    'type': 'historical_pattern',
                    'factor': 'elevated_failure_rate',
                    'failure_rate': round(failure_rate * 100, 1),
                    'recent_builds': total_builds,
                    'severity': 'medium'
                })
            
            return {
                'risk_contribution': min(risk_contribution, 0.4),
                'factors': factors
            }
            
        except Exception as e:
            return {'risk_contribution': 0.0, 'factors': []}
    
    def _get_historical_stage_times(self) -> Dict:
        """Get historical stage execution times for comparison"""
        try:
            stage_times = self.db.execute_query("""
                SELECT stage_name, 
                       TIMESTAMPDIFF(SECOND, start_time, end_time) as duration
                FROM build_stages 
                WHERE status = 'success' 
                AND start_time >= DATE_SUB(NOW(), INTERVAL 60 DAY)
                AND end_time IS NOT NULL
            """, fetch=True)
            
            # Group by stage and calculate statistics
            stage_stats = defaultdict(list)
            for stage in stage_times:
                if stage['duration'] and stage['duration'] > 0:
                    stage_stats[stage['stage_name']].append(stage['duration'])
            
            # Calculate averages and standard deviations
            result = {}
            for stage_name, durations in stage_stats.items():
                if len(durations) >= 3:  # Need at least 3 data points
                    result[stage_name] = {
                        'avg': statistics.mean(durations),
                        'std': statistics.stdev(durations) if len(durations) > 1 else 0,
                        'count': len(durations)
                    }
            
            return result
            
        except Exception as e:
            return {}
    
    def get_early_warning_indicators(self, build_id: str) -> Dict:
        """Get early warning indicators for a running build"""
        try:
            risk_analysis = self.analyze_build_risk(build_id)
            
            if 'error' in risk_analysis:
                return risk_analysis
            
            warnings = []
            
            # Critical risk warnings
            if risk_analysis['risk_score'] >= 80:
                warnings.append({
                    'level': 'critical',
                    'message': 'Build failure highly likely - immediate attention required',
                    'action': 'Consider stopping build and investigating'
                })
            elif risk_analysis['risk_score'] >= 60:
                warnings.append({
                    'level': 'warning',
                    'message': 'Build showing signs of potential failure',
                    'action': 'Monitor closely and prepare for intervention'
                })
            
            # Specific factor warnings
            for factor in risk_analysis['risk_factors']:
                if factor.get('severity') == 'high':
                    if factor['type'] == 'warning_accumulation':
                        warnings.append({
                            'level': 'warning',
                            'message': f"High {factor['category']} warning count: {factor['count']}",
                            'action': f"Review {factor['category']} issues in build logs"
                        })
                    elif factor['type'] == 'performance_degradation':
                        warnings.append({
                            'level': 'warning',
                            'message': f"Stage {factor['stage']} running {factor['slowdown_factor']}x slower than average",
                            'action': 'Check system resources and stage dependencies'
                        })
            
            return {
                'build_id': build_id,
                'risk_score': risk_analysis['risk_score'],
                'risk_level': risk_analysis['risk_level'],
                'warnings': warnings,
                'recommendation': risk_analysis['recommendation'],
                'analysis_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': f'Early warning analysis failed: {str(e)}'}
    
    def predict_build_success_probability(self, build_config: Dict) -> Dict:
        """Predict success probability for a new build based on historical data"""
        try:
            # Analyze similar historical builds
            base_probability = 0.7  # Default 70% success rate
            
            # Get recent builds with similar configuration
            recent_success_rate = self._get_recent_success_rate()
            
            # Adjust based on current system state
            system_adjustment = self._get_system_health_adjustment()
            
            # Adjust based on time factors
            time_adjustment = self._get_time_based_adjustment()
            
            # Calculate final probability
            probability = base_probability * recent_success_rate * system_adjustment * time_adjustment
            probability = max(0.1, min(0.95, probability))  # Clamp between 10% and 95%
            
            return {
                'success_probability': round(probability * 100, 1),
                'confidence': 'high' if recent_success_rate > 0.8 else 'medium' if recent_success_rate > 0.5 else 'low',
                'factors': {
                    'recent_success_rate': round(recent_success_rate * 100, 1),
                    'system_health': round(system_adjustment * 100, 1),
                    'time_factors': round(time_adjustment * 100, 1)
                },
                'recommendation': 'Proceed with build' if probability > 0.6 else 'Consider addressing issues before building'
            }
            
        except Exception as e:
            return {'error': f'Prediction failed: {str(e)}'}
    
    def _get_recent_success_rate(self) -> float:
        """Get recent build success rate"""
        try:
            recent_builds = self.db.execute_query("""
                SELECT status FROM builds 
                WHERE start_time >= DATE_SUB(NOW(), INTERVAL 14 DAY)
                ORDER BY start_time DESC 
                LIMIT 10
            """, fetch=True)
            
            if not recent_builds:
                return 0.7  # Default
            
            successful = sum(1 for b in recent_builds if b['status'] == 'completed')
            return successful / len(recent_builds)
            
        except Exception:
            return 0.7
    
    def _get_system_health_adjustment(self) -> float:
        """Get system health adjustment factor"""
        try:
            import psutil
            
            # Check system resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            adjustment = 1.0
            
            if cpu_percent > 80:
                adjustment *= 0.9
            if memory_percent > 85:
                adjustment *= 0.8
            if disk_percent > 90:
                adjustment *= 0.7
            
            return adjustment
            
        except ImportError:
            return 1.0  # No adjustment if psutil not available
    
    def _get_time_based_adjustment(self) -> float:
        """Get time-based adjustment factor"""
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()
        
        adjustment = 1.0
        
        # Slightly lower success rate on weekends (less monitoring)
        if weekday >= 5:
            adjustment *= 0.95
        
        # Lower success rate during night hours (less immediate attention)
        if hour < 6 or hour > 22:
            adjustment *= 0.9
        
        return adjustment