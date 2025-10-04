#!/usr/bin/env python3
"""
Advanced Fault Analyzer for LFS Build System
Analyzes build failures with comprehensive insights, trends, and auto-fix suggestions
"""

import re
import json
import os
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

# Import advanced analysis modules
try:
    from .predictive_analyzer import PredictiveAnalyzer
    from .root_cause_analyzer import RootCauseAnalyzer
    from .performance_analyzer import PerformanceAnalyzer
    from .intelligent_guidance_engine import IntelligentGuidanceEngine
except ImportError:
    # Fallback if modules not available
    PredictiveAnalyzer = None
    RootCauseAnalyzer = None
    PerformanceAnalyzer = None
    IntelligentGuidanceEngine = None

class FaultPattern:
    def __init__(self, name: str, pattern: str, severity: str, description: str, solution: str, auto_fix_command: str = None):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        self.severity = severity  # Critical, High, Medium, Low
        self.description = description
        self.solution = solution
        self.auto_fix_command = auto_fix_command
        self.count = 0
        self.recent_builds = []
        self.stage_occurrences = defaultdict(int)

class FaultAnalyzer:
    def __init__(self, db_manager):
        self.db = db_manager
        self.fault_patterns = self._initialize_patterns()
        
        # Initialize advanced analyzers
        self.predictive_analyzer = PredictiveAnalyzer(db_manager) if PredictiveAnalyzer else None
        self.root_cause_analyzer = RootCauseAnalyzer(db_manager) if RootCauseAnalyzer else None
        self.performance_analyzer = PerformanceAnalyzer(db_manager) if PerformanceAnalyzer else None
        self.guidance_engine = IntelligentGuidanceEngine(db_manager) if IntelligentGuidanceEngine else None
    
    def _initialize_patterns(self) -> List[FaultPattern]:
        """Initialize common LFS build fault patterns with auto-fix commands"""
        return [
            # Critical Issues
            FaultPattern(
                "Permission Denied",
                r"permission denied|cannot create directory|operation not permitted",
                "Critical",
                "File system permission issues preventing build operations",
                "Run 'Setup LFS Permissions' from Build Actions menu or check /mnt/lfs ownership",
                "sudo chown -R lfs:lfs /mnt/lfs && sudo chmod -R 755 /mnt/lfs"
            ),
            FaultPattern(
                "Disk Space Full",
                r"no space left on device|disk full|cannot write",
                "Critical", 
                "Insufficient disk space for build operations",
                "Free up disk space or use external storage via Settings",
                "df -h && sudo du -sh /mnt/lfs/* | sort -hr"
            ),
            FaultPattern(
                "Missing Dependencies",
                r"command not found|no such file or directory.*bin/|cannot find -l",
                "Critical",
                "Required build tools or libraries are missing from host system",
                "Install missing dependencies: sudo dnf install gcc make binutils",
                "sudo dnf groupinstall 'Development Tools' && sudo dnf install gcc-c++ glibc-devel"
            ),
            
            # High Severity
            FaultPattern(
                "Compilation Errors",
                r"error:|fatal error:|compilation terminated|collect2: error:",
                "High",
                "Source code compilation failures in toolchain or packages",
                "Check compiler version compatibility and package source integrity",
                "gcc --version && make clean && make -j1"
            ),
            FaultPattern(
                "Linker Errors", 
                r"undefined reference|cannot find -l|ld: error:|relocation truncated",
                "High",
                "Linking failures during compilation process",
                "Verify library paths and ensure all dependencies are built correctly",
                "ldconfig -p | grep -i missing_lib && export LD_LIBRARY_PATH=/mnt/lfs/usr/lib"
            ),
            FaultPattern(
                "Configure Script Failures",
                r"configure: error:|config.status: error:|cannot run C compiled programs",
                "High",
                "Package configuration script failures",
                "Check host system compatibility and required development packages",
                "./configure --help && export CC=gcc CXX=g++"
            ),
            
            # Medium Severity
            FaultPattern(
                "Make Errors",
                r"make.*error|make.*failed|recipe for target.*failed",
                "Medium",
                "Build process failures in make system",
                "Check for missing files, incorrect paths, or parallel build issues",
                "make clean && make -j1 VERBOSE=1"
            ),
            FaultPattern(
                "Network/Download Issues",
                r"download failed|connection refused|timeout|404 not found",
                "Medium",
                "Package download or mirror connectivity problems",
                "Check network connection or try different mirrors in Package Manager",
                "ping -c 3 8.8.8.8 && curl -I http://ftp.gnu.org/"
            ),
            FaultPattern(
                "Path Issues",
                r"no such file or directory(?!.*bin/)|file not found|cannot access",
                "Medium",
                "File or directory path problems",
                "Verify file paths and ensure previous build stages completed successfully",
                "find /mnt/lfs -name 'missing_file' 2>/dev/null"
            ),
            
            # Low Severity
            FaultPattern(
                "Warnings",
                r"warning:|note:|deprecated|implicit declaration",
                "Low",
                "Compilation warnings that may indicate potential issues",
                "Review warnings for potential compatibility issues, usually non-critical"
            ),
            FaultPattern(
                "Missing Documentation Tools",
                r"makeinfo.*missing|help2man.*not found|documentation will not be built",
                "Low",
                "Documentation generation tools missing (non-critical for LFS)",
                "Install texinfo package if documentation is needed: sudo dnf install texinfo",
                "sudo dnf install texinfo help2man"
            )
        ]
    
    def analyze_comprehensive(self, days: int = 30) -> Dict:
        """Comprehensive analysis including failures, trends, and success rates"""
        try:
            failure_analysis = self.analyze_build_failures(days)
            stage_analysis = self.analyze_by_stage(days)
            trend_analysis = self.analyze_trends(days)
            success_rates = self.calculate_success_rates(days)
            new_patterns = self.detect_new_patterns(days)
            
            # Advanced analysis modules
            performance_analysis = None
            if self.performance_analyzer:
                performance_analysis = self.performance_analyzer.analyze_performance_correlation(days)
            
            return {
                'failure_analysis': failure_analysis,
                'stage_analysis': stage_analysis,
                'trend_analysis': trend_analysis,
                'success_rates': success_rates,
                'new_patterns': new_patterns,
                'performance_analysis': performance_analysis,
                'summary': f"Comprehensive analysis of last {days} days completed"
            }
        except Exception as e:
            return {'error': f"Comprehensive analysis failed: {str(e)}"}
    
    def analyze_build_failures(self, days: int = 30) -> Dict:
        """Analyze build failures from the last N days"""
        try:
            # Get failed builds from last N days
            cutoff_date = datetime.now() - timedelta(days=days)
            
            failed_builds = self.db.execute_query("""
                SELECT build_id, start_time FROM builds 
                WHERE status IN ('failed', 'cancelled') 
                AND start_time >= %s
                ORDER BY start_time DESC
            """, (cutoff_date,), fetch=True)
            
            if not failed_builds:
                return {
                    'total_failures': 0,
                    'patterns': [],
                    'recommendations': [],
                    'summary': 'No build failures found in the specified period.'
                }
            
            # Reset pattern counts
            for pattern in self.fault_patterns:
                pattern.count = 0
                pattern.recent_builds = []
            
            # Analyze each failed build
            total_analyzed = 0
            for build in failed_builds:
                build_id = build['build_id']
                
                # Get error and log documents for this build (context-aware analysis)
                error_docs = self.db.execute_query("""
                    SELECT content, title, document_type FROM build_documents 
                    WHERE build_id = %s 
                    AND (document_type IN ('error', 'log') 
                         OR title LIKE '%error%' OR title LIKE '%failed%'
                         OR content LIKE '%error%' OR content LIKE '%failed%')
                """, (build_id,), fetch=True)
                
                # Get stage information for this build
                stage_info = self.db.execute_query("""
                    SELECT stage_name FROM build_stages 
                    WHERE build_id = %s AND status = 'failed'
                """, (build_id,), fetch=True)
                
                failed_stages = [s['stage_name'] for s in stage_info]
                
                # Analyze error content
                build_content = ""
                for doc in error_docs:
                    build_content += doc['content'] + "\n"
                
                if build_content.strip():
                    self._analyze_content(build_content, build_id, build['start_time'], failed_stages)
                    total_analyzed += 1
            
            # Sort patterns by count (most common first)
            sorted_patterns = sorted(
                [p for p in self.fault_patterns if p.count > 0],
                key=lambda x: (self._severity_weight(x.severity), x.count),
                reverse=True
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(sorted_patterns)
            
            return {
                'total_failures': len(failed_builds),
                'analyzed_builds': total_analyzed,
                'patterns': [self._pattern_to_dict(p) for p in sorted_patterns],
                'recommendations': recommendations,
                'summary': f"Analyzed {total_analyzed} failed builds from last {days} days"
            }
            
        except Exception as e:
            return {
                'error': f"Analysis failed: {str(e)}",
                'total_failures': 0,
                'patterns': [],
                'recommendations': []
            }
    
    def analyze_build_risk(self, build_id: str) -> Dict:
        """Analyze risk factors for a running build using predictive analysis"""
        if self.predictive_analyzer:
            return self.predictive_analyzer.analyze_build_risk(build_id)
        else:
            return {'error': 'Predictive analysis not available'}
    
    def get_intelligent_guidance(self, build_id: str, stage_name: str, error_output: str) -> Dict:
        """Get intelligent next-attempt guidance based on historical data"""
        if self.guidance_engine:
            return self.guidance_engine.analyze_failure_and_suggest_next_steps(build_id, stage_name, error_output)
        else:
            return {'error': 'Intelligent guidance not available', 'recommendations': []}
    
    def record_fix_attempt(self, build_id: str, recommendation_index: int, commands_executed: List[str], 
                          success: bool, recovery_time_seconds: int) -> bool:
        """Record the outcome of a fix attempt for learning"""
        if self.guidance_engine:
            return self.guidance_engine.record_resolution_attempt(
                build_id, recommendation_index, commands_executed, success, recovery_time_seconds
            )
        return False
    
    def get_guidance_effectiveness(self, days: int = 30) -> Dict:
        """Get insights about guidance effectiveness"""
        if self.guidance_engine:
            return self.guidance_engine.get_learning_insights(days)
        return {'effectiveness_stats': [], 'top_effective_patterns': []}
    
    def analyze_root_cause(self, build_id: str) -> Dict:
        """Perform root cause analysis for a failed build"""
        if self.root_cause_analyzer:
            return self.root_cause_analyzer.analyze_failure_root_cause(build_id)
        else:
            return {'error': 'Root cause analysis not available'}
    
    def get_early_warning_indicators(self, build_id: str) -> Dict:
        """Get early warning indicators for a running build"""
        if self.predictive_analyzer:
            return self.predictive_analyzer.get_early_warning_indicators(build_id)
        else:
            return {'error': 'Early warning system not available'}
    
    def predict_build_success(self, build_config: Dict = None) -> Dict:
        """Predict success probability for a new build"""
        if self.predictive_analyzer:
            return self.predictive_analyzer.predict_build_success_probability(build_config or {})
        else:
            return {'error': 'Build prediction not available'}
    
    def get_build_performance_score(self, build_id: str) -> Dict:
        """Get performance score for a specific build"""
        if self.performance_analyzer:
            return self.performance_analyzer.get_build_performance_score(build_id)
        else:
            return {'error': 'Performance analysis not available'}
    
    def analyze_by_stage(self, days: int = 30) -> Dict:
        """Analyze failures by build stage"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get stage failure counts
            stage_failures = self.db.execute_query("""
                SELECT stage_name, COUNT(*) as failure_count,
                       AVG(TIMESTAMPDIFF(MINUTE, start_time, end_time)) as avg_duration
                FROM build_stages 
                WHERE status = 'failed' AND start_time >= %s
                GROUP BY stage_name ORDER BY failure_count DESC
            """, (cutoff_date,), fetch=True)
            
            # Get stage success counts for comparison
            stage_success = self.db.execute_query("""
                SELECT stage_name, COUNT(*) as success_count
                FROM build_stages 
                WHERE status = 'completed' AND start_time >= %s
                GROUP BY stage_name
            """, (cutoff_date,), fetch=True)
            
            success_dict = {s['stage_name']: s['success_count'] for s in stage_success}
            
            # Calculate failure rates
            stage_analysis = []
            for stage in stage_failures:
                stage_name = stage['stage_name']
                failures = stage['failure_count']
                successes = success_dict.get(stage_name, 0)
                total = failures + successes
                failure_rate = (failures / total * 100) if total > 0 else 0
                
                stage_analysis.append({
                    'stage_name': stage_name,
                    'failure_count': failures,
                    'success_count': successes,
                    'failure_rate': round(failure_rate, 1),
                    'avg_duration': round(stage.get('avg_duration', 0) or 0, 1)
                })
            
            return {
                'stages': stage_analysis,
                'most_problematic': stage_analysis[0]['stage_name'] if stage_analysis else None,
                'total_stage_failures': sum(s['failure_count'] for s in stage_analysis)
            }
            
        except Exception as e:
            return {'error': f"Stage analysis failed: {str(e)}", 'stages': []}
    
    def analyze_trends(self, days: int = 30) -> Dict:
        """Analyze failure trends over time"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            previous_cutoff = cutoff_date - timedelta(days=days)
            
            # Current period failures
            current_failures = self.db.execute_query("""
                SELECT COUNT(*) as count FROM builds 
                WHERE status IN ('failed', 'cancelled') AND start_time >= %s
            """, (cutoff_date,), fetch=True)[0]['count']
            
            # Previous period failures
            previous_failures = self.db.execute_query("""
                SELECT COUNT(*) as count FROM builds 
                WHERE status IN ('failed', 'cancelled') 
                AND start_time >= %s AND start_time < %s
            """, (previous_cutoff, cutoff_date), fetch=True)[0]['count']
            
            # Calculate trend
            if previous_failures > 0:
                trend_percentage = ((current_failures - previous_failures) / previous_failures) * 100
            else:
                trend_percentage = 100 if current_failures > 0 else 0
            
            trend_direction = "improving" if trend_percentage < -10 else "worsening" if trend_percentage > 10 else "stable"
            
            # Weekly breakdown
            weekly_data = []
            for week in range(4):
                week_start = datetime.now() - timedelta(days=(week + 1) * 7)
                week_end = datetime.now() - timedelta(days=week * 7)
                
                week_failures = self.db.execute_query("""
                    SELECT COUNT(*) as count FROM builds 
                    WHERE status IN ('failed', 'cancelled') 
                    AND start_time >= %s AND start_time < %s
                """, (week_start, week_end), fetch=True)[0]['count']
                
                weekly_data.append({
                    'week': f"Week {4-week}",
                    'failures': week_failures
                })
            
            return {
                'current_period_failures': current_failures,
                'previous_period_failures': previous_failures,
                'trend_percentage': round(trend_percentage, 1),
                'trend_direction': trend_direction,
                'weekly_breakdown': weekly_data
            }
            
        except Exception as e:
            return {'error': f"Trend analysis failed: {str(e)}"}
    
    def calculate_success_rates(self, days: int = 30) -> Dict:
        """Calculate success rates by stage and overall"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Overall success rate
            total_builds = self.db.execute_query("""
                SELECT COUNT(*) as count FROM builds WHERE start_time >= %s
            """, (cutoff_date,), fetch=True)[0]['count']
            
            successful_builds = self.db.execute_query("""
                SELECT COUNT(*) as count FROM builds 
                WHERE status = 'completed' AND start_time >= %s
            """, (cutoff_date,), fetch=True)[0]['count']
            
            overall_success_rate = (successful_builds / total_builds * 100) if total_builds > 0 else 0
            
            # Stage success rates
            stage_rates = self.db.execute_query("""
                SELECT stage_name,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successes,
                       COUNT(*) as total
                FROM build_stages 
                WHERE start_time >= %s
                GROUP BY stage_name
                ORDER BY stage_name
            """, (cutoff_date,), fetch=True)
            
            stage_success_rates = []
            for stage in stage_rates:
                success_rate = (stage['successes'] / stage['total'] * 100) if stage['total'] > 0 else 0
                stage_success_rates.append({
                    'stage_name': stage['stage_name'],
                    'success_rate': round(success_rate, 1),
                    'successes': stage['successes'],
                    'total_attempts': stage['total']
                })
            
            # Find most/least reliable stages
            if stage_success_rates:
                most_reliable = max(stage_success_rates, key=lambda x: x['success_rate'])
                least_reliable = min(stage_success_rates, key=lambda x: x['success_rate'])
            else:
                most_reliable = least_reliable = None
            
            return {
                'overall_success_rate': round(overall_success_rate, 1),
                'total_builds': total_builds,
                'successful_builds': successful_builds,
                'stage_success_rates': stage_success_rates,
                'most_reliable_stage': most_reliable,
                'least_reliable_stage': least_reliable
            }
            
        except Exception as e:
            return {'error': f"Success rate calculation failed: {str(e)}"}
    
    def detect_new_patterns(self, days: int = 30, min_occurrences: int = 3) -> Dict:
        """Use simple ML to detect new failure patterns automatically"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get all error content from recent builds
            error_content = self.db.execute_query("""
                SELECT bd.content FROM build_documents bd
                JOIN builds b ON bd.build_id = b.build_id
                WHERE b.status IN ('failed', 'cancelled') 
                AND b.start_time >= %s
                AND bd.document_type IN ('error', 'log')
                AND (bd.content LIKE '%error%' OR bd.content LIKE '%failed%')
            """, (cutoff_date,), fetch=True)
            
            if not error_content:
                return {'new_patterns': [], 'summary': 'No error content found for analysis'}
            
            # Extract error lines and count occurrences
            error_lines = []
            for doc in error_content:
                lines = doc['content'].split('\n')
                for line in lines:
                    line = line.strip()
                    if any(keyword in line.lower() for keyword in ['error', 'failed', 'cannot', 'unable']):
                        # Clean up the line (remove timestamps, paths, etc.)
                        cleaned_line = re.sub(r'\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2}', '', line)
                        cleaned_line = re.sub(r'/[^\s]*/', '/<path>/', cleaned_line)
                        cleaned_line = re.sub(r'\d+', '<number>', cleaned_line)
                        if len(cleaned_line.strip()) > 20:  # Ignore very short lines
                            error_lines.append(cleaned_line.strip())
            
            # Count occurrences
            error_counter = Counter(error_lines)
            
            # Find patterns that occur frequently but aren't in existing patterns
            new_patterns = []
            existing_pattern_text = ' '.join([p.pattern.pattern for p in self.fault_patterns])
            
            for error_text, count in error_counter.most_common(20):
                if count >= min_occurrences:
                    # Check if this error is already covered by existing patterns
                    is_covered = False
                    for pattern in self.fault_patterns:
                        if pattern.pattern.search(error_text):
                            is_covered = True
                            break
                    
                    if not is_covered:
                        # Suggest a new pattern
                        pattern_name = self._generate_pattern_name(error_text)
                        new_patterns.append({
                            'suggested_name': pattern_name,
                            'error_text': error_text,
                            'occurrences': count,
                            'suggested_pattern': self._generate_regex_pattern(error_text),
                            'suggested_severity': self._suggest_severity(error_text)
                        })
            
            return {
                'new_patterns': new_patterns[:10],  # Top 10 suggestions
                'total_analyzed_lines': len(error_lines),
                'summary': f"Found {len(new_patterns)} potential new patterns from {len(error_lines)} error lines"
            }
            
        except Exception as e:
            return {'error': f"Pattern detection failed: {str(e)}", 'new_patterns': []}
    
    def _generate_pattern_name(self, error_text: str) -> str:
        """Generate a descriptive name for a new pattern"""
        # Extract key words from error text
        key_words = re.findall(r'\b[a-zA-Z]{4,}\b', error_text.lower())
        common_words = {'error', 'failed', 'cannot', 'unable', 'missing', 'not', 'found'}
        relevant_words = [w for w in key_words if w not in common_words][:3]
        
        if relevant_words:
            return ' '.join(word.title() for word in relevant_words) + ' Issue'
        else:
            return 'Unknown Error Pattern'
    
    def _generate_regex_pattern(self, error_text: str) -> str:
        """Generate a regex pattern from error text"""
        # Escape special regex characters and make it more general
        escaped = re.escape(error_text)
        # Replace <number> and <path> placeholders with regex
        pattern = escaped.replace(r'\<number\>', r'\d+')
        pattern = pattern.replace(r'\<path\>', r'[^\s]*')
        return pattern
    
    def _suggest_severity(self, error_text: str) -> str:
        """Suggest severity based on error text content"""
        text_lower = error_text.lower()
        
        if any(word in text_lower for word in ['permission', 'denied', 'space', 'disk', 'fatal']):
            return 'Critical'
        elif any(word in text_lower for word in ['compilation', 'linker', 'configure']):
            return 'High'
        elif any(word in text_lower for word in ['make', 'build', 'target']):
            return 'Medium'
        else:
            return 'Low'
    
    def export_patterns(self, filename: str = None) -> str:
        """Export patterns as JSON for sharing"""
        if not filename:
            filename = f"lfs_fault_patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        patterns_data = []
        for pattern in self.fault_patterns:
            patterns_data.append({
                'name': pattern.name,
                'pattern': pattern.pattern.pattern,
                'severity': pattern.severity,
                'description': pattern.description,
                'solution': pattern.solution,
                'auto_fix_command': pattern.auto_fix_command
            })
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'version': '1.0',
            'patterns': patterns_data
        }
        
        try:
            patterns_dir = os.path.join(os.path.dirname(__file__), 'patterns')
            os.makedirs(patterns_dir, exist_ok=True)
            filepath = os.path.join(patterns_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return filepath
        except Exception as e:
            return f"Export failed: {str(e)}"
    
    def import_patterns(self, filepath: str) -> Dict:
        """Import community-contributed patterns"""
        try:
            with open(filepath, 'r') as f:
                import_data = json.load(f)
            
            imported_count = 0
            skipped_count = 0
            
            for pattern_data in import_data.get('patterns', []):
                # Check if pattern already exists
                existing_names = [p.name for p in self.fault_patterns]
                if pattern_data['name'] not in existing_names:
                    new_pattern = FaultPattern(
                        name=pattern_data['name'],
                        pattern=pattern_data['pattern'],
                        severity=pattern_data['severity'],
                        description=pattern_data['description'],
                        solution=pattern_data['solution'],
                        auto_fix_command=pattern_data.get('auto_fix_command')
                    )
                    self.fault_patterns.append(new_pattern)
                    imported_count += 1
                else:
                    skipped_count += 1
            
            return {
                'success': True,
                'imported_count': imported_count,
                'skipped_count': skipped_count,
                'message': f"Imported {imported_count} new patterns, skipped {skipped_count} existing ones"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Import failed: {str(e)}"
            }
    
    def get_advanced_insights(self, build_id: str = None, days: int = 30) -> Dict:
        """Get comprehensive insights combining all analysis modules"""
        try:
            insights = {
                'analysis_time': datetime.now().isoformat(),
                'analysis_scope': f'Last {days} days' if not build_id else f'Build {build_id}'
            }
            
            if build_id:
                # Build-specific analysis
                if self.predictive_analyzer:
                    insights['risk_analysis'] = self.predictive_analyzer.analyze_build_risk(build_id)
                    insights['early_warnings'] = self.predictive_analyzer.get_early_warning_indicators(build_id)
                
                if self.root_cause_analyzer:
                    insights['root_cause'] = self.root_cause_analyzer.analyze_failure_root_cause(build_id)
                
                if self.performance_analyzer:
                    insights['performance_score'] = self.performance_analyzer.get_build_performance_score(build_id)
                
                if self.guidance_engine:
                    insights['guidance_effectiveness'] = self.guidance_engine.get_learning_insights(30)
            else:
                # System-wide analysis
                insights['comprehensive_analysis'] = self.analyze_comprehensive(days)
                
                if self.performance_analyzer:
                    insights['performance_correlation'] = self.performance_analyzer.analyze_performance_correlation(days)
                
                if self.predictive_analyzer:
                    insights['build_prediction'] = self.predictive_analyzer.predict_build_success_probability({})
                
                if self.guidance_engine:
                    insights['guidance_effectiveness'] = self.guidance_engine.get_learning_insights(days)
            
            return insights
            
        except Exception as e:
            return {'error': f'Advanced insights failed: {str(e)}'}
    
    def get_system_health_report(self) -> Dict:
        """Generate comprehensive system health report"""
        try:
            health_report = {
                'report_time': datetime.now().isoformat(),
                'overall_health': 'unknown',
                'health_score': 0,
                'recommendations': []
            }
            
            # Get recent build statistics
            recent_builds = self.db.execute_query("""
                SELECT status, COUNT(*) as count 
                FROM builds 
                WHERE start_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY status
            """, fetch=True)
            
            total_builds = sum(b['count'] for b in recent_builds)
            successful_builds = sum(b['count'] for b in recent_builds if b['status'] == 'completed')
            
            if total_builds > 0:
                success_rate = (successful_builds / total_builds) * 100
                health_report['success_rate'] = round(success_rate, 1)
                health_report['total_builds_7d'] = total_builds
                
                # Determine health score
                if success_rate >= 90:
                    health_report['overall_health'] = 'excellent'
                    health_report['health_score'] = 95
                elif success_rate >= 75:
                    health_report['overall_health'] = 'good'
                    health_report['health_score'] = 80
                elif success_rate >= 50:
                    health_report['overall_health'] = 'fair'
                    health_report['health_score'] = 60
                else:
                    health_report['overall_health'] = 'poor'
                    health_report['health_score'] = 30
                
                # Generate recommendations
                if success_rate < 75:
                    health_report['recommendations'].append('Investigate recent build failures to improve success rate')
                if total_builds < 3:
                    health_report['recommendations'].append('Consider running more builds to establish baseline performance')
            
            # Add performance insights if available
            if self.performance_analyzer:
                perf_analysis = self.performance_analyzer.analyze_performance_correlation(7)
                if 'performance_insights' in perf_analysis:
                    health_report['performance_insights'] = perf_analysis['performance_insights']
            
            # Add predictive insights if available
            if self.predictive_analyzer:
                prediction = self.predictive_analyzer.predict_build_success_probability({})
                if 'success_probability' in prediction:
                    health_report['next_build_prediction'] = prediction
            
            return health_report
            
        except Exception as e:
            return {'error': f'Health report generation failed: {str(e)}'}
    
    def _analyze_content(self, content: str, build_id: str, build_time: datetime, failed_stages: List[str] = None):
        """Analyze content for fault patterns with stage context"""
        for pattern in self.fault_patterns:
            if pattern.pattern.search(content):
                pattern.count += 1
                pattern.recent_builds.append({
                    'build_id': build_id,
                    'time': build_time
                })
                
                # Track stage occurrences
                if failed_stages:
                    for stage in failed_stages:
                        pattern.stage_occurrences[stage] += 1
    
    def _severity_weight(self, severity: str) -> int:
        """Convert severity to numeric weight for sorting"""
        weights = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}
        return weights.get(severity, 0)
    
    def _pattern_to_dict(self, pattern: FaultPattern) -> Dict:
        """Convert pattern to dictionary for display"""
        return {
            'name': pattern.name,
            'severity': pattern.severity,
            'count': pattern.count,
            'description': pattern.description,
            'solution': pattern.solution,
            'auto_fix_command': pattern.auto_fix_command,
            'recent_builds': pattern.recent_builds[-5:],  # Last 5 occurrences
            'stage_occurrences': dict(pattern.stage_occurrences),
            'most_common_stage': max(pattern.stage_occurrences.items(), key=lambda x: x[1])[0] if pattern.stage_occurrences else None
        }
    
    def _generate_recommendations(self, patterns: List[FaultPattern]) -> List[str]:
        """Generate actionable recommendations based on patterns"""
        recommendations = []
        
        if not patterns:
            recommendations.append("✅ No common failure patterns detected in recent builds")
            return recommendations
        
        # Critical issues first
        critical_patterns = [p for p in patterns if p.severity == 'Critical']
        if critical_patterns:
            recommendations.append("🚨 CRITICAL ISSUES DETECTED:")
            for pattern in critical_patterns[:3]:  # Top 3 critical
                recommendations.append(f"   • {pattern.name} ({pattern.count} occurrences): {pattern.solution}")
        
        # High severity issues
        high_patterns = [p for p in patterns if p.severity == 'High']
        if high_patterns:
            recommendations.append("⚠️  HIGH PRIORITY ISSUES:")
            for pattern in high_patterns[:3]:  # Top 3 high
                recommendations.append(f"   • {pattern.name} ({pattern.count} occurrences): {pattern.solution}")
        
        # General recommendations based on most common issues
        most_common = patterns[0] if patterns else None
        if most_common:
            if most_common.count >= 5:
                recommendations.append(f"📊 Most frequent issue: {most_common.name} - Consider addressing this systematically")
        
        # System-level recommendations
        permission_issues = sum(1 for p in patterns if 'permission' in p.name.lower())
        if permission_issues:
            recommendations.append("🔧 Run 'Setup LFS Permissions' from Build Actions menu to resolve permission issues")
        
        space_issues = sum(1 for p in patterns if 'space' in p.name.lower() or 'disk' in p.name.lower())
        if space_issues:
            recommendations.append("💾 Consider using external storage via Settings for builds requiring more space")
        
        return recommendations