#!/usr/bin/env python3
"""
Root Cause Analysis for LFS Build System
Analyzes dependency chains and environmental factors to identify root causes of failures
"""

import re
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

class RootCauseAnalyzer:
    def __init__(self, db_manager):
        self.db = db_manager
        self.dependency_patterns = self._initialize_dependency_patterns()
        self.environmental_correlations = self._initialize_environmental_correlations()
    
    def _initialize_dependency_patterns(self) -> Dict:
        """Initialize patterns for dependency chain analysis"""
        return {
            'stage_dependencies': {
                'prepare_host': [],
                'download_sources': ['prepare_host'],
                'build_toolchain': ['download_sources'],
                'build_temp_system': ['build_toolchain'],
                'chroot_environment': ['build_temp_system'],
                'build_final_system': ['chroot_environment'],
                'system_configuration': ['build_final_system'],
                'kernel_build': ['system_configuration'],
                'bootloader_setup': ['kernel_build']
            },
            'failure_propagation': {
                'permission_errors': ['prepare_host', 'download_sources'],
                'compilation_errors': ['build_toolchain', 'build_temp_system', 'build_final_system'],
                'configuration_errors': ['system_configuration', 'kernel_build'],
                'network_errors': ['download_sources'],
                'disk_space_errors': ['download_sources', 'build_toolchain', 'build_temp_system']
            }
        }
    
    def _initialize_environmental_correlations(self) -> Dict:
        """Initialize environmental factor correlation patterns"""
        return {
            'system_resources': {
                'low_memory': ['compilation_errors', 'linker_errors'],
                'low_disk_space': ['download_failures', 'build_failures'],
                'high_cpu_load': ['timeout_errors', 'performance_issues']
            },
            'temporal_patterns': {
                'time_of_day': ['network_timeouts', 'mirror_availability'],
                'day_of_week': ['system_maintenance', 'resource_contention'],
                'system_uptime': ['memory_leaks', 'resource_exhaustion']
            },
            'configuration_factors': {
                'host_system_version': ['compatibility_issues', 'tool_version_conflicts'],
                'package_versions': ['dependency_conflicts', 'api_changes'],
                'build_environment': ['path_issues', 'environment_variables']
            }
        }
    
    def analyze_failure_root_cause(self, build_id: str) -> Dict:
        """Perform comprehensive root cause analysis for a failed build"""
        try:
            # Get build details
            build_details = self.db.get_build_details(build_id)
            if not build_details:
                return {'error': 'Build not found'}
            
            build = build_details['build']
            stages = build_details['stages']
            documents = build_details['documents']
            
            if build.get('status') not in ['failed', 'cancelled']:
                return {'error': 'Build did not fail - no root cause analysis needed'}
            
            # Perform different types of analysis
            dependency_analysis = self._analyze_dependency_chain(stages)
            environmental_analysis = self._analyze_environmental_factors(build, documents)
            comparative_analysis = self._analyze_comparative_factors(build_id, build)
            timeline_analysis = self._analyze_failure_timeline(stages, documents)
            
            # Determine primary root cause
            root_cause = self._determine_primary_root_cause(
                dependency_analysis, environmental_analysis, 
                comparative_analysis, timeline_analysis
            )
            
            return {
                'build_id': build_id,
                'analysis_time': datetime.now().isoformat(),
                'root_cause': root_cause,
                'dependency_analysis': dependency_analysis,
                'environmental_analysis': environmental_analysis,
                'comparative_analysis': comparative_analysis,
                'timeline_analysis': timeline_analysis,
                'recommendations': self._generate_root_cause_recommendations(root_cause)
            }
            
        except Exception as e:
            return {'error': f'Root cause analysis failed: {str(e)}'}
    
    def _analyze_dependency_chain(self, stages: List[Dict]) -> Dict:
        """Analyze the dependency chain to find upstream causes"""
        failed_stages = []
        successful_stages = []
        dependency_issues = []
        
        # Categorize stages by status
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            stage_name = stage.get('stage_name')
            status = stage.get('status')
            
            if status == 'failed':
                failed_stages.append(stage_name)
            elif status in ['completed', 'success']:
                successful_stages.append(stage_name)
        
        # Analyze dependency chain failures
        stage_deps = self.dependency_patterns['stage_dependencies']
        
        for failed_stage in failed_stages:
            if failed_stage in stage_deps:
                dependencies = stage_deps[failed_stage]
                
                # Check if dependencies completed successfully
                missing_deps = [dep for dep in dependencies if dep not in successful_stages]
                if missing_deps:
                    dependency_issues.append({
                        'failed_stage': failed_stage,
                        'missing_dependencies': missing_deps,
                        'type': 'missing_dependency',
                        'severity': 'high'
                    })
                
                # Check for failed dependencies
                failed_deps = [dep for dep in dependencies if dep in failed_stages]
                if failed_deps:
                    dependency_issues.append({
                        'failed_stage': failed_stage,
                        'failed_dependencies': failed_deps,
                        'type': 'upstream_failure',
                        'severity': 'critical'
                    })
        
        # Find root cause stage (earliest failure in dependency chain)
        root_stage = None
        if failed_stages:
            # Sort by typical stage order
            stage_order = list(stage_deps.keys())
            failed_stages_ordered = [s for s in stage_order if s in failed_stages]
            if failed_stages_ordered:
                root_stage = failed_stages_ordered[0]
        
        return {
            'failed_stages': failed_stages,
            'successful_stages': successful_stages,
            'dependency_issues': dependency_issues,
            'root_stage': root_stage,
            'cascade_failure': len(failed_stages) > 1 and len(dependency_issues) > 0
        }
    
    def _analyze_environmental_factors(self, build: Dict, documents: List[Dict]) -> Dict:
        """Analyze environmental factors that may have caused the failure"""
        environmental_factors = []
        
        # Analyze build timing
        start_time = build.get('start_time')
        if start_time:
            hour = start_time.hour
            weekday = start_time.weekday()
            
            # Check for problematic timing
            if hour < 6 or hour > 22:
                environmental_factors.append({
                    'type': 'timing',
                    'factor': 'off_hours_build',
                    'details': f'Build started at {hour:02d}:00 (off-hours)',
                    'impact': 'medium',
                    'explanation': 'Off-hours builds may have reduced monitoring and support'
                })
            
            if weekday >= 5:  # Weekend
                environmental_factors.append({
                    'type': 'timing',
                    'factor': 'weekend_build',
                    'details': f'Build started on weekend (day {weekday})',
                    'impact': 'low',
                    'explanation': 'Weekend builds may have delayed issue resolution'
                })
        
        # Analyze system resource indicators from documents
        resource_issues = self._extract_resource_issues(documents)
        environmental_factors.extend(resource_issues)
        
        # Analyze network/connectivity issues
        network_issues = self._extract_network_issues(documents)
        environmental_factors.extend(network_issues)
        
        # Analyze host system compatibility issues
        compatibility_issues = self._extract_compatibility_issues(documents)
        environmental_factors.extend(compatibility_issues)
        
        return {
            'factors': environmental_factors,
            'primary_environmental_cause': self._identify_primary_environmental_cause(environmental_factors)
        }
    
    def _analyze_comparative_factors(self, build_id: str, build: Dict) -> Dict:
        """Compare failed build with similar successful builds"""
        try:
            # Get recent successful builds for comparison
            successful_builds = self.db.execute_query("""
                SELECT build_id, start_time, end_time, config_name 
                FROM builds 
                WHERE status = 'completed' 
                AND start_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                ORDER BY start_time DESC 
                LIMIT 5
            """, fetch=True)
            
            if not successful_builds:
                return {'differences': [], 'analysis': 'No recent successful builds for comparison'}
            
            differences = []
            
            # Compare timing patterns
            failed_start = build.get('start_time')
            if failed_start:
                for success_build in successful_builds:
                    success_start = success_build['start_time']
                    
                    # Compare time of day
                    if abs(failed_start.hour - success_start.hour) > 6:
                        differences.append({
                            'type': 'timing_difference',
                            'factor': 'time_of_day',
                            'failed_build_hour': failed_start.hour,
                            'successful_build_hour': success_start.hour,
                            'impact': 'medium'
                        })
            
            # Compare configuration differences (if available)
            config_differences = self._compare_build_configurations(build_id, successful_builds)
            differences.extend(config_differences)
            
            # Compare system state differences
            system_differences = self._compare_system_states(build_id, successful_builds)
            differences.extend(system_differences)
            
            return {
                'differences': differences,
                'successful_builds_analyzed': len(successful_builds),
                'key_differences': [d for d in differences if d.get('impact') in ['high', 'critical']]
            }
            
        except Exception as e:
            return {'error': f'Comparative analysis failed: {str(e)}'}
    
    def _analyze_failure_timeline(self, stages: List[Dict], documents: List[Dict]) -> Dict:
        """Analyze the timeline of events leading to failure"""
        timeline_events = []
        
        # Add stage events
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            
            stage_name = stage.get('stage_name')
            status = stage.get('status')
            start_time = stage.get('start_time')
            end_time = stage.get('end_time')
            
            if start_time:
                timeline_events.append({
                    'timestamp': start_time,
                    'type': 'stage_start',
                    'stage': stage_name,
                    'status': status
                })
            
            if end_time:
                timeline_events.append({
                    'timestamp': end_time,
                    'type': 'stage_end',
                    'stage': stage_name,
                    'status': status
                })
        
        # Add document events (errors, warnings)
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            
            created_at = doc.get('created_at')
            doc_type = doc.get('document_type')
            title = doc.get('title', '')
            content = doc.get('content', '')
            
            if created_at and doc_type == 'error':
                timeline_events.append({
                    'timestamp': created_at,
                    'type': 'error_event',
                    'title': title,
                    'severity': self._classify_error_severity(content)
                })
        
        # Sort events by timestamp
        timeline_events.sort(key=lambda x: x['timestamp'])
        
        # Identify critical moments
        critical_moments = self._identify_critical_moments(timeline_events)
        
        return {
            'timeline': timeline_events,
            'critical_moments': critical_moments,
            'failure_sequence': self._reconstruct_failure_sequence(timeline_events)
        }
    
    def _extract_resource_issues(self, documents: List[Dict]) -> List[Dict]:
        """Extract system resource issues from documents"""
        resource_issues = []
        
        resource_patterns = {
            'memory': [
                r'out of memory|memory.*exhausted|cannot allocate memory',
                r'virtual memory.*exceeded|malloc.*failed'
            ],
            'disk_space': [
                r'no space left on device|disk.*full|cannot write',
                r'insufficient.*space|disk.*quota.*exceeded'
            ],
            'cpu': [
                r'load.*average.*high|cpu.*overload|system.*overloaded'
            ]
        }
        
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            content = doc.get('content', '')
            
            for resource_type, patterns in resource_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        resource_issues.append({
                            'type': 'resource',
                            'factor': f'{resource_type}_exhaustion',
                            'details': f'{resource_type.title()} resource exhaustion detected',
                            'impact': 'high',
                            'explanation': f'System {resource_type} resources were insufficient for build requirements'
                        })
                        break
        
        return resource_issues
    
    def _extract_network_issues(self, documents: List[Dict]) -> List[Dict]:
        """Extract network/connectivity issues from documents"""
        network_issues = []
        
        network_patterns = [
            r'connection.*refused|connection.*timeout|network.*unreachable',
            r'download.*failed|404.*not found|mirror.*unavailable',
            r'dns.*resolution.*failed|host.*not found'
        ]
        
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            content = doc.get('content', '')
            
            for pattern in network_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    network_issues.append({
                        'type': 'network',
                        'factor': 'connectivity_issue',
                        'details': 'Network connectivity or mirror availability issue detected',
                        'impact': 'medium',
                        'explanation': 'Network issues prevented package downloads or updates'
                    })
                    break
        
        return network_issues
    
    def _extract_compatibility_issues(self, documents: List[Dict]) -> List[Dict]:
        """Extract host system compatibility issues from documents"""
        compatibility_issues = []
        
        compatibility_patterns = [
            r'version.*mismatch|incompatible.*version|unsupported.*version',
            r'command not found|no such file or directory.*bin/',
            r'library.*not found|shared.*library.*error'
        ]
        
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            content = doc.get('content', '')
            
            for pattern in compatibility_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    compatibility_issues.append({
                        'type': 'compatibility',
                        'factor': 'host_system_incompatibility',
                        'details': 'Host system compatibility issue detected',
                        'impact': 'high',
                        'explanation': 'Host system lacks required tools or has incompatible versions'
                    })
                    break
        
        return compatibility_issues
    
    def _identify_primary_environmental_cause(self, factors: List[Dict]) -> Optional[Dict]:
        """Identify the primary environmental cause from all factors"""
        if not factors:
            return None
        
        # Sort by impact level
        impact_weights = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        factors_weighted = sorted(factors, key=lambda x: impact_weights.get(x.get('impact', 'low'), 0), reverse=True)
        
        return factors_weighted[0] if factors_weighted else None
    
    def _compare_build_configurations(self, build_id: str, successful_builds: List[Dict]) -> List[Dict]:
        """Compare build configurations to identify differences"""
        # This would require storing and comparing build configurations
        # For now, return empty list as configuration comparison needs more infrastructure
        return []
    
    def _compare_system_states(self, build_id: str, successful_builds: List[Dict]) -> List[Dict]:
        """Compare system states between failed and successful builds"""
        # This would require storing system state information
        # For now, return empty list as system state comparison needs more infrastructure
        return []
    
    def _classify_error_severity(self, content: str) -> str:
        """Classify error severity based on content"""
        critical_patterns = [r'fatal error|critical error|segmentation fault']
        high_patterns = [r'error:|compilation.*error|linker.*error']
        medium_patterns = [r'warning:|deprecated|implicit']
        
        for pattern in critical_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return 'critical'
        
        for pattern in high_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return 'high'
        
        for pattern in medium_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return 'medium'
        
        return 'low'
    
    def _identify_critical_moments(self, timeline_events: List[Dict]) -> List[Dict]:
        """Identify critical moments in the failure timeline"""
        critical_moments = []
        
        # Find first error
        first_error = None
        for event in timeline_events:
            if event['type'] == 'error_event':
                first_error = event
                break
        
        if first_error:
            critical_moments.append({
                'timestamp': first_error['timestamp'],
                'type': 'first_error',
                'description': f"First error occurred: {first_error['title']}",
                'significance': 'high'
            })
        
        # Find first stage failure
        first_failure = None
        for event in timeline_events:
            if event['type'] == 'stage_end' and event['status'] == 'failed':
                first_failure = event
                break
        
        if first_failure:
            critical_moments.append({
                'timestamp': first_failure['timestamp'],
                'type': 'first_stage_failure',
                'description': f"First stage failure: {first_failure['stage']}",
                'significance': 'critical'
            })
        
        return critical_moments
    
    def _reconstruct_failure_sequence(self, timeline_events: List[Dict]) -> List[str]:
        """Reconstruct the sequence of events leading to failure"""
        sequence = []
        
        for event in timeline_events:
            if event['type'] == 'stage_start':
                sequence.append(f"Started {event['stage']} stage")
            elif event['type'] == 'stage_end':
                if event['status'] == 'failed':
                    sequence.append(f"❌ {event['stage']} stage failed")
                elif event['status'] in ['completed', 'success']:
                    sequence.append(f"✅ {event['stage']} stage completed")
            elif event['type'] == 'error_event':
                sequence.append(f"🚨 Error: {event['title']}")
        
        return sequence
    
    def _determine_primary_root_cause(self, dependency_analysis: Dict, environmental_analysis: Dict, 
                                    comparative_analysis: Dict, timeline_analysis: Dict) -> Dict:
        """Determine the primary root cause from all analyses"""
        
        # Priority order for root cause determination
        # 1. Critical dependency failures
        # 2. High-impact environmental factors
        # 3. System resource issues
        # 4. Configuration differences
        
        root_cause = {
            'category': 'unknown',
            'description': 'Unable to determine root cause',
            'confidence': 'low',
            'evidence': []
        }
        
        # Check for dependency chain issues (highest priority)
        if dependency_analysis.get('dependency_issues'):
            critical_deps = [issue for issue in dependency_analysis['dependency_issues'] 
                           if issue.get('severity') == 'critical']
            if critical_deps:
                root_cause = {
                    'category': 'dependency_failure',
                    'description': f"Upstream dependency failure in {critical_deps[0].get('failed_dependencies', ['unknown'])[0]}",
                    'confidence': 'high',
                    'evidence': [f"Stage {critical_deps[0]['failed_stage']} failed due to upstream failure"],
                    'root_stage': dependency_analysis.get('root_stage')
                }
        
        # Check for environmental factors (second priority)
        elif environmental_analysis.get('primary_environmental_cause'):
            primary_env = environmental_analysis['primary_environmental_cause']
            if primary_env.get('impact') in ['critical', 'high']:
                root_cause = {
                    'category': 'environmental',
                    'description': primary_env.get('explanation', 'Environmental factor caused failure'),
                    'confidence': 'high' if primary_env.get('impact') == 'critical' else 'medium',
                    'evidence': [primary_env.get('details', 'Environmental issue detected')],
                    'environmental_factor': primary_env.get('factor')
                }
        
        # Check for comparative differences (third priority)
        elif comparative_analysis.get('key_differences'):
            key_diff = comparative_analysis['key_differences'][0]
            root_cause = {
                'category': 'configuration_difference',
                'description': f"Build differs from successful builds in {key_diff.get('factor', 'unknown aspect')}",
                'confidence': 'medium',
                'evidence': [f"Key difference: {key_diff.get('type', 'unknown')}"],
                'difference_type': key_diff.get('type')
            }
        
        return root_cause
    
    def _generate_root_cause_recommendations(self, root_cause: Dict) -> List[str]:
        """Generate actionable recommendations based on root cause"""
        recommendations = []
        
        category = root_cause.get('category', 'unknown')
        
        if category == 'dependency_failure':
            recommendations.extend([
                f"Fix the upstream failure in {root_cause.get('root_stage', 'unknown')} stage first",
                "Review dependency chain and ensure all prerequisites are met",
                "Check for missing tools or libraries required by failed stage",
                "Consider running stages individually to isolate the specific failure point"
            ])
        
        elif category == 'environmental':
            env_factor = root_cause.get('environmental_factor', '')
            if 'memory' in env_factor:
                recommendations.extend([
                    "Increase available system memory or close other applications",
                    "Consider using swap space if memory is limited",
                    "Monitor memory usage during builds and optimize if needed"
                ])
            elif 'disk' in env_factor:
                recommendations.extend([
                    "Free up disk space before retrying the build",
                    "Consider using external storage for build artifacts",
                    "Monitor disk usage and set up alerts for low space"
                ])
            elif 'network' in env_factor:
                recommendations.extend([
                    "Check network connectivity and retry the build",
                    "Try different package mirrors if downloads are failing",
                    "Consider downloading packages manually if mirrors are unavailable"
                ])
            else:
                recommendations.append("Address the identified environmental issue before retrying")
        
        elif category == 'configuration_difference':
            recommendations.extend([
                "Compare build configuration with recent successful builds",
                "Check for changes in host system or build environment",
                "Verify all required tools and dependencies are properly installed",
                "Consider reverting to a known working configuration"
            ])
        
        else:
            recommendations.extend([
                "Review build logs for specific error messages",
                "Check system resources (memory, disk space, CPU)",
                "Verify host system meets LFS requirements",
                "Consider running a clean build from scratch"
            ])
        
        # Add general recommendations
        recommendations.extend([
            "Document the issue and solution for future reference",
            "Consider running the fault analysis tool for additional insights"
        ])
        
        return recommendations