#!/usr/bin/env python3

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime

class MLSolutionIntegration:
    """Integration class for ML solution finding in GUI components"""
    
    def __init__(self, parent_window):
        self.parent = parent_window
        self.ml_engine = getattr(parent_window, 'ml_engine', None)
        self.db = getattr(parent_window, 'db', None)
    
    def add_solution_research_button(self, layout, build_id_callback=None):
        """Add solution research button to any layout"""
        solution_btn = QPushButton("🔍 Find Internet Solutions")
        solution_btn.clicked.connect(lambda: self.open_solution_research(build_id_callback))
        solution_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; }")
        solution_btn.setToolTip("Use ML to search internet for solutions to build failures")
        layout.addWidget(solution_btn)
        return solution_btn
    
    def open_solution_research(self, build_id_callback=None):
        """Open solution research dialog"""
        try:
            from .solution_report_dialog import SolutionReportDialog
            
            dialog = SolutionReportDialog(self.parent, self.db, self.ml_engine)
            
            # If build_id_callback provided, pre-select build
            if build_id_callback and callable(build_id_callback):
                build_id = build_id_callback()
                if build_id:
                    # Find and select the build in combo box
                    for i in range(dialog.build_combo.count()):
                        if dialog.build_combo.itemData(i) == build_id:
                            dialog.build_combo.setCurrentIndex(i)
                            break
            
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self.parent, "Solution Research Error", f"Failed to open solution research: {str(e)}")
    
    def add_solution_context_menu(self, table_widget, build_id_column=0):
        """Add solution research to context menu of build tables"""
        def show_context_menu(position):
            item = table_widget.itemAt(position)
            if item:
                row = item.row()
                build_id = table_widget.item(row, build_id_column).text()
                
                menu = QMenu()
                solution_action = menu.addAction("🔍 Find Internet Solutions")
                solution_action.triggered.connect(lambda: self.research_build_solutions(build_id))
                
                menu.exec_(table_widget.mapToGlobal(position))
        
        table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        table_widget.customContextMenuRequested.connect(show_context_menu)
    
    def research_build_solutions(self, build_id):
        """Research solutions for specific build"""
        if not self.ml_engine:
            QMessageBox.warning(self.parent, "ML Engine", "ML engine not available for solution research")
            return
        
        try:
            # Show progress dialog
            progress = QProgressDialog("Researching internet solutions...", "Cancel", 0, 0, self.parent)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            # Start solution research
            solutions_report = self.ml_engine.find_build_solutions(build_id)
            progress.close()
            
            if solutions_report and 'error' not in solutions_report:
                self.show_solution_results(build_id, solutions_report)
            else:
                QMessageBox.information(self.parent, "Solution Research", 
                                      f"No solutions found for build {build_id}")
        
        except Exception as e:
            progress.close()
            QMessageBox.critical(self.parent, "Solution Research Error", f"Failed to research solutions: {str(e)}")
    
    def show_solution_results(self, build_id, solutions_report):
        """Show solution results in a dialog"""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle(f"Internet Solutions for Build {build_id}")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel(f"🔍 Internet Solutions for Build {build_id}")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #3498db;")
        layout.addWidget(header)
        
        # Results
        results_text = QTextEdit()
        results_text.setFont(QFont("Courier", 9))
        
        content = f"""INTERNET SOLUTION RESEARCH RESULTS
{'=' * 50}

Build ID: {build_id}
Total Failures: {solutions_report.get('total_failures', 0)}
Solutions Found: {solutions_report.get('solutions_found', 0)}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        
        if solutions_report.get('solutions_found', 0) > 0:
            for stage_solution in solutions_report.get('stage_solutions', []):
                content += f"STAGE: {stage_solution['stage_name']}\n{'-' * 30}\n"
                content += f"Package: {stage_solution.get('package_name', 'Unknown')}\n"
                content += f"Error: {stage_solution['error_summary']}\n"
                content += f"Solutions Found: {stage_solution['solution_count']}\n\n"
                
                for i, solution in enumerate(stage_solution.get('solutions', []), 1):
                    content += f"  Solution {i}:\n"
                    content += f"    Source: {solution['source']}\n"
                    content += f"    Title: {solution['title']}\n"
                    content += f"    URL: {solution['url']}\n"
                    content += f"    Relevance: {solution['relevance_score']}\n\n"
                
                content += "\n"
        else:
            content += "No internet solutions found for the build failures.\n"
        
        results_text.setPlainText(content)
        layout.addWidget(results_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        export_btn = QPushButton("Export Results")
        export_btn.clicked.connect(lambda: self.export_solution_results(build_id, content))
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        
        button_layout.addWidget(export_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        dialog.exec_()
    
    def export_solution_results(self, build_id, content):
        """Export solution results to file"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self.parent,
                "Export Solution Results",
                f"solutions_{build_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "Text Files (*.txt)"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    f.write(content)
                
                QMessageBox.information(self.parent, "Export Complete", f"Results exported to {filename}")
        
        except Exception as e:
            QMessageBox.critical(self.parent, "Export Error", f"Failed to export results: {str(e)}")
    
    def add_solution_status_indicator(self, status_bar):
        """Add ML solution status to status bar"""
        if self.ml_engine:
            ml_status = QLabel("🔍 ML Solutions: Ready")
            ml_status.setStyleSheet("color: #27ae60;")
        else:
            ml_status = QLabel("🔍 ML Solutions: Unavailable")
            ml_status.setStyleSheet("color: #e74c3c;")
        
        status_bar.addWidget(ml_status)
        return ml_status