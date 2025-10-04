import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem,
                            QSplitter, QTabWidget, QLabel, QLineEdit, QComboBox,
                            QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
                            QMessageBox, QFileDialog, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from datetime import datetime
from typing import Dict, List

from ..database.db_manager import DatabaseManager
from ..build.build_engine import BuildEngine
from ..repository.repo_manager import RepositoryManager

class BuildMonitorThread(QThread):
    build_updated = pyqtSignal(dict)
    stage_updated = pyqtSignal(dict)
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.current_build_id = None
        self.running = False
    
    def set_build_id(self, build_id: str):
        self.current_build_id = build_id
    
    def run(self):
        self.running = True
        while self.running and self.current_build_id:
            try:
                build_details = self.db.get_build_details(self.current_build_id)
                if build_details:
                    self.build_updated.emit(build_details)
                self.msleep(1000)  # Update every second
            except Exception as e:
                print(f"Monitor error: {e}")
                self.msleep(5000)
    
    def stop(self):
        self.running = False

class BuildConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Build Configuration")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout()
        
        # Config name
        layout.addWidget(QLabel("Configuration Name:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        
        # Config content
        layout.addWidget(QLabel("Configuration (YAML):"))
        self.config_edit = QTextEdit()
        self.config_edit.setFont(QFont("Courier", 10))
        
        # Default LFS config
        default_config = """name: Linux From Scratch Build
version: '12.0'
stages:
  - name: prepare_host
    order: 1
    command: bash scripts/prepare_host.sh
    dependencies: []
    rollback_command: bash scripts/cleanup_host.sh
  - name: download_sources
    order: 2
    command: bash scripts/download_sources.sh
    dependencies: [prepare_host]
    rollback_command: rm -rf /mnt/lfs/sources/*
  - name: build_toolchain
    order: 3
    command: bash scripts/build_toolchain.sh
    dependencies: [download_sources]
    rollback_command: rm -rf /mnt/lfs/tools/*
"""
        self.config_edit.setPlainText(default_config)
        layout.addWidget(self.config_edit)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                 QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_config(self):
        return self.name_edit.text(), self.config_edit.toPlainText()

class LFSMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Linux From Scratch Build System")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize components
        self.db = DatabaseManager()
        self.build_engine = BuildEngine(self.db)
        self.repo_manager = RepositoryManager(self.db)
        
        # Setup callbacks
        self.build_engine.register_callback('stage_start', self.on_stage_start)
        self.build_engine.register_callback('stage_complete', self.on_stage_complete)
        self.build_engine.register_callback('build_complete', self.on_build_complete)
        self.build_engine.register_callback('build_error', self.on_build_error)
        
        # Monitor thread
        self.monitor_thread = BuildMonitorThread(self.db)
        self.monitor_thread.build_updated.connect(self.update_build_display)
        
        self.current_build_id = None
        
        self.setup_ui()
        self.load_build_history()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Build controls and history
        left_panel = QWidget()
        left_panel.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_panel)
        
        # Build controls
        controls_group = QWidget()
        controls_layout = QVBoxLayout(controls_group)
        
        controls_layout.addWidget(QLabel("Build Controls"))
        
        button_layout = QHBoxLayout()
        self.new_build_btn = QPushButton("New Build")
        self.new_build_btn.clicked.connect(self.new_build)
        
        self.start_build_btn = QPushButton("Start Build")
        self.start_build_btn.clicked.connect(self.start_build)
        self.start_build_btn.setEnabled(False)
        
        self.cancel_build_btn = QPushButton("Cancel Build")
        self.cancel_build_btn.clicked.connect(self.cancel_build)
        self.cancel_build_btn.setEnabled(False)
        
        button_layout.addWidget(self.new_build_btn)
        button_layout.addWidget(self.start_build_btn)
        button_layout.addWidget(self.cancel_build_btn)
        controls_layout.addLayout(button_layout)
        
        # Search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.search_builds)
        search_layout.addWidget(self.search_edit)
        controls_layout.addLayout(search_layout)
        
        # Status filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "running", "success", "failed", "cancelled"])
        self.status_filter.currentTextChanged.connect(self.filter_builds)
        filter_layout.addWidget(self.status_filter)
        controls_layout.addLayout(filter_layout)
        
        left_layout.addWidget(controls_group)
        
        # Build history
        left_layout.addWidget(QLabel("Build History"))
        self.build_history = QTreeWidget()
        self.build_history.setHeaderLabels(["Build ID", "Status", "Date", "Duration"])
        self.build_history.itemClicked.connect(self.select_build)
        left_layout.addWidget(self.build_history)
        
        main_layout.addWidget(left_panel)
        
        # Right panel - Build details and logs
        right_panel = QTabWidget()
        
        # Build overview tab
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        
        # Build info
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("Build ID:"))
        self.build_id_label = QLabel("None")
        info_layout.addWidget(self.build_id_label)
        info_layout.addStretch()
        
        info_layout.addWidget(QLabel("Status:"))
        self.build_status_label = QLabel("None")
        info_layout.addWidget(self.build_status_label)
        overview_layout.addLayout(info_layout)
        
        # Progress
        self.progress_bar = QProgressBar()
        overview_layout.addWidget(self.progress_bar)
        
        # Stages
        overview_layout.addWidget(QLabel("Build Stages"))
        self.stages_tree = QTreeWidget()
        self.stages_tree.setHeaderLabels(["Stage", "Status", "Duration", "Output"])
        overview_layout.addWidget(self.stages_tree)
        
        right_panel.addTab(overview_tab, "Build Overview")
        
        # Logs tab
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        
        self.logs_text = QTextEdit()
        self.logs_text.setFont(QFont("Courier", 9))
        self.logs_text.setReadOnly(True)
        logs_layout.addWidget(self.logs_text)
        
        right_panel.addTab(logs_tab, "Build Logs")
        
        # Documents tab
        docs_tab = QWidget()
        docs_layout = QVBoxLayout(docs_tab)
        
        # Document search
        doc_search_layout = QHBoxLayout()
        doc_search_layout.addWidget(QLabel("Search Documents:"))
        self.doc_search_edit = QLineEdit()
        self.doc_search_edit.textChanged.connect(self.search_documents)
        doc_search_layout.addWidget(self.doc_search_edit)
        docs_layout.addLayout(doc_search_layout)
        
        # Documents list
        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(4)
        self.documents_table.setHorizontalHeaderLabels(["Type", "Title", "Date", "Size"])
        self.documents_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.documents_table.itemClicked.connect(self.view_document)
        docs_layout.addWidget(self.documents_table)
        
        # Document viewer
        self.document_viewer = QTextEdit()
        self.document_viewer.setFont(QFont("Courier", 9))
        self.document_viewer.setReadOnly(True)
        docs_layout.addWidget(self.document_viewer)
        
        right_panel.addTab(docs_tab, "Documents")
        
        # Repository tab
        repo_tab = QWidget()
        repo_layout = QVBoxLayout(repo_tab)
        
        # Repository controls
        repo_controls = QHBoxLayout()
        self.branch_combo = QComboBox()
        self.update_branches()
        repo_controls.addWidget(QLabel("Branch:"))
        repo_controls.addWidget(self.branch_combo)
        
        self.commit_btn = QPushButton("Commit Changes")
        self.commit_btn.clicked.connect(self.commit_changes)
        repo_controls.addWidget(self.commit_btn)
        repo_layout.addLayout(repo_controls)
        
        # Repository status
        self.repo_status = QTextEdit()
        self.repo_status.setMaximumHeight(100)
        self.repo_status.setReadOnly(True)
        repo_layout.addWidget(self.repo_status)
        self.update_repo_status()
        
        right_panel.addTab(repo_tab, "Repository")
        
        main_layout.addWidget(right_panel)
    
    def new_build(self):
        dialog = BuildConfigDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, config_content = dialog.get_config()
            if name and config_content:
                # Save config to repository
                config_path = self.repo_manager.add_build_config(name, config_content)
                QMessageBox.information(self, "Success", f"Configuration saved: {config_path}")
                self.start_build_btn.setEnabled(True)
    
    def start_build(self):
        configs = self.repo_manager.list_configs()
        if not configs:
            QMessageBox.warning(self, "No Configuration", "Please create a build configuration first.")
            return
        
        # Use the most recent config for now
        config_path = configs[0]['path']
        
        try:
            build_id = self.build_engine.start_build(config_path)
            self.current_build_id = build_id
            
            self.monitor_thread.set_build_id(build_id)
            self.monitor_thread.start()
            
            self.start_build_btn.setEnabled(False)
            self.cancel_build_btn.setEnabled(True)
            
            self.load_build_history()
            
        except Exception as e:
            QMessageBox.critical(self, "Build Error", f"Failed to start build: {str(e)}")
    
    def cancel_build(self):
        if self.current_build_id:
            self.build_engine.cancel_build(self.current_build_id)
            self.monitor_thread.stop()
            self.start_build_btn.setEnabled(True)
            self.cancel_build_btn.setEnabled(False)
    
    def load_build_history(self):
        self.build_history.clear()
        builds = self.db.search_builds(limit=50)
        
        for build in builds:
            item = QTreeWidgetItem([
                build['build_id'],
                build['status'],
                build['start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                f"{build.get('duration_seconds', 0)}s"
            ])
            self.build_history.addTopLevelItem(item)
    
    def select_build(self, item):
        build_id = item.text(0)
        self.display_build_details(build_id)
    
    def display_build_details(self, build_id: str):
        details = self.db.get_build_details(build_id)
        if not details:
            return
        
        build = details['build']
        stages = details['stages']
        documents = details['documents']
        
        # Update build info
        self.build_id_label.setText(build['build_id'])
        self.build_status_label.setText(build['status'])
        
        # Update progress
        if build['total_stages'] > 0:
            progress = (build['completed_stages'] / build['total_stages']) * 100
            self.progress_bar.setValue(int(progress))
        
        # Update stages
        self.stages_tree.clear()
        for stage in stages:
            duration = ""
            if stage['start_time'] and stage['end_time']:
                delta = stage['end_time'] - stage['start_time']
                duration = f"{delta.total_seconds()}s"
            
            stage_item = QTreeWidgetItem([
                stage['stage_name'],
                stage['status'],
                duration,
                f"{len(stage.get('output_log', ''))} chars"
            ])
            self.stages_tree.addTopLevelItem(stage_item)
        
        # Update documents
        self.documents_table.setRowCount(len(documents))
        for i, doc in enumerate(documents):
            self.documents_table.setItem(i, 0, QTableWidgetItem(doc['document_type']))
            self.documents_table.setItem(i, 1, QTableWidgetItem(doc['title']))
            self.documents_table.setItem(i, 2, QTableWidgetItem(doc['created_at'].strftime('%Y-%m-%d %H:%M:%S')))
            self.documents_table.setItem(i, 3, QTableWidgetItem(f"{len(doc['content'])} chars"))
        
        # Update logs
        log_content = ""
        for stage in stages:
            if stage['output_log']:
                log_content += f"=== {stage['stage_name']} ===\n"
                log_content += stage['output_log'] + "\n\n"
        
        self.logs_text.setPlainText(log_content)
    
    def update_build_display(self, build_details):
        if build_details and build_details.get('build'):
            build_id = build_details['build']['build_id']
            self.display_build_details(build_id)
    
    def search_builds(self):
        query = self.search_edit.text()
        status = self.status_filter.currentText()
        status = "" if status == "All" else status
        
        self.build_history.clear()
        builds = self.db.search_builds(query=query, status=status, limit=50)
        
        for build in builds:
            item = QTreeWidgetItem([
                build['build_id'],
                build['status'],
                build['start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                f"{build.get('duration_seconds', 0)}s"
            ])
            self.build_history.addTopLevelItem(item)
    
    def filter_builds(self):
        self.search_builds()
    
    def search_documents(self):
        # Implement document search
        pass
    
    def view_document(self, item):
        row = item.row()
        if row >= 0:
            # Get document content and display
            pass
    
    def update_branches(self):
        branches = self.repo_manager.list_branches()
        self.branch_combo.clear()
        self.branch_combo.addItems(branches)
    
    def update_repo_status(self):
        status = self.repo_manager.get_repository_status()
        status_text = f"""Current Branch: {status.get('current_branch', 'Unknown')}
Uncommitted Changes: {'Yes' if status.get('uncommitted_changes') else 'No'}
Untracked Files: {'Yes' if status.get('untracked_files') else 'No'}
Last Commit: {status.get('last_commit', {}).get('message', 'None')}"""
        self.repo_status.setPlainText(status_text)
    
    def commit_changes(self):
        message, ok = QLineEdit().text(), True  # Simplified for demo
        if ok and message:
            commit_hash = self.repo_manager.commit_changes(message, self.current_build_id)
            if commit_hash:
                QMessageBox.information(self, "Success", f"Changes committed: {commit_hash[:8]}")
                self.update_repo_status()
    
    def on_stage_start(self, data):
        print(f"Stage started: {data['stage']}")
    
    def on_stage_complete(self, data):
        print(f"Stage completed: {data['stage']} - {data['status']}")
    
    def on_build_complete(self, data):
        print(f"Build completed: {data['build_id']} - {data['status']}")
        self.monitor_thread.stop()
        self.start_build_btn.setEnabled(True)
        self.cancel_build_btn.setEnabled(False)
        self.load_build_history()
    
    def on_build_error(self, data):
        print(f"Build error: {data.get('error', 'Unknown error')}")
        self.monitor_thread.stop()
        self.start_build_btn.setEnabled(True)
        self.cancel_build_btn.setEnabled(False)

def main():
    app = QApplication(sys.argv)
    window = LFSMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()