from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import os
from datetime import datetime
from typing import Dict, List

class GitCommitGraphWidget(QWidget):
    """Visual commit graph similar to git log --graph"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.commits = []
        self.setMinimumHeight(400)
    
    def set_commits(self, commits: List[Dict]):
        self.commits = commits
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if not self.commits:
            return
        
        # Draw commit graph
        y_offset = 20
        line_height = 25
        
        for i, commit in enumerate(self.commits):
            y = y_offset + i * line_height
            
            # Draw commit dot
            painter.setBrush(QBrush(QColor(100, 150, 200)))
            painter.drawEllipse(10, y, 8, 8)
            
            # Draw branch lines
            if i < len(self.commits) - 1:
                painter.setPen(QPen(QColor(150, 150, 150), 1))
                painter.drawLine(14, y + 8, 14, y + line_height)
            
            # Draw commit info
            painter.setPen(QPen(QColor(0, 0, 0)))
            font = painter.font()
            font.setPointSize(9)
            painter.setFont(font)
            
            text = f"{commit['short_hash']} {commit['message'][:60]}"
            if len(commit['message']) > 60:
                text += "..."
            
            painter.drawText(25, y + 6, text)
            
            # Draw author and date
            font.setPointSize(8)
            painter.setFont(font)
            painter.setPen(QPen(QColor(100, 100, 100)))
            author_text = f"{commit['author']} - {commit['date'].strftime('%Y-%m-%d %H:%M')}"
            painter.drawText(25, y + 18, author_text)

class GitStatusWidget(QWidget):
    """Git status display with file staging"""
    
    file_staged = pyqtSignal(str)
    file_unstaged = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Status sections
        self.staged_list = QListWidget()
        self.staged_list.setMaximumHeight(150)
        self.staged_list.itemDoubleClicked.connect(self.unstage_file)
        
        self.modified_list = QListWidget()
        self.modified_list.setMaximumHeight(150)
        self.modified_list.itemDoubleClicked.connect(self.stage_file)
        
        self.untracked_list = QListWidget()
        self.untracked_list.setMaximumHeight(150)
        self.untracked_list.itemDoubleClicked.connect(self.stage_file)
        
        # Add sections with labels
        layout.addWidget(QLabel("Staged Changes (double-click to unstage):"))
        layout.addWidget(self.staged_list)
        
        layout.addWidget(QLabel("Modified Files (double-click to stage):"))
        layout.addWidget(self.modified_list)
        
        layout.addWidget(QLabel("Untracked Files (double-click to stage):"))
        layout.addWidget(self.untracked_list)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        stage_all_btn = QPushButton("Stage All")
        stage_all_btn.clicked.connect(self.stage_all)
        
        unstage_all_btn = QPushButton("Unstage All")
        unstage_all_btn.clicked.connect(self.unstage_all)
        
        button_layout.addWidget(stage_all_btn)
        button_layout.addWidget(unstage_all_btn)
        layout.addLayout(button_layout)
    
    def update_status(self, status: Dict):
        self.staged_list.clear()
        self.modified_list.clear()
        self.untracked_list.clear()
        
        for file in status.get('staged', []):
            item = QListWidgetItem(f"✓ {file}")
            item.setForeground(QColor(0, 150, 0))
            self.staged_list.addItem(item)
        
        for file in status.get('modified', []):
            item = QListWidgetItem(f"M {file}")
            item.setForeground(QColor(200, 100, 0))
            self.modified_list.addItem(item)
        
        for file in status.get('untracked', []):
            item = QListWidgetItem(f"? {file}")
            item.setForeground(QColor(150, 150, 150))
            self.untracked_list.addItem(item)
    
    def stage_file(self, item):
        file_path = item.text()[2:]  # Remove status prefix
        self.file_staged.emit(file_path)
    
    def unstage_file(self, item):
        file_path = item.text()[2:]  # Remove status prefix
        self.file_unstaged.emit(file_path)
    
    def stage_all(self):
        for i in range(self.modified_list.count()):
            file_path = self.modified_list.item(i).text()[2:]
            self.file_staged.emit(file_path)
        
        for i in range(self.untracked_list.count()):
            file_path = self.untracked_list.item(i).text()[2:]
            self.file_staged.emit(file_path)
    
    def unstage_all(self):
        for i in range(self.staged_list.count()):
            file_path = self.staged_list.item(i).text()[2:]
            self.file_unstaged.emit(file_path)

class GitBranchWidget(QWidget):
    """Branch management interface"""
    
    branch_switched = pyqtSignal(str)
    branch_created = pyqtSignal(str, str)
    branch_deleted = pyqtSignal(str)
    branch_merged = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Current branch display
        self.current_branch_label = QLabel("Current Branch: main")
        self.current_branch_label.setStyleSheet("font-weight: bold; color: green;")
        layout.addWidget(self.current_branch_label)
        
        # Branch list
        self.branch_list = QListWidget()
        self.branch_list.itemDoubleClicked.connect(self.switch_branch)
        layout.addWidget(QLabel("Branches (double-click to switch):"))
        layout.addWidget(self.branch_list)
        
        # Branch actions
        button_layout = QHBoxLayout()
        
        create_btn = QPushButton("Create Branch")
        create_btn.clicked.connect(self.create_branch)
        
        delete_btn = QPushButton("Delete Branch")
        delete_btn.clicked.connect(self.delete_branch)
        
        merge_btn = QPushButton("Merge Branch")
        merge_btn.clicked.connect(self.merge_branch)
        
        button_layout.addWidget(create_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(merge_btn)
        layout.addLayout(button_layout)
    
    def update_branches(self, branches: List[str], current: str):
        self.current_branch_label.setText(f"Current Branch: {current}")
        
        self.branch_list.clear()
        for branch in branches:
            item = QListWidgetItem(branch)
            if branch == current:
                item.setForeground(QColor(0, 150, 0))
                item.setText(f"* {branch}")
            self.branch_list.addItem(item)
    
    def switch_branch(self, item):
        branch_name = item.text().replace('* ', '')
        self.branch_switched.emit(branch_name)
    
    def create_branch(self):
        name, ok = QInputDialog.getText(self, 'Create Branch', 'Branch name:')
        if ok and name:
            from_branch, ok2 = QInputDialog.getText(self, 'Create Branch', 'From branch (empty for current):')
            if ok2:
                self.branch_created.emit(name, from_branch)
    
    def delete_branch(self):
        current_item = self.branch_list.currentItem()
        if current_item:
            branch_name = current_item.text().replace('* ', '')
            reply = QMessageBox.question(self, 'Delete Branch', 
                                       f'Delete branch "{branch_name}"?',
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.branch_deleted.emit(branch_name)
    
    def merge_branch(self):
        current_item = self.branch_list.currentItem()
        if current_item:
            branch_name = current_item.text().replace('* ', '')
            reply = QMessageBox.question(self, 'Merge Branch', 
                                       f'Merge branch "{branch_name}" into current branch?',
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.branch_merged.emit(branch_name)

class GitDiffViewer(QWidget):
    """Diff viewer with syntax highlighting"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.diff_text = QTextEdit()
        self.diff_text.setFont(QFont("Courier", 10))
        self.diff_text.setReadOnly(True)
        layout.addWidget(self.diff_text)
    
    def show_diff(self, diff_text: str):
        self.diff_text.clear()
        
        # Simple syntax highlighting for diff
        cursor = self.diff_text.textCursor()
        
        for line in diff_text.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                cursor.insertText(line + '\n')
                # Color added lines green
                format = QTextCharFormat()
                format.setForeground(QColor(0, 150, 0))
                cursor.select(QTextCursor.LineUnderCursor)
                cursor.mergeCharFormat(format)
                cursor.movePosition(QTextCursor.End)
            elif line.startswith('-') and not line.startswith('---'):
                cursor.insertText(line + '\n')
                # Color removed lines red
                format = QTextCharFormat()
                format.setForeground(QColor(200, 0, 0))
                cursor.select(QTextCursor.LineUnderCursor)
                cursor.mergeCharFormat(format)
                cursor.movePosition(QTextCursor.End)
            elif line.startswith('@@'):
                cursor.insertText(line + '\n')
                # Color hunk headers blue
                format = QTextCharFormat()
                format.setForeground(QColor(0, 0, 200))
                cursor.select(QTextCursor.LineUnderCursor)
                cursor.mergeCharFormat(format)
                cursor.movePosition(QTextCursor.End)
            else:
                cursor.insertText(line + '\n')

class GitStashWidget(QWidget):
    """Stash management interface"""
    
    stash_applied = pyqtSignal(str)
    stash_dropped = pyqtSignal(str)
    stash_created = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Stash list
        self.stash_list = QListWidget()
        layout.addWidget(QLabel("Stashes:"))
        layout.addWidget(self.stash_list)
        
        # Stash actions
        button_layout = QHBoxLayout()
        
        create_btn = QPushButton("Create Stash")
        create_btn.clicked.connect(self.create_stash)
        
        apply_btn = QPushButton("Apply Stash")
        apply_btn.clicked.connect(self.apply_stash)
        
        pop_btn = QPushButton("Pop Stash")
        pop_btn.clicked.connect(self.pop_stash)
        
        drop_btn = QPushButton("Drop Stash")
        drop_btn.clicked.connect(self.drop_stash)
        
        button_layout.addWidget(create_btn)
        button_layout.addWidget(apply_btn)
        button_layout.addWidget(pop_btn)
        button_layout.addWidget(drop_btn)
        layout.addLayout(button_layout)
    
    def update_stashes(self, stashes: List[Dict]):
        self.stash_list.clear()
        for stash in stashes:
            item = QListWidgetItem(f"{stash['id']}: {stash['message']}")
            self.stash_list.addItem(item)
    
    def create_stash(self):
        message, ok = QInputDialog.getText(self, 'Create Stash', 'Stash message (optional):')
        if ok:
            self.stash_created.emit(message)
    
    def apply_stash(self):
        current_item = self.stash_list.currentItem()
        if current_item:
            stash_id = current_item.text().split(':')[0]
            self.stash_applied.emit(stash_id)
    
    def pop_stash(self):
        current_item = self.stash_list.currentItem()
        if current_item:
            stash_id = current_item.text().split(':')[0]
            self.stash_applied.emit(stash_id)  # Pop is apply + drop
            self.stash_dropped.emit(stash_id)
    
    def drop_stash(self):
        current_item = self.stash_list.currentItem()
        if current_item:
            stash_id = current_item.text().split(':')[0]
            reply = QMessageBox.question(self, 'Drop Stash', 
                                       f'Drop stash "{stash_id}"?',
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.stash_dropped.emit(stash_id)

class GitTagWidget(QWidget):
    """Tag management interface"""
    
    tag_created = pyqtSignal(str, str)
    tag_deleted = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tag list
        self.tag_list = QListWidget()
        layout.addWidget(QLabel("Tags:"))
        layout.addWidget(self.tag_list)
        
        # Tag actions
        button_layout = QHBoxLayout()
        
        create_btn = QPushButton("Create Tag")
        create_btn.clicked.connect(self.create_tag)
        
        delete_btn = QPushButton("Delete Tag")
        delete_btn.clicked.connect(self.delete_tag)
        
        button_layout.addWidget(create_btn)
        button_layout.addWidget(delete_btn)
        layout.addLayout(button_layout)
    
    def update_tags(self, tags: List[Dict]):
        self.tag_list.clear()
        for tag in tags:
            text = f"{tag['name']} ({tag['date'].strftime('%Y-%m-%d')})"
            if 'message' in tag:
                text += f" - {tag['message'][:50]}"
            item = QListWidgetItem(text)
            self.tag_list.addItem(item)
    
    def create_tag(self):
        name, ok = QInputDialog.getText(self, 'Create Tag', 'Tag name:')
        if ok and name:
            message, ok2 = QInputDialog.getText(self, 'Create Tag', 'Tag message (optional):')
            if ok2:
                self.tag_created.emit(name, message)
    
    def delete_tag(self):
        current_item = self.tag_list.currentItem()
        if current_item:
            tag_name = current_item.text().split(' ')[0]
            reply = QMessageBox.question(self, 'Delete Tag', 
                                       f'Delete tag "{tag_name}"?',
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.tag_deleted.emit(tag_name)

class GitMainInterface(QWidget):
    """Main Git interface combining all components"""
    
    def __init__(self, repo_manager, parent=None):
        super().__init__(parent)
        self.repo_manager = repo_manager
        self.setup_ui()
        self.refresh_all()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget for different git views
        self.tab_widget = QTabWidget()
        
        # Status and Staging tab
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        
        self.status_widget = GitStatusWidget()
        self.status_widget.file_staged.connect(self.stage_file)
        self.status_widget.file_unstaged.connect(self.unstage_file)
        
        # Commit area
        commit_widget = QWidget()
        commit_layout = QVBoxLayout(commit_widget)
        
        commit_layout.addWidget(QLabel("Commit Message:"))
        self.commit_message = QTextEdit()
        self.commit_message.setMaximumHeight(100)
        commit_layout.addWidget(self.commit_message)
        
        commit_button_layout = QHBoxLayout()
        commit_btn = QPushButton("Commit")
        commit_btn.clicked.connect(self.commit_changes)
        
        amend_btn = QPushButton("Amend Last Commit")
        amend_btn.clicked.connect(self.amend_commit)
        
        commit_button_layout.addWidget(commit_btn)
        commit_button_layout.addWidget(amend_btn)
        commit_layout.addLayout(commit_button_layout)
        
        status_layout.addWidget(self.status_widget, 2)
        status_layout.addWidget(commit_widget, 1)
        
        self.tab_widget.addTab(status_widget, "Status & Commit")
        
        # History tab with commit graph
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        
        # Commit graph
        self.commit_graph = GitCommitGraphWidget()
        history_layout.addWidget(QLabel("Commit History:"))
        history_layout.addWidget(self.commit_graph)
        
        # Diff viewer
        self.diff_viewer = GitDiffViewer()
        history_layout.addWidget(QLabel("Diff:"))
        history_layout.addWidget(self.diff_viewer)
        
        self.tab_widget.addTab(history_widget, "History")
        
        # Branches tab
        self.branch_widget = GitBranchWidget()
        self.branch_widget.branch_switched.connect(self.switch_branch)
        self.branch_widget.branch_created.connect(self.create_branch)
        self.branch_widget.branch_deleted.connect(self.delete_branch)
        self.branch_widget.branch_merged.connect(self.merge_branch)
        
        self.tab_widget.addTab(self.branch_widget, "Branches")
        
        # Stash tab
        self.stash_widget = GitStashWidget()
        self.stash_widget.stash_created.connect(self.create_stash)
        self.stash_widget.stash_applied.connect(self.apply_stash)
        self.stash_widget.stash_dropped.connect(self.drop_stash)
        
        self.tab_widget.addTab(self.stash_widget, "Stash")
        
        # Tags tab
        self.tag_widget = GitTagWidget()
        self.tag_widget.tag_created.connect(self.create_tag)
        self.tag_widget.tag_deleted.connect(self.delete_tag)
        
        self.tab_widget.addTab(self.tag_widget, "Tags")
        
        # Repository Files tab (from legacy repository tab)
        repo_files_widget = QWidget()
        repo_files_layout = QVBoxLayout(repo_files_widget)
        
        # Repository summary
        self.repo_summary_label = QLabel("")
        self.repo_summary_label.setStyleSheet("font-weight: bold; padding: 5px; background-color: #f0f0f0; border: 1px solid #ccc;")
        repo_files_layout.addWidget(self.repo_summary_label)
        
        # Repository files
        repo_files_layout.addWidget(QLabel("Repository Files:"))
        self.repo_files_tree = QTreeWidget()
        self.repo_files_tree.setHeaderLabels(["File", "Size", "Type", "Date"])
        self.repo_files_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.repo_files_tree.customContextMenuRequested.connect(self.show_repo_file_context_menu)
        repo_files_layout.addWidget(self.repo_files_tree)
        
        # Repository actions
        repo_actions = QHBoxLayout()
        
        refresh_repo_btn = QPushButton("Refresh Files")
        refresh_repo_btn.clicked.connect(self.update_repo_files)
        repo_actions.addWidget(refresh_repo_btn)
        
        missing_packages_btn = QPushButton("Show Missing Packages")
        missing_packages_btn.clicked.connect(self.show_missing_packages)
        repo_actions.addWidget(missing_packages_btn)
        
        repo_files_layout.addLayout(repo_actions)
        
        self.tab_widget.addTab(repo_files_widget, "Repository Files")
        
        layout.addWidget(self.tab_widget)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh All")
        refresh_btn.clicked.connect(self.refresh_all)
        layout.addWidget(refresh_btn)
        
        # Initialize repository files
        self.update_repo_files()
    
    def refresh_all(self):
        """Refresh all git information"""
        try:
            # Update status
            status = self.repo_manager.get_detailed_status()
            self.status_widget.update_status(status)
            
            # Update branches
            repo_status = self.repo_manager.get_repository_status()
            self.branch_widget.update_branches(
                repo_status.get('branches', []),
                repo_status.get('current_branch', 'main')
            )
            
            # Update commit history
            commits = self.repo_manager.get_commit_graph(50)
            self.commit_graph.set_commits(commits)
            
            # Update stashes
            stashes = self.repo_manager.list_stashes()
            self.stash_widget.update_stashes(stashes)
            
            # Update tags
            tags = self.repo_manager.list_tags()
            self.tag_widget.update_tags(tags)
            
            # Update repository files
            self.update_repo_files()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to refresh git data: {e}")
    
    def stage_file(self, file_path: str):
        if self.repo_manager.stage_file(file_path):
            self.refresh_all()
        else:
            QMessageBox.warning(self, "Error", f"Failed to stage {file_path}")
    
    def unstage_file(self, file_path: str):
        if self.repo_manager.unstage_file(file_path):
            self.refresh_all()
        else:
            QMessageBox.warning(self, "Error", f"Failed to unstage {file_path}")
    
    def commit_changes(self):
        message = self.commit_message.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Error", "Please enter a commit message")
            return
        
        commit_hash = self.repo_manager.commit_changes(message)
        if commit_hash:
            self.commit_message.clear()
            self.refresh_all()
            QMessageBox.information(self, "Success", f"Committed: {commit_hash[:8]}")
        else:
            QMessageBox.warning(self, "Error", "Failed to commit changes")
    
    def amend_commit(self):
        message = self.commit_message.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Error", "Please enter a commit message")
            return
        
        commit_hash = self.repo_manager.commit_changes(message, amend=True)
        if commit_hash:
            self.commit_message.clear()
            self.refresh_all()
            QMessageBox.information(self, "Success", f"Amended commit: {commit_hash[:8]}")
        else:
            QMessageBox.warning(self, "Error", "Failed to amend commit")
    
    def switch_branch(self, branch_name: str):
        if self.repo_manager.switch_branch(branch_name):
            self.refresh_all()
            QMessageBox.information(self, "Success", f"Switched to branch: {branch_name}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to switch to branch: {branch_name}")
    
    def create_branch(self, name: str, from_branch: str):
        from_branch = from_branch if from_branch else None
        if self.repo_manager.create_branch(name, from_branch):
            self.refresh_all()
            QMessageBox.information(self, "Success", f"Created branch: {name}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to create branch: {name}")
    
    def delete_branch(self, branch_name: str):
        if self.repo_manager.delete_branch(branch_name):
            self.refresh_all()
            QMessageBox.information(self, "Success", f"Deleted branch: {branch_name}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to delete branch: {branch_name}")
    
    def merge_branch(self, branch_name: str):
        success, message = self.repo_manager.merge_branch(branch_name)
        if success:
            self.refresh_all()
            QMessageBox.information(self, "Success", f"Merged branch: {branch_name}")
        else:
            QMessageBox.warning(self, "Merge Error", message)
    
    def create_stash(self, message: str):
        stash_name = self.repo_manager.stash_changes(message)
        if stash_name:
            self.refresh_all()
            QMessageBox.information(self, "Success", f"Created stash: {stash_name}")
        else:
            QMessageBox.warning(self, "Error", "Failed to create stash")
    
    def apply_stash(self, stash_id: str):
        if self.repo_manager.apply_stash(stash_id):
            self.refresh_all()
            QMessageBox.information(self, "Success", f"Applied stash: {stash_id}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to apply stash: {stash_id}")
    
    def drop_stash(self, stash_id: str):
        if self.repo_manager.drop_stash(stash_id):
            self.refresh_all()
            QMessageBox.information(self, "Success", f"Dropped stash: {stash_id}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to drop stash: {stash_id}")
    
    def create_tag(self, name: str, message: str):
        if self.repo_manager.create_tag(name, message):
            self.refresh_all()
            QMessageBox.information(self, "Success", f"Created tag: {name}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to create tag: {name}")
    
    def delete_tag(self, tag_name: str):
        if self.repo_manager.delete_tag(tag_name):
            self.refresh_all()
            QMessageBox.information(self, "Success", f"Deleted tag: {tag_name}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to delete tag: {tag_name}")
    
    def update_repo_files(self):
        """Update repository files display and summary"""
        self.repo_files_tree.clear()
        
        try:
            # Get build engine from parent window
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'build_engine'):
                parent_window = parent_window.parent()
            
            if not parent_window:
                self.repo_summary_label.setText("📦 Repository status unavailable")
                return
            
            # Get package status
            all_packages = parent_window.build_engine.downloader.get_package_list()
            cached_packages = parent_window.build_engine.downloader.get_cached_packages() or []
            
            # Create lookup for cached packages
            cached_lookup = {pkg['package_name']: pkg for pkg in cached_packages}
            
            # Analyze package status
            total_packages = len(all_packages)
            cached_count = len(cached_packages)
            missing_packages = []
            
            for pkg in all_packages:
                if pkg['name'] not in cached_lookup:
                    missing_packages.append(pkg['name'])
            
            missing_count = len(missing_packages)
            
            # Update summary
            summary_text = f"📦 Packages: {cached_count}/{total_packages} cached"
            if missing_count > 0:
                summary_text += f" | ⚠ {missing_count} missing"
            
            self.repo_summary_label.setText(summary_text)
            
            # Show missing packages in tooltip if any
            if missing_packages:
                missing_list = ", ".join(missing_packages[:10])  # Show first 10
                if len(missing_packages) > 10:
                    missing_list += f" and {len(missing_packages) - 10} more..."
                self.repo_summary_label.setToolTip(f"Missing packages: {missing_list}")
            else:
                self.repo_summary_label.setToolTip("All required packages are cached")
            
            sources_dir = self.repo_manager.repo_path / "sources"
            if not sources_dir.exists():
                return
            
            # Add cached packages to tree
            for pkg in cached_packages:
                filename = pkg['url'].split('/')[-1] if 'url' in pkg else f"{pkg['package_name']}-{pkg['version']}"
                file_path = sources_dir / filename
                
                if file_path.exists():
                    size_mb = pkg.get('file_size', 0) / (1024 * 1024)
                    date_str = pkg.get('downloaded_at', 'Unknown')[:19] if pkg.get('downloaded_at') else 'Unknown'
                    
                    item = QTreeWidgetItem([
                        filename,
                        f"{size_mb:.1f} MB",
                        "Package",
                        date_str
                    ])
                    item.setData(0, Qt.UserRole, str(file_path))
                    self.repo_files_tree.addTopLevelItem(item)
            
            # Add other files in sources directory
            for file_path in sources_dir.iterdir():
                if file_path.is_file() and not file_path.name.endswith('.info'):
                    # Check if already added as cached package
                    already_added = False
                    for i in range(self.repo_files_tree.topLevelItemCount()):
                        if self.repo_files_tree.topLevelItem(i).text(0) == file_path.name:
                            already_added = True
                            break
                    
                    if not already_added:
                        from datetime import datetime
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        date_str = datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        
                        item = QTreeWidgetItem([
                            file_path.name,
                            f"{size_mb:.1f} MB",
                            "File",
                            date_str
                        ])
                        item.setData(0, Qt.UserRole, str(file_path))
                        self.repo_files_tree.addTopLevelItem(item)
            
            # Sort by filename
            self.repo_files_tree.sortItems(0, Qt.AscendingOrder)
            
        except Exception as e:
            print(f"Error updating repo files: {e}")
            self.repo_summary_label.setText("📦 Repository status unavailable")
    
    def show_repo_file_context_menu(self, position):
        """Show context menu for repository files"""
        item = self.repo_files_tree.itemAt(position)
        if item:
            menu = QMenu()
            
            open_action = menu.addAction("Open File Location")
            open_action.triggered.connect(lambda: self.open_file_location(item))
            
            verify_action = menu.addAction("Verify Checksum")
            verify_action.triggered.connect(lambda: self.verify_file_checksum(item))
            
            menu.addSeparator()
            
            missing_action = menu.addAction("Show Missing Packages")
            missing_action.triggered.connect(self.show_missing_packages)
            
            menu.exec_(self.repo_files_tree.mapToGlobal(position))
    
    def open_file_location(self, item):
        """Open file location in system file manager"""
        file_path = item.data(0, Qt.UserRole)
        if file_path:
            import subprocess
            import os
            try:
                # Open directory containing the file
                subprocess.run(['xdg-open', os.path.dirname(file_path)])
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not open file location: {str(e)}")
    
    def verify_file_checksum(self, item):
        """Verify file checksum against known packages"""
        filename = item.text(0)
        file_path = item.data(0, Qt.UserRole)
        
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Error", "File not found")
            return
        
        try:
            # Get build engine from parent window
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'build_engine'):
                parent_window = parent_window.parent()
            
            if not parent_window:
                QMessageBox.warning(self, "Error", "Cannot access package information")
                return
            
            # Find matching package in our list
            packages = parent_window.build_engine.downloader.get_package_list()
            matching_package = None
            
            for pkg in packages:
                pkg_filename = pkg['url'].split('/')[-1]
                if pkg_filename == filename:
                    matching_package = pkg
                    break
            
            if matching_package:
                # Verify checksum
                from pathlib import Path
                actual_md5 = parent_window.build_engine.downloader.get_file_md5(Path(file_path))
                expected_md5 = matching_package['md5']
                
                if actual_md5 == expected_md5:
                    QMessageBox.information(self, "Checksum Verification", 
                                           f"✓ File verified successfully\n\n"
                                           f"File: {filename}\n"
                                           f"MD5: {actual_md5}")
                else:
                    QMessageBox.warning(self, "Checksum Verification", 
                                       f"✗ Checksum mismatch!\n\n"
                                       f"File: {filename}\n"
                                       f"Expected: {expected_md5}\n"
                                       f"Actual: {actual_md5}")
            else:
                # Just show the file's checksum
                from pathlib import Path
                actual_md5 = parent_window.build_engine.downloader.get_file_md5(Path(file_path))
                QMessageBox.information(self, "File Checksum", 
                                       f"File: {filename}\n"
                                       f"MD5: {actual_md5}\n\n"
                                       f"(No matching package found for verification)")
                
        except Exception as e:
            QMessageBox.critical(self, "Verification Error", f"Failed to verify checksum: {str(e)}")
    
    def show_missing_packages(self):
        """Show detailed missing packages information"""
        try:
            # Get build engine from parent window
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'build_engine'):
                parent_window = parent_window.parent()
            
            if not parent_window:
                QMessageBox.warning(self, "Error", "Cannot access package information")
                return
            
            all_packages = parent_window.build_engine.downloader.get_package_list()
            cached_packages = parent_window.build_engine.downloader.get_cached_packages() or []
            
            # Create lookup for cached packages
            cached_lookup = {pkg['package_name']: pkg for pkg in cached_packages}
            
            missing_packages = []
            for pkg in all_packages:
                if pkg['name'] not in cached_lookup:
                    missing_packages.append(pkg)
            
            if not missing_packages:
                QMessageBox.information(self, "Missing Packages", "✅ All required packages are cached!")
                return
            
            # Create detailed missing packages dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Missing Packages")
            dialog.resize(600, 400)
            
            layout = QVBoxLayout()
            
            # Header
            header_label = QLabel(f"⚠ {len(missing_packages)} packages still need to be downloaded:")
            header_label.setStyleSheet("font-weight: bold; color: #d63384;")
            layout.addWidget(header_label)
            
            # Missing packages table
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Package", "Version", "URL"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.setRowCount(len(missing_packages))
            
            for i, pkg in enumerate(missing_packages):
                table.setItem(i, 0, QTableWidgetItem(pkg['name']))
                table.setItem(i, 1, QTableWidgetItem(pkg['version']))
                url_item = QTableWidgetItem(pkg['url'])
                url_item.setToolTip(pkg['url'])
                table.setItem(i, 2, url_item)
            
            layout.addWidget(table)
            
            # Action buttons
            button_layout = QHBoxLayout()
            
            download_btn = QPushButton("Download Missing")
            download_btn.clicked.connect(lambda: self.download_missing_from_dialog(dialog, parent_window))
            button_layout.addWidget(download_btn)
            
            export_btn = QPushButton("Export URLs")
            export_btn.clicked.connect(lambda: self.export_missing_urls(missing_packages))
            button_layout.addWidget(export_btn)
            
            button_layout.addStretch()
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get missing packages: {str(e)}")
    
    def download_missing_from_dialog(self, dialog, parent_window):
        """Start downloading missing packages from the dialog"""
        dialog.accept()
        if hasattr(parent_window, 'download_sources'):
            parent_window.download_sources()
    
    def export_missing_urls(self, missing_packages):
        """Export missing package URLs to a file"""
        filename, _ = QFileDialog.getSaveFileName(self, "Save Missing Package URLs", "missing-packages.txt", "Text Files (*.txt)")
        if filename:
            try:
                from datetime import datetime
                with open(filename, 'w') as f:
                    f.write(f"# Missing LFS Packages ({len(missing_packages)} packages)\n")
                    f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    for pkg in missing_packages:
                        f.write(f"# {pkg['name']} {pkg['version']}\n")
                        f.write(f"{pkg['url']}\n\n")
                
                QMessageBox.information(self, "Export Complete", f"Missing package URLs saved to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save URLs: {str(e)}")