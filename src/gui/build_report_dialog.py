from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTextEdit, QPushButton, QTabWidget, QWidget, 
                            QTableWidget, QTableWidgetItem, QGroupBox, 
                            QMessageBox, QFileDialog, QApplication, QHeaderView)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
import json


class BuildReportDialog(QDialog):
    """Comprehensive build report dialog with analysis and recommendations"""
    
    def __init__(self, db_manager, build_id=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.build_id = build_id
        self.report_data = None
        
        self.setWindowTitle("Build Analysis & Recommendations")
        self.setModal(True)
        self.resize(1000, 700)
        
        self.setup_ui()
        self.load_report()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("📊 Build Analysis & Next Build Recommendations")
        header.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 10px; color: #2c3e50;")
        layout.addWidget(header)
        
        # Tabs
        tab_widget = QTabWidget()
        
        # Overview tab
        overview_tab = self.create_overview_tab()
        tab_widget.addTab(overview_tab, "📈 Overview")
        
        # Analysis tab
        analysis_tab = self.create_analysis_tab()
        tab_widget.addTab(analysis_tab, "🔍 Analysis")
        
        # Recommendations tab
        recommendations_tab = self.create_recommendations_tab()
        tab_widget.addTab(recommendations_tab, "💡 Recommendations")
        
        # Next Build tab
        next_build_tab = self.create_next_build_tab()
        tab_widget.addTab(next_build_tab, "🚀 Next Build")
        
        layout.addWidget(tab_widget)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Refresh Analysis")
        self.refresh_btn.clicked.connect(self.load_report)
        
        self.export_btn = QPushButton("📄 Export Report")
        self.export_btn.clicked.connect(self.export_report)
        
        self.copy_btn = QPushButton("📋 Copy to Clipboard")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        
        self.print_btn = QPushButton("🖨️ Print Report")
        self.print_btn.clicked.connect(self.print_report)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.copy_btn)
        button_layout.addWidget(self.print_btn)
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_overview_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Build summary
        self.summary_group = QGroupBox("Build Summary")
        summary_layout = QVBoxLayout()
        
        self.summary_text = QTextEdit()
        self.summary_text.setMaximumHeight(150)
        self.summary_text.setReadOnly(True)
        summary_layout.addWidget(self.summary_text)
        
        self.summary_group.setLayout(summary_layout)
        layout.addWidget(self.summary_group)
        
        # Success metrics
        metrics_group = QGroupBox("Success Metrics")
        metrics_layout = QVBoxLayout()
        
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(2)
        self.metrics_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.metrics_table.setMaximumHeight(200)
        
        metrics_layout.addWidget(self.metrics_table)
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)
        
        # Recent builds
        recent_group = QGroupBox("Recent Build History")
        recent_layout = QVBoxLayout()
        
        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(4)
        self.recent_table.setHorizontalHeaderLabels(["Build ID", "Status", "Duration", "Date"])
        self.recent_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        recent_layout.addWidget(self.recent_table)
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)
        
        return tab
    
    def create_analysis_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Failure patterns
        failures_group = QGroupBox("Common Failure Patterns")
        failures_layout = QVBoxLayout()
        
        self.failures_table = QTableWidget()
        self.failures_table.setColumnCount(3)
        self.failures_table.setHorizontalHeaderLabels(["Stage", "Failure Count", "Common Errors"])
        self.failures_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        failures_layout.addWidget(self.failures_table)
        failures_group.setLayout(failures_layout)
        layout.addWidget(failures_group)
        
        # Build stages analysis
        stages_group = QGroupBox("Build Stages Analysis")
        stages_layout = QVBoxLayout()
        
        self.stages_table = QTableWidget()
        self.stages_table.setColumnCount(4)
        self.stages_table.setHorizontalHeaderLabels(["Stage", "Status", "Duration", "Issues"])
        self.stages_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        stages_layout.addWidget(self.stages_table)
        stages_group.setLayout(stages_layout)
        layout.addWidget(stages_group)
        
        return tab
    
    def create_recommendations_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Recommendations table
        recommendations_group = QGroupBox("Recommendations for Improvement")
        recommendations_layout = QVBoxLayout()
        
        self.recommendations_table = QTableWidget()
        self.recommendations_table.setColumnCount(4)
        self.recommendations_table.setHorizontalHeaderLabels(["Priority", "Category", "Issue", "Recommendation"])
        self.recommendations_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        recommendations_layout.addWidget(self.recommendations_table)
        recommendations_group.setLayout(recommendations_layout)
        layout.addWidget(recommendations_group)
        
        # Detailed recommendations
        details_group = QGroupBox("Detailed Analysis")
        details_layout = QVBoxLayout()
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        details_layout.addWidget(self.recommendations_text)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        return tab
    
    def create_next_build_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Next build advice
        advice_group = QGroupBox("Next Build Preparation")
        advice_layout = QVBoxLayout()
        
        self.advice_table = QTableWidget()
        self.advice_table.setColumnCount(4)
        self.advice_table.setHorizontalHeaderLabels(["Priority", "Action Required", "Estimated Time", "Details"])
        self.advice_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        advice_layout.addWidget(self.advice_table)
        advice_group.setLayout(advice_layout)
        layout.addWidget(advice_group)
        
        # Action checklist
        checklist_group = QGroupBox("Pre-Build Checklist")
        checklist_layout = QVBoxLayout()
        
        self.checklist_text = QTextEdit()
        self.checklist_text.setReadOnly(True)
        checklist_layout.addWidget(self.checklist_text)
        
        checklist_group.setLayout(checklist_layout)
        layout.addWidget(checklist_group)
        
        return tab
    
    def load_report(self):
        """Load build analysis and recommendations using database and ML"""
        try:
            from ..analysis.build_advisor import BuildAdvisor
            advisor = BuildAdvisor(self.db)
            
            # Get comprehensive analysis with ML insights
            analysis = advisor.generate_build_advice(self.build_id)
            
            # Get actual build data from database
            builds = self.db.execute_query(
                "SELECT * FROM builds ORDER BY start_time DESC LIMIT 50",
                fetch=True
            ) or []
            
            # Get failure analysis from database
            failures = self.db.execute_query(
                "SELECT stage_name, COUNT(*) as failure_count, GROUP_CONCAT(output_log) as errors FROM build_stages WHERE status = 'failed' GROUP BY stage_name ORDER BY failure_count DESC",
                fetch=True
            ) or []
            
            # Get ML insights if available
            ml_insights = None
            try:
                from ..ml.ml_engine import MLEngine
                ml_engine = MLEngine(self.db)
                if ml_engine.is_enabled():
                    ml_insights = ml_engine.get_system_wide_insights()
            except:
                pass
            
            self.report_data = {
                'analysis': analysis.get('analysis', {}),
                'builds': builds,
                'failures': failures,
                'ml_insights': ml_insights,
                'recommendations': analysis.get('recommendations', []),
                'next_build_advice': analysis.get('next_build_advice', []),
                'generated_at': datetime.now().isoformat()
            }
            
            self.populate_ui()
            
        except Exception as e:
            QMessageBox.critical(self, "Report Error", f"Failed to generate report: {str(e)}")
    
    def populate_ui(self):
        """Populate UI with report data"""
        if not self.report_data or 'error' in self.report_data:
            error_msg = self.report_data.get('error', 'Unknown error') if self.report_data else 'No data'
            self.summary_text.setPlainText(f"Error generating report: {error_msg}")
            return
        
        analysis = self.report_data.get('analysis', {})
        
        # Populate overview
        self.populate_overview(analysis)
        
        # Populate analysis
        self.populate_analysis(analysis)
        
        # Populate recommendations
        self.populate_recommendations(analysis)
        
        # Populate next build advice
        self.populate_next_build_advice(analysis)
    
    def populate_overview(self, analysis):
        """Populate overview tab with actual database data"""
        builds = self.report_data.get('builds', [])
        ml_insights = self.report_data.get('ml_insights', {})
        
        total = len(builds)
        successful = len([b for b in builds if b.get('status') == 'success'])
        failed = len([b for b in builds if b.get('status') == 'failed'])
        cancelled = len([b for b in builds if b.get('status') == 'cancelled'])
        success_rate = (successful / total * 100) if total > 0 else 0
        
        # Add ML insights to summary
        ml_status = "ML Analysis: Enabled" if ml_insights else "ML Analysis: Not Available"
        failure_risk = ""
        if ml_insights and ml_insights.get('insights', {}).get('failure_prediction'):
            risk = ml_insights['insights']['failure_prediction'].get('risk_score', 0) * 100
            failure_risk = f"\nNext Build Failure Risk: {risk:.1f}%"
        
        summary = f"""Build Analysis Summary (Database-Driven)
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{ml_status}{failure_risk}

Total Builds: {total}
Successful: {successful}
Failed: {failed}
Cancelled: {cancelled}
Success Rate: {success_rate:.1f}%

Analysis based on actual build history from database with ML insights."""
        
        self.summary_text.setPlainText(summary)
        
        # Metrics table
        metrics = [
            ("Success Rate", f"{analysis.get('success_rate', 0)}%"),
            ("Total Builds", str(analysis.get('total_builds', 0))),
            ("Failed Builds", str(analysis.get('failed_builds', 0))),
            ("Average Duration", "Calculating..."),
            ("Most Common Failure", "Analyzing...")
        ]
        
        self.metrics_table.setRowCount(len(metrics))
        for i, (metric, value) in enumerate(metrics):
            self.metrics_table.setItem(i, 0, QTableWidgetItem(metric))
            
            value_item = QTableWidgetItem(value)
            if "%" in value:
                try:
                    pct = float(value.replace('%', ''))
                    if pct >= 80:
                        value_item.setForeground(QColor(39, 174, 96))  # Green
                    elif pct >= 60:
                        value_item.setForeground(QColor(243, 156, 18))  # Orange
                    else:
                        value_item.setForeground(QColor(231, 76, 60))  # Red
                except:
                    pass
            
            self.metrics_table.setItem(i, 1, value_item)
    
    def populate_analysis(self, analysis):
        """Populate analysis tab with actual database failure data"""
        # Use actual failure data from database
        failures = self.report_data.get('failures', [])
        self.failures_table.setRowCount(len(failures))
        
        for i, failure in enumerate(failures):
            self.failures_table.setItem(i, 0, QTableWidgetItem(failure.get('stage_name', 'Unknown')))
            self.failures_table.setItem(i, 1, QTableWidgetItem(str(failure.get('failure_count', 0))))
            
            errors = failure.get('errors', '') or 'No error details'
            # Truncate long error messages
            if len(errors) > 100:
                errors = errors[:100] + '...'
            self.failures_table.setItem(i, 2, QTableWidgetItem(errors))
        
        # Build stages (if specific build)
        if 'stages' in self.report_data:
            stages = self.report_data['stages']
            self.stages_table.setRowCount(len(stages))
            
            for i, stage in enumerate(stages):
                self.stages_table.setItem(i, 0, QTableWidgetItem(stage.get('stage_name', 'Unknown')))
                
                status_item = QTableWidgetItem(stage.get('status', 'Unknown'))
                if stage.get('status') == 'completed':
                    status_item.setForeground(QColor(39, 174, 96))  # Green
                elif stage.get('status') == 'failed':
                    status_item.setForeground(QColor(231, 76, 60))  # Red
                
                self.stages_table.setItem(i, 1, status_item)
                
                duration = stage.get('duration_seconds', 0)
                duration_text = f"{duration}s" if duration else "N/A"
                self.stages_table.setItem(i, 2, QTableWidgetItem(duration_text))
                
                issues = stage.get('error_message', 'None')
                self.stages_table.setItem(i, 3, QTableWidgetItem(issues))
    
    def populate_recommendations(self, analysis):
        """Populate recommendations tab with ML-driven recommendations"""
        recommendations = self.report_data.get('recommendations', [])
        
        # Add ML recommendations if available
        ml_insights = self.report_data.get('ml_insights', {})
        if ml_insights and ml_insights.get('insights'):
            for insight_type, insight_data in ml_insights['insights'].items():
                if insight_data.get('recommendations'):
                    for rec in insight_data['recommendations']:
                        recommendations.append({
                            'priority': 'High',
                            'category': f'ML-{insight_type}',
                            'issue': f'ML detected {insight_type} issue',
                            'recommendation': rec
                        })
        
        self.recommendations_table.setRowCount(len(recommendations))
        
        for i, rec in enumerate(recommendations):
            priority_item = QTableWidgetItem(rec.get('priority', 'Medium'))
            if rec.get('priority') == 'High':
                priority_item.setForeground(QColor(231, 76, 60))  # Red
            elif rec.get('priority') == 'Critical':
                priority_item.setForeground(QColor(155, 89, 182))  # Purple
            
            self.recommendations_table.setItem(i, 0, priority_item)
            self.recommendations_table.setItem(i, 1, QTableWidgetItem(rec.get('category', 'General')))
            self.recommendations_table.setItem(i, 2, QTableWidgetItem(rec.get('issue', 'No issue specified')))
            self.recommendations_table.setItem(i, 3, QTableWidgetItem(rec.get('recommendation', 'No recommendation')))
        
        # Detailed recommendations text
        detailed_text = "📋 DETAILED RECOMMENDATIONS\\n\\n"
        
        for i, rec in enumerate(recommendations, 1):
            detailed_text += f"{i}. {rec.get('category', 'General')} - {rec.get('priority', 'Medium')} Priority\\n"
            detailed_text += f"   Issue: {rec.get('issue', 'No issue specified')}\\n"
            detailed_text += f"   Recommendation: {rec.get('recommendation', 'No recommendation')}\\n"
            detailed_text += f"   Action: {rec.get('action', 'No specific action')}\\n\\n"
        
        if not recommendations:
            detailed_text += "🎉 No specific recommendations - your build success rate is excellent!"
        
        self.recommendations_text.setPlainText(detailed_text)
    
    def populate_next_build_advice(self, analysis):
        """Populate next build advice tab"""
        advice_list = analysis.get('next_build_advice', [])
        self.advice_table.setRowCount(len(advice_list))
        
        for i, advice in enumerate(advice_list):
            priority_item = QTableWidgetItem(advice.get('priority', 'Medium'))
            if advice.get('priority') == 'Critical':
                priority_item.setForeground(QColor(231, 76, 60))  # Red
            elif advice.get('priority') == 'High':
                priority_item.setForeground(QColor(243, 156, 18))  # Orange
            
            self.advice_table.setItem(i, 0, priority_item)
            self.advice_table.setItem(i, 1, QTableWidgetItem(advice.get('action', 'No action specified')))
            self.advice_table.setItem(i, 2, QTableWidgetItem(advice.get('estimated_time', 'Unknown')))
            self.advice_table.setItem(i, 3, QTableWidgetItem(advice.get('message', 'No details')))
        
        # Pre-build checklist
        checklist = """🚀 PRE-BUILD CHECKLIST

Before starting your next LFS build, complete these steps:

□ System Preparation
  • Run compliance check (Tools > Compliance Check)
  • Verify LFS directory permissions (Build Actions > Setup LFS Permissions)
  • Ensure 15+ GB free disk space available
  • Check that required development tools are installed

□ Configuration Review
  • Select or create appropriate build configuration
  • Review kernel configuration if building custom kernel
  • Verify package cache status (Tools > Package Manager)

□ Environment Check
  • Ensure stable network connection for downloads
  • Close unnecessary applications to free memory
  • Verify no other builds are running

□ Backup & Recovery
  • Backup any important configurations
  • Note current system state for rollback if needed

□ Monitoring Setup
  • Open build monitoring tabs for real-time tracking
  • Enable auto-refresh for live log streaming
  • Prepare for 4-8 hour build duration

Following this checklist significantly improves build success rates!"""
        
        self.checklist_text.setPlainText(checklist)
    
    def export_report(self):
        """Export report to file"""
        if not self.report_data:
            QMessageBox.warning(self, "No Data", "No report data to export")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Build Report", 
            f"build_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            try:
                if filename.endswith('.json'):
                    with open(filename, 'w') as f:
                        json.dump(self.report_data, f, indent=2, default=str)
                else:
                    # Export as text
                    with open(filename, 'w') as f:
                        f.write(self.generate_text_report())
                
                QMessageBox.information(self, "Export Complete", f"Report exported to {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export report: {str(e)}")
    
    def copy_to_clipboard(self):
        """Copy report to clipboard"""
        try:
            text_report = self.generate_text_report()
            clipboard = QApplication.clipboard()
            clipboard.setText(text_report)
            QMessageBox.information(self, "Copied", "Report copied to clipboard")
        except Exception as e:
            QMessageBox.critical(self, "Copy Error", f"Failed to copy report: {str(e)}")
    
    def print_report(self):
        """Print report"""
        try:
            from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
            from PyQt5.QtGui import QTextDocument
            
            printer = QPrinter()
            dialog = QPrintDialog(printer, self)
            
            if dialog.exec_() == QPrintDialog.Accepted:
                document = QTextDocument()
                document.setPlainText(self.generate_text_report())
                document.print_(printer)
                QMessageBox.information(self, "Print Complete", "Report sent to printer")
                
        except ImportError:
            QMessageBox.warning(self, "Print Error", "Print support not available")
        except Exception as e:
            QMessageBox.critical(self, "Print Error", f"Failed to print report: {str(e)}")
    
    def generate_text_report(self):
        """Generate text version of report with actual data"""
        if not self.report_data:
            return "No report data available"
        
        analysis = self.report_data.get('analysis', {})
        
        # Get actual build data from database
        try:
            builds = self.db.execute_query(
                "SELECT build_id, status, start_time, duration_seconds FROM builds ORDER BY start_time DESC LIMIT 10",
                fetch=True
            ) or []
            
            total_builds = len(builds)
            successful = len([b for b in builds if b.get('status') == 'success'])
            failed = len([b for b in builds if b.get('status') == 'failed'])
            success_rate = (successful / total_builds * 100) if total_builds > 0 else 0
            
        except Exception:
            builds = []
            total_builds = analysis.get('total_builds', 0)
            successful = analysis.get('successful_builds', 0)
            failed = analysis.get('failed_builds', 0)
            success_rate = analysis.get('success_rate', 0)
        
        report = f"""LFS BUILD ANALYSIS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*50}

OVERVIEW
--------
Total Builds: {total_builds}
Successful Builds: {successful}
Failed Builds: {failed}
Success Rate: {success_rate:.1f}%

RECENT BUILDS
-------------
"""
        
        if builds:
            for build in builds[:5]:
                status_icon = "✅" if build.get('status') == 'success' else "❌" if build.get('status') == 'failed' else "⏸️"
                duration = f"{build.get('duration_seconds', 0)//60}min" if build.get('duration_seconds') else "N/A"
                report += f"{status_icon} {build.get('build_id', 'Unknown')} - {build.get('status', 'unknown')} ({duration})\n"
        else:
            report += "No recent builds found\n"
        
        report += "\nCOMMON FAILURE PATTERNS\n-----------------------\n"
        
        failures = analysis.get('common_failures', [])
        if failures:
            for failure in failures:
                report += f"• {failure.get('stage', 'Unknown')}: {failure.get('failure_count', 0)} failures\n"
                for error in failure.get('common_errors', [])[:2]:
                    report += f"  - {error}\n"
        else:
            report += "No failure patterns detected\n"
        
        report += "\nRECOMMENDATIONS\n---------------\n"
        
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            for rec in recommendations:
                report += f"• [{rec.get('priority', 'Medium')}] {rec.get('issue', 'No issue')}\n"
                report += f"  Action: {rec.get('recommendation', 'No recommendation')}\n\n"
        else:
            report += "No specific recommendations - build performance is good\n"
        
        report += "NEXT BUILD ADVICE\n-----------------\n"
        
        advice_list = analysis.get('next_build_advice', [])
        if advice_list:
            for advice in advice_list:
                report += f"• {advice.get('action', 'No action')} ({advice.get('estimated_time', 'Unknown time')})\n"
        else:
            report += "• Run system compliance check before next build\n"
            report += "• Ensure adequate disk space (15+ GB)\n"
            report += "• Verify network connectivity for downloads\n"
        
        return report