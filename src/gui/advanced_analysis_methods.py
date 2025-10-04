#!/usr/bin/env python3
"""
Advanced Analysis Methods for GUI
Additional formatting and handler methods for the enhanced fault analysis system
"""

from datetime import datetime

def format_performance_results(self, performance_analysis: dict) -> str:
    """Format performance analysis results for display"""
    if 'error' in performance_analysis:
        return f"❌ Performance Analysis Error: {performance_analysis['error']}"
    
    result_lines = []
    result_lines.append("⚡ PERFORMANCE CORRELATION ANALYSIS")
    result_lines.append("=" * 60)
    
    # Duration analysis
    if 'duration_analysis' in performance_analysis:
        duration = performance_analysis['duration_analysis']
        result_lines.append("⏱️ BUILD DURATION PATTERNS:")
        
        if 'successful_builds_stats' in duration:
            stats = duration['successful_builds_stats']
            result_lines.append(f"✅ Successful Builds: {stats.get('count', 0)} builds")
            result_lines.append(f"   Avg Duration: {stats.get('avg_duration', 0)} seconds")
            result_lines.append(f"   Range: {stats.get('min_duration', 0)}-{stats.get('max_duration', 0)} seconds")
        
        if 'failed_builds_stats' in duration:
            stats = duration['failed_builds_stats']
            result_lines.append(f"❌ Failed Builds: {stats.get('count', 0)} builds")
            result_lines.append(f"   Avg Duration: {stats.get('avg_duration', 0)} seconds")
        
        for finding in duration.get('correlation_findings', []):
            result_lines.append(f"🔍 {finding['finding']}")
        
        result_lines.append("")
    
    # Performance insights
    if 'performance_insights' in performance_analysis:
        result_lines.append("💡 PERFORMANCE INSIGHTS:")
        result_lines.append("-" * 60)
        for insight in performance_analysis['performance_insights']:
            result_lines.append(f"• {insight}")
        result_lines.append("")
    
    return "\n".join(result_lines)

def format_predictive_analysis_results(self) -> str:
    """Format predictive analysis results for recent builds"""
    try:
        # Get prediction for next build
        prediction = self.fault_analyzer.predict_build_success()
        
        result_lines = []
        result_lines.append("🔮 PREDICTIVE ANALYSIS")
        result_lines.append("=" * 60)
        
        if 'error' in prediction:
            result_lines.append(f"❌ Prediction Error: {prediction['error']}")
        else:
            success_prob = prediction.get('success_probability', 0)
            confidence = prediction.get('confidence', 'unknown')
            
            prob_icon = "🟢" if success_prob > 80 else "🟡" if success_prob > 60 else "🟠" if success_prob > 40 else "🔴"
            
            result_lines.append(f"{prob_icon} Next Build Success Probability: {success_prob}%")
            result_lines.append(f"📊 Confidence Level: {confidence.title()}")
            result_lines.append(f"💡 Recommendation: {prediction.get('recommendation', 'No recommendation')}")
            result_lines.append("")
            
            factors = prediction.get('factors', {})
            if factors:
                result_lines.append("📈 CONTRIBUTING FACTORS:")
                result_lines.append(f"   Recent Success Rate: {factors.get('recent_success_rate', 0)}%")
                result_lines.append(f"   System Health: {factors.get('system_health', 0)}%")
                result_lines.append(f"   Time Factors: {factors.get('time_factors', 0)}%")
        
        # Get early warnings for current build if available
        if self.current_build_id:
            warnings = self.fault_analyzer.get_early_warning_indicators(self.current_build_id)
            if 'warnings' in warnings and warnings['warnings']:
                result_lines.append("")
                result_lines.append("⚠️ EARLY WARNING INDICATORS:")
                result_lines.append("-" * 60)
                for warning in warnings['warnings']:
                    level_icon = "🚨" if warning['level'] == 'critical' else "⚠️"
                    result_lines.append(f"{level_icon} {warning['message']}")
                    result_lines.append(f"   Action: {warning['action']}")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        return f"❌ Predictive analysis failed: {str(e)}"

def format_root_cause_analysis_results(self) -> str:
    """Format root cause analysis results for recent failures"""
    try:
        result_lines = []
        result_lines.append("🔍 ROOT CAUSE ANALYSIS")
        result_lines.append("=" * 60)
        
        # Get recent failed builds
        failed_builds = self.db.execute_query("""
            SELECT build_id, start_time FROM builds 
            WHERE status IN ('failed', 'cancelled') 
            AND start_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY start_time DESC 
            LIMIT 3
        """, fetch=True)
        
        if not failed_builds:
            result_lines.append("✅ No recent build failures to analyze")
            return "\n".join(result_lines)
        
        result_lines.append(f"📊 Analyzing {len(failed_builds)} recent failures:")
        result_lines.append("")
        
        for i, build in enumerate(failed_builds, 1):
            build_id = build['build_id']
            root_cause = self.fault_analyzer.analyze_root_cause(build_id)
            
            result_lines.append(f"{i}. Build {build_id[-8:]}... ({build['start_time'].strftime('%m/%d %H:%M')})")
            
            if 'error' in root_cause:
                result_lines.append(f"   ❌ Analysis failed: {root_cause['error']}")
            else:
                primary_cause = root_cause.get('root_cause', {})
                category = primary_cause.get('category', 'unknown')
                description = primary_cause.get('description', 'No description')
                confidence = primary_cause.get('confidence', 'low')
                
                category_icon = {
                    'dependency_failure': '🔗',
                    'environmental': '🌍',
                    'configuration_difference': '⚙️',
                    'unknown': '❓'
                }.get(category, '❓')
                
                result_lines.append(f"   {category_icon} Category: {category.replace('_', ' ').title()}")
                result_lines.append(f"   📝 Cause: {description}")
                result_lines.append(f"   🎯 Confidence: {confidence.title()}")
                
                # Show top recommendation
                recommendations = root_cause.get('recommendations', [])
                if recommendations:
                    result_lines.append(f"   💡 Fix: {recommendations[0]}")
            
            result_lines.append("")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        return f"❌ Root cause analysis failed: {str(e)}"

def generate_health_report(self):
    """Generate system health report"""
    try:
        health_report = self.fault_analyzer.get_system_health_report()
        
        if 'error' in health_report:
            self.health_results.setPlainText(f"❌ Health Report Error: {health_report['error']}")
            return
        
        result_lines = []
        result_lines.append("🏥 SYSTEM HEALTH REPORT")
        result_lines.append("=" * 60)
        result_lines.append(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        result_lines.append("")
        
        # Overall health
        health = health_report.get('overall_health', 'unknown')
        score = health_report.get('health_score', 0)
        
        health_icon = {
            'excellent': '🟢',
            'good': '🟡',
            'fair': '🟠',
            'poor': '🔴'
        }.get(health, '⚪')
        
        result_lines.append(f"{health_icon} Overall Health: {health.upper()} ({score}/100)")
        
        if 'success_rate' in health_report:
            result_lines.append(f"✅ Success Rate (7 days): {health_report['success_rate']}%")
            result_lines.append(f"📊 Total Builds: {health_report.get('total_builds_7d', 0)}")
        
        result_lines.append("")
        
        # Recommendations
        recommendations = health_report.get('recommendations', [])
        if recommendations:
            result_lines.append("💡 HEALTH RECOMMENDATIONS:")
            result_lines.append("-" * 60)
            for rec in recommendations:
                result_lines.append(f"• {rec}")
            result_lines.append("")
        
        # Performance insights
        if 'performance_insights' in health_report:
            result_lines.append("⚡ PERFORMANCE INSIGHTS:")
            result_lines.append("-" * 60)
            for insight in health_report['performance_insights']:
                result_lines.append(f"• {insight}")
            result_lines.append("")
        
        # Next build prediction
        if 'next_build_prediction' in health_report:
            prediction = health_report['next_build_prediction']
            prob = prediction.get('success_probability', 0)
            result_lines.append(f"🔮 Next Build Prediction: {prob}% success probability")
        
        self.health_results.setPlainText("\n".join(result_lines))
        
    except Exception as e:
        self.health_results.setPlainText(f"❌ Health report generation failed: {str(e)}")

def predict_next_build(self):
    """Predict success probability for next build"""
    try:
        from PyQt5.QtWidgets import QMessageBox
        
        prediction = self.fault_analyzer.predict_build_success()
        
        if 'error' in prediction:
            QMessageBox.warning(self, "Prediction Error", prediction['error'])
            return
        
        success_prob = prediction.get('success_probability', 0)
        confidence = prediction.get('confidence', 'unknown')
        recommendation = prediction.get('recommendation', 'No recommendation')
        
        prob_icon = "🟢" if success_prob > 80 else "🟡" if success_prob > 60 else "🟠" if success_prob > 40 else "🔴"
        
        message = f"{prob_icon} Build Success Prediction\n\n"
        message += f"Success Probability: {success_prob}%\n"
        message += f"Confidence Level: {confidence.title()}\n\n"
        message += f"Recommendation: {recommendation}"
        
        factors = prediction.get('factors', {})
        if factors:
            message += "\n\nContributing Factors:\n"
            message += f"• Recent Success Rate: {factors.get('recent_success_rate', 0)}%\n"
            message += f"• System Health: {factors.get('system_health', 0)}%\n"
            message += f"• Time Factors: {factors.get('time_factors', 0)}%"
        
        QMessageBox.information(self, "Build Prediction", message)
        
    except Exception as e:
        QMessageBox.critical(self, "Prediction Error", f"Failed to predict build success: {str(e)}")