from datetime import datetime, timedelta
import json
import mysql.connector
from typing import Dict, List, Optional


class BuildAdvisor:
    """Intelligent build advisor that analyzes database history to provide recommendations"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        # Get connection from database manager
        if hasattr(db_manager, 'connection'):
            self.connection = db_manager.connection
        elif hasattr(db_manager, 'get_connection'):
            self.connection = db_manager.get_connection()
        else:
            # Create direct connection for build advisor
            import mysql.connector
            self.connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='G`/C#Pi"5uqHNrZ@r<pT',
                database='lfs_builds'
            )
    
    def analyze_build_history(self, limit=50):
        """Analyze recent build history for patterns and recommendations"""
        try:
            # Get recent builds with detailed information
            builds = self.db.execute_query("""
                SELECT b.build_id, b.config_name, b.status, b.start_time, b.end_time,
                       b.duration_seconds, COUNT(bs.stage_name) as total_stages,
                       SUM(CASE WHEN bs.status = 'completed' THEN 1 ELSE 0 END) as completed_stages
                FROM builds b
                LEFT JOIN build_stages bs ON b.build_id = bs.build_id
                WHERE b.start_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY b.build_id
                ORDER BY b.start_time DESC
                LIMIT %s
            """, (limit,), fetch=True)
            
            if not builds:
                return self._generate_first_build_advice()
            
            # Analyze patterns
            analysis = {
                'total_builds': len(builds),
                'successful_builds': len([b for b in builds if b['status'] == 'success']),
                'failed_builds': len([b for b in builds if b['status'] == 'failed']),
                'cancelled_builds': len([b for b in builds if b['status'] == 'cancelled']),
                'success_rate': 0,
                'common_failures': [],
                'recommendations': [],
                'next_build_advice': []
            }
            
            if analysis['total_builds'] > 0:
                analysis['success_rate'] = round((analysis['successful_builds'] / analysis['total_builds']) * 100, 1)
            
            # Analyze failure patterns
            analysis['common_failures'] = self._analyze_failure_patterns(builds)
            
            # Generate recommendations
            analysis['recommendations'] = self._generate_recommendations(builds, analysis)
            
            # Generate next build advice
            analysis['next_build_advice'] = self._generate_next_build_advice(builds, analysis)
            
            return analysis
            
        except Exception as e:
            return {'error': f"Failed to analyze build history: {str(e)}"}
    
    def _analyze_failure_patterns(self, builds):
        """Analyze common failure patterns from build history"""
        failures = []
        
        try:
            # Get failed builds
            failed_builds = [b for b in builds if b['status'] == 'failed']
            
            for build in failed_builds:
                # Get failed stages for this build
                failed_stages = self.db.execute_query("""
                    SELECT stage_name, error_message, stage_order
                    FROM build_stages 
                    WHERE build_id = %s AND status = 'failed'
                    ORDER BY stage_order
                """, (build['build_id'],), fetch=True)
                
                for stage in failed_stages:
                    failures.append({
                        'build_id': build['build_id'],
                        'stage': stage['stage_name'],
                        'error': stage.get('error_message', 'Unknown error'),
                        'stage_order': stage['stage_order']
                    })
            
            # Count common failure stages
            stage_failures = {}
            for failure in failures:
                stage = failure['stage']
                if stage not in stage_failures:
                    stage_failures[stage] = {'count': 0, 'errors': []}
                stage_failures[stage]['count'] += 1
                if failure['error'] and failure['error'] not in stage_failures[stage]['errors']:
                    stage_failures[stage]['errors'].append(failure['error'])
            
            # Sort by frequency
            common_failures = []
            for stage, data in sorted(stage_failures.items(), key=lambda x: x[1]['count'], reverse=True):
                common_failures.append({
                    'stage': stage,
                    'failure_count': data['count'],
                    'common_errors': data['errors'][:3]  # Top 3 errors
                })
            
            return common_failures[:5]  # Top 5 failure patterns
            
        except Exception as e:
            return [{'stage': 'analysis_error', 'failure_count': 0, 'common_errors': [str(e)]}]
    
    def _generate_recommendations(self, builds, analysis):
        """Generate recommendations based on build history analysis"""
        recommendations = []
        
        # Success rate recommendations
        if analysis['success_rate'] < 50:
            recommendations.append({
                'priority': 'High',
                'category': 'Success Rate',
                'issue': f"Low success rate ({analysis['success_rate']}%)",
                'recommendation': 'Review system requirements and ensure all dependencies are installed',
                'action': 'Run system preparation checks before next build'
            })
        elif analysis['success_rate'] < 80:
            recommendations.append({
                'priority': 'Medium',
                'category': 'Success Rate',
                'issue': f"Moderate success rate ({analysis['success_rate']}%)",
                'recommendation': 'Identify and address common failure patterns',
                'action': 'Review failed build logs for recurring issues'
            })
        
        # Common failure recommendations
        for failure in analysis['common_failures'][:3]:
            if failure['failure_count'] >= 2:
                recommendations.append({
                    'priority': 'High',
                    'category': 'Stage Failure',
                    'issue': f"Stage '{failure['stage']}' fails frequently ({failure['failure_count']} times)",
                    'recommendation': self._get_stage_specific_advice(failure['stage']),
                    'action': f"Focus on resolving {failure['stage']} issues before next build"
                })
        
        # Build frequency recommendations
        recent_builds = [b for b in builds if b['start_time'] and 
                        (datetime.now() - b['start_time']).days <= 7]
        
        if len(recent_builds) > 10:
            recommendations.append({
                'priority': 'Medium',
                'category': 'Build Frequency',
                'issue': f"High build frequency ({len(recent_builds)} builds in 7 days)",
                'recommendation': 'Consider using build templates and pre-validation to reduce failed attempts',
                'action': 'Implement build validation checks before starting builds'
            })
        
        return recommendations
    
    def _generate_next_build_advice(self, builds, analysis):
        """Generate specific advice for the next build attempt"""
        advice = []
        
        # Get the most recent build
        if builds:
            last_build = builds[0]
            
            if last_build['status'] == 'failed':
                # Get the failed stage
                failed_stage = self.db.execute_query("""
                    SELECT stage_name, error_message, stage_order
                    FROM build_stages 
                    WHERE build_id = %s AND status = 'failed'
                    ORDER BY stage_order DESC
                    LIMIT 1
                """, (last_build['build_id'],), fetch=True)
                
                if failed_stage:
                    stage = failed_stage[0]
                    advice.append({
                        'type': 'Fix Required',
                        'priority': 'Critical',
                        'message': f"Last build failed at stage '{stage['stage_name']}'",
                        'action': self._get_stage_specific_fix(stage['stage_name'], stage.get('error_message')),
                        'estimated_time': '15-30 minutes'
                    })
            
            elif last_build['status'] == 'success':
                advice.append({
                    'type': 'Success Pattern',
                    'priority': 'Info',
                    'message': f"Last build succeeded with configuration '{last_build['config_name']}'",
                    'action': 'Consider using the same configuration for consistency',
                    'estimated_time': 'Same as previous build'
                })
        
        # System preparation advice
        advice.append({
            'type': 'Preparation',
            'priority': 'High',
            'message': 'Ensure system is properly prepared',
            'action': 'Run compliance check and verify LFS directory permissions',
            'estimated_time': '5-10 minutes'
        })
        
        # Resource advice
        advice.append({
            'type': 'Resources',
            'priority': 'Medium',
            'message': 'Verify system resources',
            'action': 'Ensure at least 15GB free space and 4GB RAM available',
            'estimated_time': '2-3 minutes'
        })
        
        return advice
    
    def _get_stage_specific_advice(self, stage_name):
        """Get specific advice for common stage failures"""
        advice_map = {
            'prepare_host': 'Verify host system has all required development tools installed',
            'download_sources': 'Check network connectivity and mirror availability',
            'build_toolchain': 'Ensure sufficient disk space (5+ GB) and memory (2+ GB)',
            'build_temp_system': 'Verify toolchain was built successfully and PATH is correct',
            'enter_chroot': 'Check LFS directory permissions and mount points',
            'build_final_system': 'Ensure temporary system is complete and chroot environment is proper',
            'configure_system': 'Verify all required packages are installed',
            'build_kernel': 'Check kernel configuration and ensure source is available',
            'install_bootloader': 'Verify boot partition is mounted and accessible'
        }
        return advice_map.get(stage_name, f'Review {stage_name} documentation and logs')
    
    def _get_stage_specific_fix(self, stage_name, error_message):
        """Get specific fix recommendations for stage failures"""
        if 'permission' in (error_message or '').lower():
            return 'Run "Setup LFS Permissions" from Build Actions menu'
        elif 'space' in (error_message or '').lower() or 'disk' in (error_message or '').lower():
            return 'Free up disk space or use external storage'
        elif 'network' in (error_message or '').lower() or 'download' in (error_message or '').lower():
            return 'Check network connectivity and try different mirrors'
        else:
            return self._get_stage_specific_advice(stage_name)
    
    def _generate_first_build_advice(self):
        """Generate advice for first-time builders"""
        return {
            'total_builds': 0,
            'successful_builds': 0,
            'failed_builds': 0,
            'cancelled_builds': 0,
            'success_rate': 0,
            'common_failures': [],
            'recommendations': [
                {
                    'priority': 'Critical',
                    'category': 'First Build',
                    'issue': 'No previous build history',
                    'recommendation': 'Follow the complete LFS preparation checklist',
                    'action': 'Run system compliance check and setup LFS permissions'
                }
            ],
            'next_build_advice': [
                {
                    'type': 'First Build',
                    'priority': 'Critical',
                    'message': 'This is your first LFS build',
                    'action': 'Start with the Build Wizard and use a tested template',
                    'estimated_time': '4-8 hours for complete build'
                },
                {
                    'type': 'Preparation',
                    'priority': 'High',
                    'message': 'System preparation is crucial',
                    'action': 'Run compliance check, setup permissions, and verify 15+ GB free space',
                    'estimated_time': '15-20 minutes'
                }
            ]
        }
    
    def generate_build_report(self, build_id):
        """Generate comprehensive build report"""
        try:
            # Get build details
            build = self.db.execute_query("""
                SELECT * FROM builds WHERE build_id = %s
            """, (build_id,), fetch=True)
            
            if not build:
                return {'error': f'Build {build_id} not found'}
            
            build = build[0]
            
            # Get build stages
            stages = self.db.execute_query("""
                SELECT * FROM build_stages 
                WHERE build_id = %s 
                ORDER BY stage_order
            """, (build_id,), fetch=True)
            
            # Get build documents
            documents = self.db.execute_query("""
                SELECT document_type, title, LENGTH(content) as size, created_at
                FROM build_documents 
                WHERE build_id = %s 
                ORDER BY created_at
            """, (build_id,), fetch=True)
            
            # Generate analysis
            analysis = self.analyze_build_history()
            
            report = {
                'build_info': build,
                'stages': stages,
                'documents': documents,
                'analysis': analysis,
                'generated_at': datetime.now().isoformat(),
                'recommendations': self._generate_build_specific_recommendations(build, stages)
            }
            
            return report
            
        except Exception as e:
            return {'error': f"Failed to generate build report: {str(e)}"}
    
    def generate_build_advice(self, build_id: Optional[int] = None) -> Dict:
        """Generate comprehensive build advice based on database analysis"""
        try:
            analysis = self.analyze_build_history()
            
            advice = {
                'timestamp': datetime.now().isoformat(),
                'build_context': build_id,
                'analysis': analysis,
                'failure_patterns': analysis.get('common_failures', []),
                'recommendations': analysis.get('recommendations', []),
                'next_build_advice': analysis.get('next_build_advice', []),
                'success_metrics': {
                    'overall_success_rate': analysis.get('success_rate', 0),
                    'total_builds': analysis.get('total_builds', 0),
                    'successful_builds': analysis.get('successful_builds', 0)
                }
            }
            
            # Store comprehensive report in database
            self._store_comprehensive_report(advice, build_id)
            
            return advice
            
        except Exception as e:
            return {
                'error': f"Failed to generate build advice: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _store_comprehensive_report(self, advice: Dict, build_id: Optional[int] = None):
        """Store comprehensive report in database with full output preservation"""
        try:
            cursor = self.connection.cursor()
            
            # Generate comprehensive output text
            full_output = self._generate_full_report_text(advice)
            
            # Calculate report size
            report_size = len(full_output.encode('utf-8'))
            
            # Generate report title
            success_rate = advice.get('success_metrics', {}).get('overall_success_rate', 0)
            title = f"Build Analysis Report - {success_rate:.1f}% Success Rate - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Insert comprehensive report
            insert_query = """
                INSERT INTO next_build_reports 
                (build_id, report_title, total_builds_analyzed, success_rate, avg_build_duration,
                 full_analysis_output, failure_patterns_json, recommendations_json, 
                 next_build_advice_json, report_size_bytes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                build_id,
                title,
                advice.get('analysis', {}).get('total_builds', 0),
                success_rate,
                advice.get('analysis', {}).get('avg_duration_minutes', 0) if 'avg_duration_minutes' in advice.get('analysis', {}) else 0,
                full_output,
                json.dumps(advice.get('failure_patterns', {})),
                json.dumps(advice.get('recommendations', {})),
                json.dumps(advice.get('next_build_advice', {})),
                report_size
            ))
            
            self.connection.commit()
            cursor.close()
            
        except Exception as e:
            print(f"Failed to store comprehensive report: {e}")
    
    def _generate_full_report_text(self, advice: Dict) -> str:
        """Generate comprehensive report text preserving all analysis output"""
        lines = []
        lines.append("=" * 80)
        lines.append("COMPREHENSIVE BUILD ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {advice.get('timestamp', 'Unknown')}")
        lines.append(f"Build Context: {advice.get('build_context', 'All Builds')}")
        lines.append("")
        
        # Analysis Summary
        analysis = advice.get('analysis', {})
        lines.append("ANALYSIS SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Builds Analyzed: {analysis.get('total_builds', 0)}")
        lines.append(f"Successful Builds: {analysis.get('successful_builds', 0)}")
        lines.append(f"Failed Builds: {analysis.get('failed_builds', 0)}")
        lines.append(f"Cancelled Builds: {analysis.get('cancelled_builds', 0)}")
        lines.append("")
        
        # Success Metrics
        metrics = advice.get('success_metrics', {})
        lines.append("SUCCESS METRICS")
        lines.append("-" * 40)
        lines.append(f"Overall Success Rate: {metrics.get('overall_success_rate', 0):.2f}%")
        lines.append(f"Total Builds: {metrics.get('total_builds', 0)}")
        lines.append(f"Successful Builds: {metrics.get('successful_builds', 0)}")
        lines.append("")
        
        # Failure Patterns
        patterns = advice.get('failure_patterns', [])
        lines.append("FAILURE PATTERNS")
        lines.append("-" * 40)
        if patterns:
            for pattern in patterns:
                lines.append(f"Stage: {pattern.get('stage', 'Unknown')} - {pattern.get('failure_count', 0)} failures")
                for error in pattern.get('common_errors', [])[:2]:
                    lines.append(f"  Error: {error}")
                lines.append("")
        else:
            lines.append("No failure patterns detected.")
            lines.append("")
        
        # Recommendations
        recommendations = advice.get('recommendations', [])
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 40)
        if recommendations:
            for rec in recommendations:
                lines.append(f"[{rec.get('priority', 'Medium')}] {rec.get('category', 'General')}")
                lines.append(f"  Issue: {rec.get('issue', 'Unknown')}")
                lines.append(f"  Recommendation: {rec.get('recommendation', 'No recommendation')}")
                lines.append(f"  Action: {rec.get('action', 'No action specified')}")
                lines.append("")
        else:
            lines.append("No specific recommendations at this time.")
            lines.append("")
        
        # Next Build Advice
        next_advice = advice.get('next_build_advice', [])
        lines.append("NEXT BUILD ADVICE")
        lines.append("-" * 40)
        if next_advice:
            for advice_item in next_advice:
                lines.append(f"[{advice_item.get('priority', 'Medium')}] {advice_item.get('type', 'General')}")
                lines.append(f"  Message: {advice_item.get('message', 'No message')}")
                lines.append(f"  Action: {advice_item.get('action', 'No action specified')}")
                lines.append(f"  Estimated Time: {advice_item.get('estimated_time', 'Unknown')}")
                lines.append("")
        else:
            lines.append("No specific next build advice available.")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def get_all_reports(self) -> List[Dict]:
        """Get all stored next build reports"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, build_id, report_title, generated_at, 
                       total_builds_analyzed, success_rate, avg_build_duration,
                       report_size_bytes, export_count, last_accessed
                FROM next_build_reports 
                ORDER BY generated_at DESC
            """)
            
            reports = cursor.fetchall()
            cursor.close()
            return reports
            
        except Exception as e:
            print(f"Failed to get reports: {e}")
            return []
    
    def get_report_details(self, report_id: int) -> Optional[Dict]:
        """Get full report details including analysis output"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM next_build_reports WHERE id = %s
            """, (report_id,))
            
            report = cursor.fetchone()
            cursor.close()
            
            if report:
                # Log access
                self._log_report_access(report_id, 'view')
                
            return report
            
        except Exception as e:
            print(f"Failed to get report details: {e}")
            return None
    
    def _log_report_access(self, report_id: int, access_type: str):
        """Log report access for tracking"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO report_access_log (report_id, access_type, user_context)
                VALUES (%s, %s, %s)
            """, (report_id, access_type, 'GUI_User'))
            
            self.connection.commit()
            cursor.close()
            
        except Exception as e:
            print(f"Failed to log report access: {e}")
    
    def delete_report(self, report_id: int) -> bool:
        """Delete a report from database"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM next_build_reports WHERE id = %s", (report_id,))
            self.connection.commit()
            cursor.close()
            return True
            
        except Exception as e:
            print(f"Failed to delete report: {e}")
            return False
    
    def search_reports(self, search_term: str) -> List[Dict]:
        """Search reports by title or content"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, build_id, report_title, generated_at, 
                       total_builds_analyzed, success_rate, avg_build_duration,
                       report_size_bytes, export_count, last_accessed
                FROM next_build_reports 
                WHERE MATCH(full_analysis_output, report_title) AGAINST(%s IN NATURAL LANGUAGE MODE)
                ORDER BY generated_at DESC
            """, (search_term,))
            
            reports = cursor.fetchall()
            cursor.close()
            return reports
            
        except Exception as e:
            print(f"Failed to search reports: {e}")
            return []
    
    def _generate_build_specific_recommendations(self, build, stages):
        """Generate recommendations specific to this build"""
        recommendations = []
        
        if build['status'] == 'failed':
            failed_stages = [s for s in stages if s['status'] == 'failed']
            for stage in failed_stages:
                recommendations.append({
                    'type': 'Fix Required',
                    'stage': stage['stage_name'],
                    'issue': stage.get('error_message', 'Stage failed'),
                    'recommendation': self._get_stage_specific_fix(stage['stage_name'], stage.get('error_message'))
                })
        
        elif build['status'] == 'success':
            recommendations.append({
                'type': 'Success',
                'stage': 'All',
                'issue': 'Build completed successfully',
                'recommendation': 'Configuration can be reused for future builds'
            })
        
        return recommendations