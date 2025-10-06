#!/usr/bin/env python3

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime

class SolutionReportDialog(QDialog):
    """Dialog for displaying ML-powered solution research results"""
    
    def __init__(self, parent, db_manager, ml_engine):
        super().__init__(parent)
        self.db = db_manager
        self.ml_engine = ml_engine
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("ML Solution Research")
        self.resize(900, 700)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("🔍 ML-Powered Build Solution Research")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #3498db;")
        layout.addWidget(header)
        
        # Build selection
        selection_group = QGroupBox("Select Build for Solution Research")
        selection_layout = QHBoxLayout()
        
        self.build_combo = QComboBox()
        self.load_failed_builds()
        
        research_btn = QPushButton("🔍 Research Solutions")
        research_btn.clicked.connect(self.start_solution_research)
        research_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; }")
        
        selection_layout.addWidget(QLabel("Failed Build:"))
        selection_layout.addWidget(self.build_combo)
        selection_layout.addWidget(research_btn)
        selection_layout.addStretch()
        
        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)
        
        # Results tabs
        self.results_tabs = QTabWidget()
        
        # Solutions tab
        solutions_tab = QWidget()
        solutions_layout = QVBoxLayout()
        
        self.solutions_text = QTextEdit()
        self.solutions_text.setFont(QFont("Courier", 9))
        self.solutions_text.setPlainText("Select a failed build and click 'Research Solutions' to find internet-based fixes...")
        
        solutions_layout.addWidget(self.solutions_text)
        solutions_tab.setLayout(solutions_layout)
        self.results_tabs.addTab(solutions_tab, "🌐 Internet Solutions")
        
        # Analysis tab
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout()
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setFont(QFont("Courier", 9))
        self.analysis_text.setPlainText("ML analysis results will appear here...")
        
        analysis_layout.addWidget(self.analysis_text)
        analysis_tab.setLayout(analysis_layout)
        self.results_tabs.addTab(analysis_tab, "📊 ML Analysis")
        
        layout.addWidget(self.results_tabs)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to research solutions")
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        export_btn = QPushButton("📤 Export Results")
        export_btn.clicked.connect(self.export_results)
        
        clear_btn = QPushButton("🗑️ Clear Results")
        clear_btn.clicked.connect(self.clear_results)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(export_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_failed_builds(self):
        """Load failed builds into combo box"""
        try:
            if self.db:
                builds = self.db.execute_query(
                    "SELECT build_id, start_time FROM builds WHERE status = 'failed' ORDER BY start_time DESC LIMIT 20",
                    fetch=True
                )
                
                self.build_combo.clear()
                for build in builds:
                    display_text = f"{build['build_id']} - {build['start_time'].strftime('%Y-%m-%d %H:%M')}"
                    self.build_combo.addItem(display_text, build['build_id'])
                
                if not builds:
                    self.build_combo.addItem("No failed builds found")
        except Exception as e:
            self.build_combo.addItem(f"Error loading builds: {str(e)}")
    
    def start_solution_research(self):
        """Start ML-powered solution research"""
        build_id = self.build_combo.currentData()
        if not build_id:
            QMessageBox.warning(self, "No Build Selected", "Please select a failed build to research solutions.")
            return
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            self.status_label.setText("🔍 Researching solutions...")
            
            # Update solutions tab immediately
            self.solutions_text.setPlainText(f"🔍 Starting solution research for build {build_id}...\n\n"
                                           f"📊 Analyzing build failures with ML algorithms...\n"
                                           f"🌐 Searching Stack Overflow and GitHub for similar issues...\n"
                                           f"🧠 Processing error patterns and finding relevant solutions...\n\n"
                                           f"⏳ This may take 30-60 seconds depending on the number of failures...")
            
            # Start research using ML engine
            if self.ml_engine:
                solutions_report = self.ml_engine.find_build_solutions(build_id)
                self.display_solution_results(solutions_report)
            else:
                self.solutions_text.setPlainText("❌ ML engine not available for solution research")
            
        except Exception as e:
            self.solutions_text.setPlainText(f"❌ Error during solution research: {str(e)}")
        finally:
            self.progress_bar.setVisible(False)
            self.status_label.setText("Solution research complete")
    
    def display_solution_results(self, solutions_report):
        """Display solution research results"""
        try:
            if not solutions_report or 'error' in solutions_report:
                self.solutions_text.setPlainText(f"❌ Solution research failed: {solutions_report.get('error', 'Unknown error')}")
                return
            
            # Format solutions results
            solutions_content = f"""INTERNET SOLUTION RESEARCH RESULTS
{'=' * 50}

Build ID: {solutions_report.get('build_id', 'Unknown')}
Total Failures: {solutions_report.get('total_failures', 0)}
Solutions Found: {solutions_report.get('solutions_found', 0)}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
            
            if solutions_report.get('solutions_found', 0) > 0:
                for stage_solution in solutions_report.get('stage_solutions', []):
                    solutions_content += f"STAGE: {stage_solution['stage_name']}\n{'-' * 30}\n"
                    solutions_content += f"Package: {stage_solution.get('package_name', 'Unknown')}\n"
                    solutions_content += f"Error: {stage_solution['error_summary']}\n"
                    solutions_content += f"Solutions Found: {stage_solution['solution_count']}\n\n"
                    
                    for i, solution in enumerate(stage_solution.get('solutions', []), 1):
                        solutions_content += f"  Solution {i}:\n"
                        solutions_content += f"    Source: {solution['source']}\n"
                        solutions_content += f"    Title: {solution['title']}\n"
                        solutions_content += f"    URL: {solution['url']}\n"
                        solutions_content += f"    Relevance Score: {solution['relevance_score']}\n"
                        if solution.get('tags'):
                            solutions_content += f"    Tags: {', '.join(solution['tags'])}\n"
                        solutions_content += "\n"
                    
                    solutions_content += "\n"
            else:
                solutions_content += "❌ No internet solutions found for the build failures.\n"
                solutions_content += "This may indicate:\n"
                solutions_content += "• A unique or uncommon build issue\n"
                solutions_content += "• Network connectivity problems\n"
                solutions_content += "• Very recent errors not yet documented online\n"
            
            self.solutions_text.setPlainText(solutions_content)
            
            # Update analysis tab
            analysis_content = f"""ML ANALYSIS SUMMARY
{'=' * 30}

Build Analysis: {solutions_report.get('build_id', 'Unknown')}
ML Engine Status: Active
Solution Sources: Stack Overflow, GitHub Issues
Search Algorithm: Keyword extraction + relevance scoring

Error Pattern Analysis:
• Total error patterns identified: {solutions_report.get('total_failures', 0)}
• Unique error signatures: {len(set(s['stage_name'] for s in solutions_report.get('stage_solutions', [])))}
• Solution match confidence: {solutions_report.get('solutions_found', 0) / max(1, solutions_report.get('total_failures', 1)) * 100:.1f}%

Recommendation:
"""
            
            if solutions_report.get('solutions_found', 0) > 0:
                analysis_content += "✅ Review the internet solutions found for potential fixes\n"
                analysis_content += "✅ Check solution relevance scores to prioritize fixes\n"
                analysis_content += "✅ Test solutions in a safe environment before applying\n"
            else:
                analysis_content += "⚠️ Consider manual troubleshooting or consulting LFS documentation\n"
                analysis_content += "⚠️ Check system logs for additional error context\n"
                analysis_content += "⚠️ Verify build environment and dependencies\n"
            
            self.analysis_text.setPlainText(analysis_content)
            
        except Exception as e:
            self.solutions_text.setPlainText(f"❌ Error displaying results: {str(e)}")
    
    def export_results(self):
        """Export solution research results"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, 
                "Export Solution Research Results", 
                f"solution_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "Text Files (*.txt)"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    f.write("INTERNET SOLUTION RESEARCH RESULTS\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(self.solutions_text.toPlainText())
                    f.write("\n\n" + "=" * 50 + "\n")
                    f.write("ML ANALYSIS\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(self.analysis_text.toPlainText())
                
                QMessageBox.information(self, "Export Complete", f"Results exported to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export results: {str(e)}")
    
    def clear_results(self):
        """Clear all results"""
        self.solutions_text.setPlainText("Select a failed build and click 'Research Solutions' to find internet-based fixes...")
        self.analysis_text.setPlainText("ML analysis results will appear here...")
        self.status_label.setText("Ready to research solutions")