from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                            QWidget, QTextEdit, QTreeWidget, QTreeWidgetItem,
                            QLabel, QProgressBar, QPushButton, QSplitter)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from datetime import datetime

class BuildDetailsDialog(QDialog):
    def __init__(self, db_manager, build_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.build_id = build_id
        self.setWindowTitle(f"Build Details - {build_id}")
        self.setModal(False)
        self.resize(900, 700)
        
        # Auto-refresh timer for running builds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        
        self.setup_ui()
        self.load_build_data()
        
        # Start auto-refresh if build is running
        build_details = self.db.get_build_details(build_id)
        if build_details and build_details['build']['status'] == 'running':
            self.refresh_timer.start(2000)  # Refresh every 2 seconds
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Build info header
        info_layout = QHBoxLayout()
        self.build_id_label = QLabel(f"Build ID: {self.build_id}")
        self.build_id_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.status_label = QLabel("Status: Loading...")
        self.progress_label = QLabel("Progress: 0/0")
        
        info_layout.addWidget(self.build_id_label)
        info_layout.addStretch()
        info_layout.addWidget(self.status_label)
        info_layout.addWidget(self.progress_label)
        layout.addLayout(info_layout)
        
        # Overall progress bar
        self.overall_progress = QProgressBar()
        layout.addWidget(self.overall_progress)
        
        # Tab widget for different views
        self.tab_widget = QTabWidget()
        
        # Stages tab
        self.stages_widget = QWidget()
        stages_layout = QVBoxLayout(self.stages_widget)
        
        self.stages_tree = QTreeWidget()
        self.stages_tree.setHeaderLabels(["Stage", "Status", "Start Time", "Duration", "Progress"])
        self.stages_tree.itemClicked.connect(self.show_stage_details)
        stages_layout.addWidget(self.stages_tree)
        
        self.tab_widget.addTab(self.stages_widget, "Build Stages")
        
        # Live logs tab
        self.logs_widget = QWidget()
        logs_layout = QVBoxLayout(self.logs_widget)
        
        # Log controls
        log_controls = QHBoxLayout()
        self.auto_scroll_btn = QPushButton("Auto Scroll")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.clear_logs_btn = QPushButton("Clear")
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        
        log_controls.addWidget(QLabel("Live Build Output:"))
        log_controls.addStretch()
        log_controls.addWidget(self.auto_scroll_btn)
        log_controls.addWidget(self.clear_logs_btn)
        logs_layout.addLayout(log_controls)
        
        self.live_logs = QTextEdit()
        self.live_logs.setFont(QFont("Courier", 9))
        self.live_logs.setReadOnly(True)
        logs_layout.addWidget(self.live_logs)
        
        self.tab_widget.addTab(self.logs_widget, "Live Logs")
        
        # Documents tab
        self.docs_widget = QWidget()
        docs_layout = QVBoxLayout(self.docs_widget)
        
        # Documents tree and viewer
        docs_splitter = QSplitter(Qt.Horizontal)
        
        self.docs_tree = QTreeWidget()
        self.docs_tree.setHeaderLabels(["Document", "Type", "Created"])
        self.docs_tree.itemClicked.connect(self.show_document)
        docs_splitter.addWidget(self.docs_tree)
        
        self.doc_viewer = QTextEdit()
        self.doc_viewer.setFont(QFont("Courier", 9))
        self.doc_viewer.setReadOnly(True)
        docs_splitter.addWidget(self.doc_viewer)
        
        docs_splitter.setSizes([300, 600])
        docs_layout.addWidget(docs_splitter)
        
        self.tab_widget.addTab(self.docs_widget, "Documents")
        
        # Configuration tab
        self.config_widget = QWidget()
        config_layout = QVBoxLayout(self.config_widget)
        
        self.config_viewer = QTextEdit()
        self.config_viewer.setFont(QFont("Courier", 9))
        self.config_viewer.setReadOnly(True)
        config_layout.addWidget(self.config_viewer)
        
        self.tab_widget.addTab(self.config_widget, "Configuration")
        
        layout.addWidget(self.tab_widget)
        
        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        close_layout.addWidget(self.close_btn)
        layout.addLayout(close_layout)
        
        self.setLayout(layout)
    
    def load_build_data(self):
        """Load and display build data"""
        details = self.db.get_build_details(self.build_id)
        if not details:
            return
        
        build = details['build']
        stages = details['stages']
        documents = details['documents']
        
        # Update header info
        self.status_label.setText(f"Status: {build['status'].upper()}")
        self.progress_label.setText(f"Progress: {build['completed_stages']}/{build['total_stages']}")
        
        # Update progress bar
        if build['total_stages'] > 0:
            progress = (build['completed_stages'] / build['total_stages']) * 100
            self.overall_progress.setValue(int(progress))
        
        # Update stages tree
        self.stages_tree.clear()
        for stage in stages:
            duration = ""
            if stage['start_time'] and stage['end_time']:
                delta = stage['end_time'] - stage['start_time']
                duration = f"{delta.total_seconds():.1f}s"
            elif stage['start_time']:
                delta = datetime.now() - stage['start_time']
                duration = f"{delta.total_seconds():.1f}s (running)"
            
            # Determine progress indicator
            progress_text = ""
            if stage['status'] == 'running':
                progress_text = "🔄 Running"
            elif stage['status'] == 'success':
                progress_text = "✅ Complete"
            elif stage['status'] == 'failed':
                progress_text = "❌ Failed"
            elif stage['status'] == 'pending':
                progress_text = "⏳ Pending"
            
            start_time = stage['start_time'].strftime('%H:%M:%S') if stage['start_time'] else ""
            
            item = QTreeWidgetItem([
                stage['stage_name'],
                stage['status'].upper(),
                start_time,
                duration,
                progress_text
            ])
            
            # Color code by status
            if stage['status'] == 'running':
                item.setBackground(0, Qt.yellow)
            elif stage['status'] == 'success':
                item.setBackground(0, Qt.green)
            elif stage['status'] == 'failed':
                item.setBackground(0, Qt.red)
            
            self.stages_tree.addTopLevelItem(item)
        
        # Update documents tree
        self.docs_tree.clear()
        for doc in documents:
            item = QTreeWidgetItem([
                doc['title'],
                doc['document_type'].upper(),
                doc['created_at'].strftime('%H:%M:%S')
            ])
            item.setData(0, Qt.UserRole, doc)
            self.docs_tree.addTopLevelItem(item)
        
        # Load configuration
        config_docs = [d for d in documents if d['document_type'] == 'config']
        if config_docs:
            self.config_viewer.setPlainText(config_docs[0]['content'])
        
        # Update live logs
        self.update_live_logs(stages)
    
    def update_live_logs(self, stages):
        """Update live logs with latest stage output"""
        log_content = ""
        for stage in stages:
            if stage['output_log'] or stage['error_log']:
                log_content += f"=== {stage['stage_name']} ({stage['status']}) ===\n"
                if stage['output_log']:
                    log_content += stage['output_log'] + "\n"
                if stage['error_log']:
                    log_content += "ERRORS:\n" + stage['error_log'] + "\n"
                log_content += "\n"
        
        # Only update if content changed to avoid flickering
        if self.live_logs.toPlainText() != log_content:
            self.live_logs.setPlainText(log_content)
            
            # Auto-scroll to bottom if enabled
            if self.auto_scroll_btn.isChecked():
                scrollbar = self.live_logs.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
    
    def show_stage_details(self, item):
        """Show detailed information for selected stage"""
        stage_name = item.text(0)
        details = self.db.get_build_details(self.build_id)
        
        for stage in details['stages']:
            if stage['stage_name'] == stage_name:
                content = f"Stage: {stage['stage_name']}\n"
                content += f"Status: {stage['status']}\n"
                content += f"Order: {stage['stage_order']}\n"
                
                if stage['start_time']:
                    content += f"Started: {stage['start_time']}\n"
                if stage['end_time']:
                    content += f"Ended: {stage['end_time']}\n"
                
                content += "\n--- OUTPUT ---\n"
                content += stage['output_log'] or "No output"
                
                if stage['error_log']:
                    content += "\n\n--- ERRORS ---\n"
                    content += stage['error_log']
                
                self.doc_viewer.setPlainText(content)
                break
    
    def show_document(self, item):
        """Show selected document content"""
        doc = item.data(0, Qt.UserRole)
        if doc:
            content = f"Document: {doc['title']}\n"
            content += f"Type: {doc['document_type']}\n"
            content += f"Created: {doc['created_at']}\n"
            content += f"Size: {len(doc['content'])} characters\n"
            content += "\n" + "="*50 + "\n\n"
            content += doc['content']
            
            self.doc_viewer.setPlainText(content)
    
    def clear_logs(self):
        """Clear the live logs display"""
        self.live_logs.clear()
    
    def refresh_data(self):
        """Refresh build data (for running builds)"""
        details = self.db.get_build_details(self.build_id)
        if details:
            build = details['build']
            if build['status'] != 'running':
                # Build finished, stop auto-refresh
                self.refresh_timer.stop()
            
            self.load_build_data()
    
    def closeEvent(self, event):
        """Stop timer when dialog is closed"""
        self.refresh_timer.stop()
        super().closeEvent(event)