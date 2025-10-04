#!/usr/bin/env python3
"""
Intelligent Guidance Engine for LFS Build System
Provides data-driven next attempt guidance based on historical patterns
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from ..database.db_manager import DatabaseManager

class IntelligentGuidanceEngine:
    """Provides intelligent next attempt guidance based on historical data"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def analyze_failure_and_suggest_next_steps(self, build_id: str, current_stage: str, 
                                             error_output: str) -> Dict:
        """Analyze current failure and provide intelligent next attempt guidance"""
        try:
            # Get historical context
            historical_context = self._get_historical_context(current_stage, error_output)
            
            # Detect patterns in current failure
            detected_patterns = self._detect_patterns_in_output(error_output)
            
            # Get successful resolution strategies
            resolution_strategies = self._get_successful_resolutions(detected_patterns, current_stage)
            
            # Analyze environment factors
            environment_factors = self._analyze_environment_factors(build_id)
            
            # Generate prioritized recommendations
            recommendations = self._generate_prioritized_recommendations(
                detected_patterns, resolution_strategies, environment_factors, historical_context
            )
            
            # Calculate success probability for each recommendation
            success_probabilities = self._calculate_success_probabilities(
                recommendations, historical_context
            )
            
            return {
                'build_id': build_id,
                'stage': current_stage,
                'detected_patterns': detected_patterns,
                'historical_success_rate': historical_context.get('success_rate', 0),
                'similar_failures': historical_context.get('similar_count', 0),
                'recommendations': recommendations,
                'success_probabilities': success_probabilities,
                'environment_risk_factors': environment_factors,
                'confidence_score': self._calculate_confidence_score(historical_context, detected_patterns)
            }
            
        except Exception as e:
            print(f"Failed to generate intelligent guidance: {e}")
            return {'error': str(e), 'recommendations': []}
    
    def _get_historical_context(self, stage: str, error_output: str) -> Dict:
        """Get historical context for similar failures"""
        try:
            # Find similar failures in the same stage
            similar_failures = self.db.execute_query("""
                SELECT 
                    pd.build_id,
                    pd.confidence_score,
                    pd.auto_fix_applied,
                    pd.fix_successful,
                    fp.pattern_name,
                    fp.auto_fix_command,
                    b.status as build_status
                FROM pattern_detections pd
                JOIN failure_patterns fp ON pd.pattern_id = fp.id
                JOIN builds b ON pd.build_id = b.build_id
                WHERE pd.stage_name = %s
                AND pd.detected_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                ORDER BY pd.detected_at DESC
                LIMIT 50
            """, (stage,), fetch=True)
            
            # Calculate success rates for different fix strategies
            fix_success_rates = {}
            total_similar = len(similar_failures)
            successful_builds = 0
            
            for failure in similar_failures:
                if failure['build_status'] == 'completed':
                    successful_builds += 1
                
                if failure['auto_fix_command'] and failure['fix_successful']:
                    cmd = failure['auto_fix_command']
                    if cmd not in fix_success_rates:
                        fix_success_rates[cmd] = {'successful': 0, 'total': 0}
                    fix_success_rates[cmd]['total'] += 1
                    if failure['fix_successful']:
                        fix_success_rates[cmd]['successful'] += 1
            
            # Calculate overall success rate
            success_rate = (successful_builds / total_similar * 100) if total_similar > 0 else 0
            
            return {
                'similar_count': total_similar,
                'success_rate': success_rate,
                'fix_success_rates': fix_success_rates,
                'recent_failures': similar_failures[:10]
            }
            
        except Exception as e:
            print(f"Failed to get historical context: {e}")
            return {'similar_count': 0, 'success_rate': 0, 'fix_success_rates': {}}
    
    def _detect_patterns_in_output(self, error_output: str) -> List[Dict]:
        """Detect known failure patterns in error output"""
        try:
            # Get all known patterns from database
            patterns = self.db.execute_query("""
                SELECT id, pattern_name, regex_pattern, severity, auto_fix_command, description
                FROM failure_patterns
                WHERE regex_pattern IS NOT NULL AND regex_pattern != ''
                ORDER BY detection_count DESC
            """, fetch=True)
            
            detected = []
            
            for pattern in patterns:
                try:
                    if re.search(pattern['regex_pattern'], error_output, re.IGNORECASE):
                        # Calculate confidence based on pattern specificity
                        confidence = self._calculate_pattern_confidence(
                            pattern['regex_pattern'], error_output
                        )
                        
                        detected.append({
                            'pattern_id': pattern['id'],
                            'pattern_name': pattern['pattern_name'],
                            'severity': pattern['severity'],
                            'confidence': confidence,
                            'auto_fix_command': pattern['auto_fix_command'],
                            'description': pattern['description']
                        })
                        
                except re.error:
                    # Skip invalid regex patterns
                    continue
            
            # Sort by confidence score
            detected.sort(key=lambda x: x['confidence'], reverse=True)
            
            return detected[:5]  # Return top 5 matches
            
        except Exception as e:
            print(f"Failed to detect patterns: {e}")
            return []
    
    def _get_successful_resolutions(self, detected_patterns: List[Dict], stage: str) -> List[Dict]:
        """Get historically successful resolution strategies"""
        try:
            if not detected_patterns:
                return []
            
            pattern_ids = [p['pattern_id'] for p in detected_patterns]
            placeholders = ','.join(['%s'] * len(pattern_ids))
            
            # Get successful resolutions for these patterns
            resolutions = self.db.execute_query(f"""
                SELECT 
                    ra.recovery_type,
                    ra.commands_executed,
                    ra.success,
                    COUNT(*) as usage_count,
                    AVG(ra.recovery_time_seconds) as avg_recovery_time,
                    fp.pattern_name
                FROM recovery_actions ra
                JOIN failure_patterns fp ON ra.failure_pattern_id = fp.id
                WHERE ra.failure_pattern_id IN ({placeholders})
                AND ra.success = TRUE
                AND ra.timestamp >= DATE_SUB(NOW(), INTERVAL 60 DAY)
                GROUP BY ra.recovery_type, ra.commands_executed, fp.pattern_name
                ORDER BY usage_count DESC, avg_recovery_time ASC
            """, pattern_ids, fetch=True)
            
            return resolutions
            
        except Exception as e:
            print(f"Failed to get successful resolutions: {e}")
            return []
    
    def _analyze_environment_factors(self, build_id: str) -> Dict:
        """Analyze environment factors that might affect success"""
        try:
            # Get build environment
            env_data = self.db.execute_query("""
                SELECT * FROM build_environment WHERE build_id = %s
            """, (build_id,), fetch=True)
            
            if not env_data:
                return {'risk_factors': [], 'recommendations': []}
            
            env = env_data[0]
            risk_factors = []
            recommendations = []
            
            # Check memory constraints
            if env['total_memory_gb'] < 4:
                risk_factors.append({
                    'factor': 'Low Memory',
                    'value': f"{env['total_memory_gb']:.1f} GB",
                    'risk_level': 'high',
                    'impact': 'May cause compilation failures or swapping'
                })
                recommendations.append('Consider adding swap space or upgrading memory')
            
            # Check disk space
            if env['disk_space_gb'] < 20:
                risk_factors.append({
                    'factor': 'Low Disk Space',
                    'value': f"{env['disk_space_gb']:.1f} GB",
                    'risk_level': 'critical',
                    'impact': 'Build will likely fail due to insufficient space'
                })
                recommendations.append('Free up disk space or use external storage')
            
            # Check CPU cores for parallel builds
            if env['cpu_cores'] < 2:
                risk_factors.append({
                    'factor': 'Single Core CPU',
                    'value': f"{env['cpu_cores']} core",
                    'risk_level': 'medium',
                    'impact': 'Build will be slower, consider reducing parallel jobs'
                })
                recommendations.append('Use -j1 for make commands to avoid overload')
            
            return {
                'risk_factors': risk_factors,
                'recommendations': recommendations,
                'environment': env
            }
            
        except Exception as e:
            print(f"Failed to analyze environment factors: {e}")
            return {'risk_factors': [], 'recommendations': []}
    
    def _generate_prioritized_recommendations(self, detected_patterns: List[Dict], 
                                           resolutions: List[Dict], 
                                           environment_factors: Dict,
                                           historical_context: Dict) -> List[Dict]:
        """Generate prioritized recommendations based on all analysis"""
        recommendations = []
        
        # Add pattern-based recommendations
        for pattern in detected_patterns:
            if pattern['auto_fix_command']:
                recommendations.append({
                    'type': 'auto_fix',
                    'priority': self._calculate_priority(pattern, historical_context),
                    'title': f"Auto-fix for {pattern['pattern_name']}",
                    'description': pattern['description'],
                    'command': pattern['auto_fix_command'],
                    'confidence': pattern['confidence'],
                    'severity': pattern['severity'],
                    'source': 'pattern_detection'
                })
        
        # Add historically successful resolutions
        for resolution in resolutions:
            if resolution['commands_executed']:
                try:
                    commands = json.loads(resolution['commands_executed'])
                    recommendations.append({
                        'type': 'historical_fix',
                        'priority': 80 + (resolution['usage_count'] * 2),  # Higher usage = higher priority
                        'title': f"Historically successful {resolution['recovery_type']}",
                        'description': f"Used {resolution['usage_count']} times successfully for {resolution['pattern_name']}",
                        'commands': commands,
                        'avg_recovery_time': resolution['avg_recovery_time'],
                        'usage_count': resolution['usage_count'],
                        'source': 'historical_success'
                    })
                except json.JSONDecodeError:
                    # Handle single command strings
                    recommendations.append({
                        'type': 'historical_fix',
                        'priority': 80 + (resolution['usage_count'] * 2),
                        'title': f"Historically successful {resolution['recovery_type']}",
                        'description': f"Used {resolution['usage_count']} times successfully",
                        'command': resolution['commands_executed'],
                        'source': 'historical_success'
                    })
        
        # Add environment-based recommendations
        for rec in environment_factors.get('recommendations', []):
            recommendations.append({
                'type': 'environment_fix',
                'priority': 70,
                'title': 'Environment Optimization',
                'description': rec,
                'source': 'environment_analysis'
            })
        
        # Sort by priority (highest first)
        recommendations.sort(key=lambda x: x.get('priority', 0), reverse=True)
        
        return recommendations[:10]  # Return top 10 recommendations
    
    def _calculate_success_probabilities(self, recommendations: List[Dict], 
                                       historical_context: Dict) -> Dict:
        """Calculate success probability for each recommendation"""
        probabilities = {}
        
        for i, rec in enumerate(recommendations):
            base_probability = historical_context.get('success_rate', 50)
            
            # Adjust based on recommendation type
            if rec['type'] == 'auto_fix':
                # Auto-fix commands have variable success rates
                confidence_boost = rec.get('confidence', 50) * 0.3
                probabilities[i] = min(95, base_probability + confidence_boost)
                
            elif rec['type'] == 'historical_fix':
                # Historical fixes have proven success rates
                usage_boost = min(30, rec.get('usage_count', 1) * 5)
                probabilities[i] = min(95, base_probability + usage_boost)
                
            elif rec['type'] == 'environment_fix':
                # Environment fixes address root causes
                probabilities[i] = min(90, base_probability + 20)
                
            else:
                probabilities[i] = base_probability
        
        return probabilities
    
    def _calculate_pattern_confidence(self, regex_pattern: str, error_output: str) -> float:
        """Calculate confidence score for pattern match"""
        try:
            matches = re.findall(regex_pattern, error_output, re.IGNORECASE)
            match_count = len(matches)
            
            # Base confidence on number of matches and pattern specificity
            base_confidence = min(90, 50 + (match_count * 10))
            
            # Boost confidence for more specific patterns
            if len(regex_pattern) > 20:  # More specific patterns
                base_confidence += 10
            
            return min(95, base_confidence)
            
        except:
            return 50.0
    
    def _calculate_priority(self, pattern: Dict, historical_context: Dict) -> int:
        """Calculate priority score for a recommendation"""
        base_priority = 50
        
        # Severity boost
        severity_boost = {
            'critical': 40,
            'high': 30,
            'medium': 20,
            'low': 10
        }.get(pattern['severity'], 15)
        
        # Confidence boost
        confidence_boost = pattern['confidence'] * 0.3
        
        # Historical success boost
        success_rate = historical_context.get('success_rate', 0)
        history_boost = success_rate * 0.2
        
        return int(base_priority + severity_boost + confidence_boost + history_boost)
    
    def _calculate_confidence_score(self, historical_context: Dict, detected_patterns: List[Dict]) -> float:
        """Calculate overall confidence in the guidance"""
        if not detected_patterns:
            return 30.0
        
        # Base confidence on pattern detection quality
        pattern_confidence = sum(p['confidence'] for p in detected_patterns) / len(detected_patterns)
        
        # Boost confidence with historical data
        similar_count = historical_context.get('similar_count', 0)
        history_boost = min(20, similar_count * 2)
        
        # Success rate boost
        success_rate = historical_context.get('success_rate', 0)
        success_boost = success_rate * 0.2
        
        total_confidence = min(95, pattern_confidence + history_boost + success_boost)
        
        return round(total_confidence, 1)
    
    def record_resolution_attempt(self, build_id: str, recommendation_index: int, 
                                commands_executed: List[str], success: bool, 
                                recovery_time_seconds: int) -> bool:
        """Record the outcome of a resolution attempt for learning"""
        try:
            # This would be called after attempting a recommended fix
            self.db.execute_query("""
                INSERT INTO recovery_actions 
                (build_id, recovery_type, commands_executed, success, recovery_time_seconds)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                build_id, 
                'intelligent_guidance',
                json.dumps(commands_executed),
                success,
                recovery_time_seconds
            ))
            
            return True
            
        except Exception as e:
            print(f"Failed to record resolution attempt: {e}")
            return False
    
    def get_learning_insights(self, days: int = 30) -> Dict:
        """Get insights about the effectiveness of intelligent guidance"""
        try:
            # Get guidance effectiveness stats
            effectiveness = self.db.execute_query("""
                SELECT 
                    recovery_type,
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_attempts,
                    AVG(recovery_time_seconds) as avg_recovery_time
                FROM recovery_actions
                WHERE timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
                AND recovery_type = 'intelligent_guidance'
                GROUP BY recovery_type
            """, (days,), fetch=True)
            
            # Get most effective patterns
            effective_patterns = self.db.execute_query("""
                SELECT 
                    fp.pattern_name,
                    COUNT(ra.id) as usage_count,
                    AVG(CASE WHEN ra.success THEN 100 ELSE 0 END) as success_rate
                FROM failure_patterns fp
                JOIN recovery_actions ra ON fp.id = ra.failure_pattern_id
                WHERE ra.timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY fp.id, fp.pattern_name
                ORDER BY success_rate DESC, usage_count DESC
                LIMIT 10
            """, (days,), fetch=True)
            
            return {
                'effectiveness_stats': effectiveness,
                'top_effective_patterns': effective_patterns,
                'analysis_period_days': days
            }
            
        except Exception as e:
            print(f"Failed to get learning insights: {e}")
            return {'effectiveness_stats': [], 'top_effective_patterns': []}