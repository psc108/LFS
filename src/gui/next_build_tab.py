from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QTextEdit, QSplitter,
                             QLabel, QLineEdit, QComboBox, QMessageBox, QHeaderView,
                             QMenu, QAction, QProgressBar, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from datetime import datetime
import json


class NextBuildTab(QWidget):
    """Tab for browsing and managing next build reports"""
    
    def __init__(self, db_manager, build_advisor):
        super().__init__()
        self.db = db_manager
        self.advisor = build_advisor
        self.current_report = None
        self.setup_ui()
        self.load_reports()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_reports)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Next Build Reports")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search reports...")
        self.search_input.textChanged.connect(self.search_reports)
        header_layout.addWidget(QLabel("Search:"))
        header_layout.addWidget(self.search_input)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_reports)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Reports list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Reports table
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(6)
        self.reports_table.setHorizontalHeaderLabels([
            "Title", "Generated", "Success Rate", "Builds", "Size", "Actions"
        ])
        
        # Configure table
        header = self.reports_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        self.reports_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.reports_table.itemSelectionChanged.connect(self.on_report_selected)
        self.reports_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.reports_table.customContextMenuRequested.connect(self.show_context_menu)
        
        left_layout.addWidget(QLabel("Available Reports:"))
        left_layout.addWidget(self.reports_table)
        
        # Report stats
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.Box)
        stats_layout = QHBoxLayout(stats_frame)
        
        self.total_reports_label = QLabel("Total: 0")
        self.avg_success_label = QLabel("Avg Success: 0%")
        self.latest_report_label = QLabel("Latest: None")
        
        stats_layout.addWidget(self.total_reports_label)
        stats_layout.addWidget(self.avg_success_label)
        stats_layout.addWidget(self.latest_report_label)
        stats_layout.addStretch()
        
        left_layout.addWidget(stats_frame)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Report details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Report header
        report_header_layout = QHBoxLayout()
        self.report_title_label = QLabel("Select a report to view details")
        self.report_title_label.setFont(QFont("Arial", 12, QFont.Bold))
        report_header_layout.addWidget(self.report_title_label)
        
        report_header_layout.addStretch()
        
        # Action buttons
        self.export_btn = QPushButton("📄 Export")
        self.export_btn.clicked.connect(self.export_report)
        self.export_btn.setEnabled(False)
        
        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.clicked.connect(self.copy_report)
        self.copy_btn.setEnabled(False)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self.delete_report)
        self.delete_btn.setEnabled(False)
        
        report_header_layout.addWidget(self.export_btn)
        report_header_layout.addWidget(self.copy_btn)
        report_header_layout.addWidget(self.delete_btn)
        
        right_layout.addLayout(report_header_layout)
        
        # Report content
        self.report_content = QTextEdit()
        self.report_content.setReadOnly(True)
        self.report_content.setFont(QFont("Courier", 10))
        right_layout.addWidget(self.report_content)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def load_reports(self):
        """Load all reports from database"""
        try:
            reports = self.advisor.get_all_reports()
            self.populate_reports_table(reports)
            self.update_stats(reports)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load reports: {str(e)}")
    
    def populate_reports_table(self, reports):
        """Populate the reports table"""
        self.reports_table.setRowCount(len(reports))
        
        for row, report in enumerate(reports):
            # Title
            title_item = QTableWidgetItem(report['report_title'])
            title_item.setData(Qt.UserRole, report['id'])
            self.reports_table.setItem(row, 0, title_item)
            
            # Generated date
            generated_date = report['generated_at'].strftime('%Y-%m-%d %H:%M') if report['generated_at'] else 'Unknown'
            self.reports_table.setItem(row, 1, QTableWidgetItem(generated_date))
            
            # Success rate
            success_rate = f"{report['success_rate']:.1f}%" if report['success_rate'] else "0%"
            self.reports_table.setItem(row, 2, QTableWidgetItem(success_rate))
            
            # Builds analyzed
            builds_count = str(report['total_builds_analyzed']) if report['total_builds_analyzed'] else "0"
            self.reports_table.setItem(row, 3, QTableWidgetItem(builds_count))
            
            # Size
            size_kb = report['report_size_bytes'] / 1024 if report['report_size_bytes'] else 0
            size_text = f"{size_kb:.1f} KB" if size_kb > 0 else "0 KB"
            self.reports_table.setItem(row, 4, QTableWidgetItem(size_text))
            
            # Actions button
            actions_btn = QPushButton("View")
            actions_btn.clicked.connect(lambda checked, r_id=report['id']: self.view_report(r_id))
            self.reports_table.setCellWidget(row, 5, actions_btn)
    
    def update_stats(self, reports):
        """Update report statistics"""
        total_reports = len(reports)
        self.total_reports_label.setText(f"Total: {total_reports}")
        
        if reports:
            avg_success = sum(r['success_rate'] or 0 for r in reports) / total_reports
            self.avg_success_label.setText(f"Avg Success: {avg_success:.1f}%")
            
            latest = reports[0]['generated_at'].strftime('%Y-%m-%d %H:%M') if reports[0]['generated_at'] else 'Unknown'
            self.latest_report_label.setText(f"Latest: {latest}")
        else:
            self.avg_success_label.setText("Avg Success: 0%")
            self.latest_report_label.setText("Latest: None")
    
    def search_reports(self):
        """Search reports based on input"""
        search_term = self.search_input.text().strip()
        
        if search_term:
            try:
                reports = self.advisor.search_reports(search_term)
                self.populate_reports_table(reports)
                self.update_stats(reports)
            except Exception as e:
                QMessageBox.warning(self, "Search Error", f"Failed to search reports: {str(e)}")
        else:
            self.load_reports()
    
    def on_report_selected(self):
        """Handle report selection"""
        current_row = self.reports_table.currentRow()
        if current_row >= 0:
            title_item = self.reports_table.item(current_row, 0)
            if title_item:
                report_id = title_item.data(Qt.UserRole)
                self.view_report(report_id)
    
    def view_report(self, report_id):
        """View detailed report"""
        try:
            report = self.advisor.get_report_details(report_id)
            if report:
                self.current_report = report
                self.display_report(report)
                self.enable_report_actions(True)
            else:
                QMessageBox.warning(self, "Error", "Report not found")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load report: {str(e)}")
    
    def display_report(self, report):
        """Display report content"""
        self.report_title_label.setText(report['report_title'])
        
        # Display full analysis output
        content = report.get('full_analysis_output', 'No content available')
        self.report_content.setPlainText(content)
    
    def enable_report_actions(self, enabled):
        """Enable/disable report action buttons"""
        self.export_btn.setEnabled(enabled)
        self.copy_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(enabled)
    
    def export_report(self):
        """Export current report"""
        if not self.current_report:
            return
        
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Report", 
                f"build_report_{self.current_report['id']}.txt",
                "Text Files (*.txt);;All Files (*)"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.current_report.get('full_analysis_output', ''))
                
                # Log export
                self.advisor._log_report_access(self.current_report['id'], 'export')
                
                QMessageBox.information(self, "Success", f"Report exported to {filename}")
                
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to export report: {str(e)}")
    
    def copy_report(self):
        """Copy report to clipboard"""
        if not self.current_report:
            return
        
        try:
            from PyQt5.QtWidgets import QApplication
            
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_report.get('full_analysis_output', ''))
            
            # Log copy
            self.advisor._log_report_access(self.current_report['id'], 'copy')
            
            QMessageBox.information(self, "Success", "Report copied to clipboard")
            
        except Exception as e:
            QMessageBox.warning(self, "Copy Error", f"Failed to copy report: {str(e)}")
    
    def delete_report(self):
        """Delete current report"""
        if not self.current_report:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete this report?\n\n{self.current_report['report_title']}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success = self.advisor.delete_report(self.current_report['id'])
                if success:
                    QMessageBox.information(self, "Success", "Report deleted successfully")
                    self.current_report = None
                    self.report_title_label.setText("Select a report to view details")
                    self.report_content.clear()
                    self.enable_report_actions(False)
                    self.load_reports()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete report")
                    
            except Exception as e:
                QMessageBox.warning(self, "Delete Error", f"Failed to delete report: {str(e)}")
    
    def show_context_menu(self, position):
        """Show context menu for reports table"""
        if self.reports_table.itemAt(position):
            menu = QMenu()
            
            view_action = QAction("View Report", self)
            view_action.triggered.connect(self.on_report_selected)
            menu.addAction(view_action)
            
            menu.addSeparator()
            
            export_action = QAction("Export Report", self)
            export_action.triggered.connect(self.export_report)
            menu.addAction(export_action)
            
            copy_action = QAction("Copy to Clipboard", self)
            copy_action.triggered.connect(self.copy_report)
            menu.addAction(copy_action)
            
            menu.addSeparator()
            
            delete_action = QAction("Delete Report", self)
            delete_action.triggered.connect(self.delete_report)
            menu.addAction(delete_action)
            
            menu.exec_(self.reports_table.mapToGlobal(position))
    
    def generate_new_report(self):
        """Generate a new build analysis report"""
        try:
            # Generate comprehensive advice which stores report in database
            advice = self.advisor.generate_build_advice()
            
            if 'error' in advice:
                QMessageBox.warning(self, "Error", f"Failed to generate report: {advice['error']}")
            else:
                QMessageBox.information(self, "Success", "New build analysis report generated")
                self.load_reports()
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to generate report: {str(e)}")