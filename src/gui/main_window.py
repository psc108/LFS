import sys
import os
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem,
                            QSplitter, QTabWidget, QLabel, QLineEdit, QComboBox,
                            QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
                            QMessageBox, QFileDialog, QDialog, QDialogButtonBox, QMenu, QSpinBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor
from datetime import datetime
from typing import Dict, List

from ..database.db_manager import DatabaseManager
from ..build.build_engine import BuildEngine
from ..repository.repo_manager import RepositoryManager
from ..config.settings_manager import SettingsManager
from .build_details_dialog import BuildDetailsDialog
from .kernel_config_dialog import KernelConfigDialog

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

class DownloadThread(QThread):
    progress = pyqtSignal(int, int, str)  # current, total, package_name
    finished = pyqtSignal(dict)  # results
    error = pyqtSignal(str)  # error message
    
    def __init__(self, build_engine, download_id):
        super().__init__()
        self.build_engine = build_engine
        self.download_id = download_id
        self.cancelled = False
    
    def cancel(self):
        self.cancelled = True
        self.terminate()
    
    def run(self):
        try:
            if self.cancelled:
                return
            results = self.build_engine.download_lfs_sources(self.download_id)
            if not self.cancelled:
                self.finished.emit(results)
        except Exception as e:
            if not self.cancelled:
                self.error.emit(str(e))

class SettingsDialog(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings = settings_manager
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout()
        
        # Repository path
        layout.addWidget(QLabel("Repository Path:"))
        repo_layout = QHBoxLayout()
        self.repo_path_edit = QLineEdit(self.settings.get_repository_path())
        self.repo_path_edit.textChanged.connect(self.update_repo_space_info)
        self.repo_browse_btn = QPushButton("Browse")
        self.repo_browse_btn.clicked.connect(self.browse_repo_path)
        self.repo_removable_btn = QPushButton("Removable Media")
        self.repo_removable_btn.clicked.connect(self.select_repo_removable)
        repo_layout.addWidget(self.repo_path_edit)
        repo_layout.addWidget(self.repo_browse_btn)
        repo_layout.addWidget(self.repo_removable_btn)
        layout.addLayout(repo_layout)
        
        # Repository space info
        self.repo_space_label = QLabel("")
        self.repo_space_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.repo_space_label)
        
        # LFS build path
        layout.addWidget(QLabel("LFS Build Path:"))
        lfs_layout = QHBoxLayout()
        self.lfs_path_edit = QLineEdit(self.settings.get_lfs_build_path())
        self.lfs_path_edit.textChanged.connect(self.update_lfs_space_info)
        self.lfs_browse_btn = QPushButton("Browse")
        self.lfs_browse_btn.clicked.connect(self.browse_lfs_path)
        self.lfs_removable_btn = QPushButton("Removable Media")
        self.lfs_removable_btn.clicked.connect(self.select_lfs_removable)
        lfs_layout.addWidget(self.lfs_path_edit)
        lfs_layout.addWidget(self.lfs_browse_btn)
        lfs_layout.addWidget(self.lfs_removable_btn)
        layout.addLayout(lfs_layout)
        
        # LFS space info
        self.lfs_space_label = QLabel("")
        self.lfs_space_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.lfs_space_label)
        
        # Parallel jobs
        layout.addWidget(QLabel("Max Parallel Jobs:"))
        self.jobs_edit = QLineEdit(str(self.settings.get("max_parallel_jobs", 1)))
        layout.addWidget(self.jobs_edit)
        
        # Auto backup
        self.auto_backup_check = QPushButton("Auto Backup")
        self.auto_backup_check.setCheckable(True)
        self.auto_backup_check.setChecked(self.settings.get("auto_backup", True))
        layout.addWidget(self.auto_backup_check)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
        # Update space info on startup
        self.update_repo_space_info()
        self.update_lfs_space_info()
    
    def get_removable_media(self):
        """Detect removable media devices"""
        removable_devices = []
        
        # Check /media and /mnt for mounted devices
        for mount_point in ['/media', '/mnt']:
            if os.path.exists(mount_point):
                for user_dir in os.listdir(mount_point):
                    user_path = os.path.join(mount_point, user_dir)
                    if os.path.isdir(user_path):
                        for device in os.listdir(user_path):
                            device_path = os.path.join(user_path, device)
                            if os.path.ismount(device_path):
                                removable_devices.append(device_path)
        
        # Also check direct /mnt mounts
        if os.path.exists('/mnt'):
            for device in os.listdir('/mnt'):
                device_path = os.path.join('/mnt', device)
                if os.path.ismount(device_path):
                    removable_devices.append(device_path)
        
        return removable_devices
    
    def get_disk_usage(self, path):
        """Get disk usage information for a path"""
        try:
            if os.path.exists(path):
                total, used, free = shutil.disk_usage(path)
                return {
                    'total': total,
                    'used': used,
                    'free': free,
                    'total_gb': total / (1024**3),
                    'used_gb': used / (1024**3),
                    'free_gb': free / (1024**3),
                    'used_percent': (used / total) * 100 if total > 0 else 0
                }
        except:
            pass
        return None
    
    def format_space_info(self, path):
        """Format disk space information for display"""
        usage = self.get_disk_usage(path)
        if usage:
            return f"💾 {usage['free_gb']:.1f} GB free of {usage['total_gb']:.1f} GB ({usage['used_percent']:.1f}% used)"
        return "💾 Path not accessible"
    
    def update_repo_space_info(self):
        """Update repository path space information"""
        path = self.repo_path_edit.text()
        if path:
            self.repo_space_label.setText(self.format_space_info(path))
        else:
            self.repo_space_label.setText("")
    
    def update_lfs_space_info(self):
        """Update LFS build path space information"""
        path = self.lfs_path_edit.text()
        if path:
            self.lfs_space_label.setText(self.format_space_info(path))
        else:
            self.lfs_space_label.setText("")
    
    def select_repo_removable(self):
        """Show removable media selection for repository"""
        devices = self.get_removable_media()
        if not devices:
            QMessageBox.information(self, "No Removable Media", "No removable media devices detected.")
            return
        
        # Create selection dialog
        from PyQt5.QtWidgets import QListWidget, QListWidgetItem
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Removable Media")
        dialog.resize(500, 300)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select removable media for repository storage:"))
        
        device_list = QListWidget()
        for device in devices:
            usage = self.get_disk_usage(device)
            if usage:
                item_text = f"{device} - {usage['free_gb']:.1f} GB free ({usage['total_gb']:.1f} GB total)"
            else:
                item_text = device
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, device)
            device_list.addItem(item)
        
        layout.addWidget(device_list)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            current_item = device_list.currentItem()
            if current_item:
                selected_path = current_item.data(Qt.UserRole)
                self.repo_path_edit.setText(selected_path)
    
    def select_lfs_removable(self):
        """Show removable media selection for LFS build"""
        devices = self.get_removable_media()
        if not devices:
            QMessageBox.information(self, "No Removable Media", "No removable media devices detected.")
            return
        
        # Create selection dialog
        from PyQt5.QtWidgets import QListWidget, QListWidgetItem
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Removable Media")
        dialog.resize(500, 300)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select removable media for LFS build storage:"))
        
        device_list = QListWidget()
        for device in devices:
            usage = self.get_disk_usage(device)
            if usage:
                item_text = f"{device} - {usage['free_gb']:.1f} GB free ({usage['total_gb']:.1f} GB total)"
            else:
                item_text = device
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, device)
            device_list.addItem(item)
        
        layout.addWidget(device_list)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            current_item = device_list.currentItem()
            if current_item:
                selected_path = current_item.data(Qt.UserRole)
                self.lfs_path_edit.setText(selected_path)
    
    def browse_repo_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Repository Directory")
        if path:
            self.repo_path_edit.setText(path)
    
    def browse_lfs_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select LFS Build Directory")
        if path:
            self.lfs_path_edit.setText(path)
    
    def save_settings(self):
        try:
            self.settings.set_repository_path(self.repo_path_edit.text())
            self.settings.set_lfs_build_path(self.lfs_path_edit.text())
            self.settings.set("max_parallel_jobs", int(self.jobs_edit.text()))
            self.settings.set("auto_backup", self.auto_backup_check.isChecked())
            self.accept()
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for parallel jobs.")

class PackageManagerDialog(QDialog):
    def __init__(self, downloader, parent=None):
        super().__init__(parent)
        self.downloader = downloader
        self.setWindowTitle("LFS Package Manager")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("LFS 12.0 Required Packages"))
        
        self.refresh_btn = QPushButton("Refresh Status")
        self.refresh_btn.clicked.connect(self.refresh_package_status)
        header_layout.addWidget(self.refresh_btn)
        
        self.download_missing_btn = QPushButton("Download Missing")
        self.download_missing_btn.clicked.connect(self.download_missing_packages)
        header_layout.addWidget(self.download_missing_btn)
        
        layout.addLayout(header_layout)
        
        # Package list
        self.package_table = QTableWidget()
        self.package_table.setColumnCount(6)
        self.package_table.setHorizontalHeaderLabels(["Package", "Version", "Status", "Size", "URL", "MD5"])
        self.package_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.package_table)
        
        # Status summary
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-weight: bold; padding: 10px;")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.export_list_btn = QPushButton("Export wget-list")
        self.export_list_btn.clicked.connect(self.export_wget_list)
        button_layout.addWidget(self.export_list_btn)
        
        self.export_md5_btn = QPushButton("Export md5sums")
        self.export_md5_btn.clicked.connect(self.export_md5sums)
        button_layout.addWidget(self.export_md5_btn)
        
        self.mirror_stats_btn = QPushButton("Mirror Stats")
        self.mirror_stats_btn.clicked.connect(self.show_mirror_stats)
        button_layout.addWidget(self.mirror_stats_btn)
        
        self.manage_mirrors_btn = QPushButton("Manage Mirrors")
        self.manage_mirrors_btn.clicked.connect(self.manage_mirrors)
        button_layout.addWidget(self.manage_mirrors_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Load initial data
        self.refresh_package_status()
    
    def refresh_package_status(self):
        """Refresh the package status display"""
        packages = self.downloader.get_package_list()
        cached_packages = self.downloader.get_cached_packages() or []
        
        # Create lookup for cached packages
        cached_lookup = {pkg['package_name']: pkg for pkg in cached_packages}
        
        self.package_table.setRowCount(len(packages))
        
        cached_count = 0
        missing_count = 0
        total_size = 0
        
        for i, package in enumerate(packages):
            # Package name
            self.package_table.setItem(i, 0, QTableWidgetItem(package['name']))
            
            # Version
            self.package_table.setItem(i, 1, QTableWidgetItem(package['version']))
            
            # Status
            if package['name'] in cached_lookup:
                status_item = QTableWidgetItem("✓ Cached")
                from PyQt5.QtGui import QColor
                status_item.setForeground(QColor(0, 128, 0))  # Green
                cached_count += 1
                size_mb = cached_lookup[package['name']]['file_size'] / (1024 * 1024)
                total_size += cached_lookup[package['name']]['file_size']
            else:
                status_item = QTableWidgetItem("⚠ Missing")
                from PyQt5.QtGui import QColor
                status_item.setForeground(QColor(255, 0, 0))  # Red
                missing_count += 1
                size_mb = 0  # Unknown size for missing packages
            
            self.package_table.setItem(i, 2, status_item)
            
            # Size
            if size_mb > 0:
                self.package_table.setItem(i, 3, QTableWidgetItem(f"{size_mb:.1f} MB"))
            else:
                self.package_table.setItem(i, 3, QTableWidgetItem("Unknown"))
            
            # URL
            url_item = QTableWidgetItem(package['url'])
            url_item.setToolTip(package['url'])  # Full URL in tooltip
            self.package_table.setItem(i, 4, url_item)
            
            # MD5
            self.package_table.setItem(i, 5, QTableWidgetItem(package['md5']))
        
        # Update status summary
        total_size_mb = total_size / (1024 * 1024)
        self.status_label.setText(
            f"📦 Total: {len(packages)} packages | "
            f"✓ Cached: {cached_count} | "
            f"⚠ Missing: {missing_count} | "
            f"💾 Cache Size: {total_size_mb:.1f} MB"
        )
        
        # Enable/disable download button
        self.download_missing_btn.setEnabled(missing_count > 0)
        self.download_missing_btn.setText(f"Download {missing_count} Missing Packages")
    
    def download_missing_packages(self):
        """Download all missing packages"""
        reply = QMessageBox.question(self, 'Download Missing Packages',
                                   'Download all missing packages to repository cache?',
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.Yes)
        
        if reply == QMessageBox.Yes:
            # Create a download ID for tracking
            download_id = f"pkg-mgr-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Create build record first
            success = self.parent().db.create_build(download_id, "download", 1)
            if not success:
                QMessageBox.critical(self, "Download Error", "Failed to create download tracking record")
                return
            
            # Start download in background
            self.download_thread = DownloadThread(self.parent().build_engine, download_id)
            self.download_thread.finished.connect(self.on_download_finished)
            self.download_thread.error.connect(self.on_download_error)
            
            # Update UI
            self.download_missing_btn.setEnabled(False)
            self.download_missing_btn.setText("Downloading...")
            
            self.download_thread.start()
    
    def on_download_finished(self, results):
        """Handle download completion"""
        cached_count = len(results.get('cached', []))
        download_count = len(results.get('success', []))
        failed_count = len(results.get('failed', []))
        
        if failed_count == 0:
            QMessageBox.information(self, "Download Complete",
                                   f"Successfully acquired all packages!\n\n"
                                   f"From cache: {cached_count}\n"
                                   f"Downloaded: {download_count}")
        else:
            QMessageBox.warning(self, "Download Incomplete",
                               f"Acquired {cached_count + download_count} packages.\n"
                               f"{failed_count} packages failed to download.")
        
        # Refresh the display
        self.refresh_package_status()
    
    def on_download_error(self, error_msg):
        """Handle download error"""
        QMessageBox.critical(self, "Download Error", f"Download failed: {error_msg}")
        self.download_missing_btn.setEnabled(True)
        self.download_missing_btn.setText("Download Missing")
    
    def export_wget_list(self):
        """Export wget-list file for manual downloads"""
        filename, _ = QFileDialog.getSaveFileName(self, "Save wget-list", "wget-list", "Text Files (*.txt)")
        if filename:
            try:
                packages = self.downloader.get_package_list()
                with open(filename, 'w') as f:
                    for package in packages:
                        f.write(f"{package['url']}\n")
                QMessageBox.information(self, "Export Complete", f"wget-list saved to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save wget-list: {str(e)}")
    
    def export_md5sums(self):
        """Export md5sums file for verification"""
        filename, _ = QFileDialog.getSaveFileName(self, "Save md5sums", "md5sums", "Text Files (*.txt)")
        if filename:
            try:
                packages = self.downloader.get_package_list()
                with open(filename, 'w') as f:
                    for package in packages:
                        package_filename = package['url'].split('/')[-1]
                        f.write(f"{package['md5']}  {package_filename}\n")
                QMessageBox.information(self, "Export Complete", f"md5sums saved to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save md5sums: {str(e)}")
    
    def show_mirror_stats(self):
        """Show mirror performance statistics"""
        stats = self.downloader.mirror_stats
        if not stats:
            QMessageBox.information(self, "Mirror Statistics", "No mirror statistics available yet.\nStatistics will be collected as packages are downloaded.")
            return
        
        # Create custom dialog with scrollable content
        dialog = QDialog(self)
        dialog.setWindowTitle("Mirror Performance Statistics")
        dialog.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Create scrollable text area
        text_widget = QTextEdit()
        text_widget.setReadOnly(True)
        text_widget.setFont(QFont("Courier", 9))
        
        stats_text = "Mirror Performance Statistics\n\n"
        
        # Sort mirrors by grade
        sorted_mirrors = sorted(stats.items(), key=lambda x: self.downloader.get_mirror_grade(x[0]), reverse=True)
        
        for domain, data in sorted_mirrors:
            grade = self.downloader.get_mirror_grade(domain)
            total_attempts = data['successes'] + data['failures']
            success_rate = (data['successes'] / total_attempts * 100) if total_attempts > 0 else 0
            avg_speed_mb = data['avg_speed'] / (1024 * 1024) if data['avg_speed'] > 0 else 0
            
            stats_text += f"🌐 {domain}\n"
            stats_text += f"   Grade: {grade:.1f}/100\n"
            stats_text += f"   Success Rate: {success_rate:.1f}% ({data['successes']}/{total_attempts})\n"
            stats_text += f"   Avg Speed: {avg_speed_mb:.1f} MB/s\n"
            stats_text += f"   Total Downloaded: {data['total_bytes']/(1024*1024):.1f} MB\n\n"
        
        stats_text += "\nMirrors are automatically prioritized by grade for future downloads."
        
        text_widget.setPlainText(stats_text)
        layout.addWidget(text_widget)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()


    def manage_mirrors(self):
        """Show mirror management dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Mirror Management")
        dialog.resize(600, 500)
        
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("Manage Download Mirrors")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header_label)
        
        # Instructions
        info_label = QLabel("Add custom mirrors for packages. Higher priority mirrors are tried first.")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)
        
        # Tabs for different mirror types
        tab_widget = QTabWidget()
        
        # User mirrors tab
        user_tab = QWidget()
        user_layout = QVBoxLayout(user_tab)
        
        self.mirror_table = QTableWidget()
        self.mirror_table.setColumnCount(4)
        self.mirror_table.setHorizontalHeaderLabels(["Package", "Mirror URL", "Priority", "Actions"])
        self.mirror_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        user_layout.addWidget(self.mirror_table)
        
        tab_widget.addTab(user_tab, "User Mirrors")
        
        # Global mirrors tab
        global_tab = QWidget()
        global_layout = QVBoxLayout(global_tab)
        
        # Instructions
        global_info = QLabel("Global mirrors are tried for all packages. Add base URLs that contain LFS packages.")
        global_info.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        global_layout.addWidget(global_info)
        
        # Global mirrors list
        self.global_table = QTableWidget()
        self.global_table.setColumnCount(2)
        self.global_table.setHorizontalHeaderLabels(["Mirror URL", "Actions"])
        self.global_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        global_layout.addWidget(self.global_table)
        
        # Add global mirror section
        global_add_layout = QHBoxLayout()
        global_add_layout.addWidget(QLabel("Base URL:"))
        self.global_url_edit = QLineEdit()
        self.global_url_edit.setPlaceholderText("https://mirror.example.com/lfs/packages/")
        global_add_layout.addWidget(self.global_url_edit)
        
        global_add_btn = QPushButton("Add Global Mirror")
        global_add_btn.clicked.connect(self.add_global_mirror)
        global_add_layout.addWidget(global_add_btn)
        global_layout.addLayout(global_add_layout)
        
        tab_widget.addTab(global_tab, "Global Mirrors")
        
        # Graded mirrors tab
        graded_tab = QWidget()
        graded_layout = QVBoxLayout(graded_tab)
        
        self.graded_table = QTableWidget()
        self.graded_table.setColumnCount(6)
        self.graded_table.setHorizontalHeaderLabels(["Domain", "Grade", "Success Rate", "Avg Speed", "Total MB", "Actions"])
        self.graded_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        graded_layout.addWidget(self.graded_table)
        
        tab_widget.addTab(graded_tab, "Graded Mirrors")
        
        layout.addWidget(tab_widget)
        
        # Add mirror section
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Package:"))
        
        self.package_combo = QComboBox()
        packages = self.downloader.get_package_list()
        for pkg in packages:
            self.package_combo.addItem(pkg['name'])
        add_layout.addWidget(self.package_combo)
        
        add_layout.addWidget(QLabel("Mirror URL:"))
        self.mirror_url_edit = QLineEdit()
        self.mirror_url_edit.setPlaceholderText("https://example.com/path/to/package.tar.xz")
        add_layout.addWidget(self.mirror_url_edit)
        
        add_layout.addWidget(QLabel("Priority:"))
        self.priority_spin = QSpinBox()
        self.priority_spin.setMinimum(1)
        self.priority_spin.setMaximum(10)
        self.priority_spin.setValue(1)
        add_layout.addWidget(self.priority_spin)
        
        add_btn = QPushButton("Add Mirror")
        add_btn.clicked.connect(self.add_mirror)
        add_layout.addWidget(add_btn)
        
        layout.addLayout(add_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_mirrors)
        button_layout.addWidget(refresh_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # Load current mirrors
        self.refresh_mirrors()
        
        dialog.exec_()
    
    def refresh_mirrors(self):
        """Refresh mirror list display"""
        # Refresh global mirrors
        global_mirrors = self.downloader.load_global_mirrors()
        self.global_table.setRowCount(len(global_mirrors))
        
        for i, mirror_url in enumerate(global_mirrors):
            # Mirror URL
            url_item = QTableWidgetItem(mirror_url)
            url_item.setToolTip(mirror_url)
            self.global_table.setItem(i, 0, url_item)
            
            # Actions
            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(lambda checked, url=mirror_url: self.remove_global_mirror(url))
            self.global_table.setCellWidget(i, 1, remove_btn)
        
        # Refresh user mirrors
        user_mirrors = self.downloader.load_user_mirrors()
        
        # Count total mirrors
        total_mirrors = sum(len(mirrors) for mirrors in user_mirrors.values())
        self.mirror_table.setRowCount(total_mirrors)
        
        row = 0
        for package_name, mirrors in user_mirrors.items():
            for i, mirror_url in enumerate(mirrors):
                # Package name
                self.mirror_table.setItem(row, 0, QTableWidgetItem(package_name))
                
                # Mirror URL
                url_item = QTableWidgetItem(mirror_url)
                url_item.setToolTip(mirror_url)
                self.mirror_table.setItem(row, 1, url_item)
                
                # Priority
                self.mirror_table.setItem(row, 2, QTableWidgetItem(str(i + 1)))
                
                # Actions
                remove_btn = QPushButton("Remove")
                remove_btn.clicked.connect(lambda checked, pkg=package_name, url=mirror_url: self.remove_mirror(pkg, url))
                self.mirror_table.setCellWidget(row, 3, remove_btn)
                
                row += 1
        
        # Refresh graded mirrors
        mirror_stats = self.downloader.mirror_stats
        self.graded_table.setRowCount(len(mirror_stats))
        
        row = 0
        for domain, stats in mirror_stats.items():
            grade = self.downloader.get_mirror_grade(domain)
            total_attempts = stats['successes'] + stats['failures']
            success_rate = (stats['successes'] / total_attempts * 100) if total_attempts > 0 else 0
            avg_speed_mb = stats['avg_speed'] / (1024 * 1024) if stats['avg_speed'] > 0 else 0
            total_mb = stats['total_bytes'] / (1024 * 1024)
            
            # Domain
            self.graded_table.setItem(row, 0, QTableWidgetItem(domain))
            
            # Grade
            grade_item = QTableWidgetItem(f"{grade:.1f}")
            if grade >= 70:
                grade_item.setForeground(QColor(0, 128, 0))  # Green
            elif grade >= 40:
                grade_item.setForeground(QColor(255, 165, 0))  # Orange
            else:
                grade_item.setForeground(QColor(255, 0, 0))  # Red
            self.graded_table.setItem(row, 1, grade_item)
            
            # Success Rate
            self.graded_table.setItem(row, 2, QTableWidgetItem(f"{success_rate:.1f}% ({stats['successes']}/{total_attempts})"))
            
            # Avg Speed
            self.graded_table.setItem(row, 3, QTableWidgetItem(f"{avg_speed_mb:.1f} MB/s"))
            
            # Total Downloaded
            self.graded_table.setItem(row, 4, QTableWidgetItem(f"{total_mb:.1f} MB"))
            
            # Actions
            reset_btn = QPushButton("Reset Grade")
            reset_btn.clicked.connect(lambda checked, d=domain: self.reset_mirror_grade(d))
            self.graded_table.setCellWidget(row, 5, reset_btn)
            
            row += 1
    
    def add_mirror(self):
        """Add new mirror"""
        package_name = self.package_combo.currentText()
        mirror_url = self.mirror_url_edit.text().strip()
        priority = self.priority_spin.value()
        
        if not mirror_url:
            QMessageBox.warning(self, "Invalid Input", "Please enter a mirror URL")
            return
        
        if not mirror_url.startswith(('http://', 'https://')):
            QMessageBox.warning(self, "Invalid URL", "Mirror URL must start with http:// or https://")
            return
        
        try:
            self.downloader.add_user_mirror(package_name, mirror_url, priority)
            self.mirror_url_edit.clear()
            self.refresh_mirrors()
            QMessageBox.information(self, "Mirror Added", f"Added mirror for {package_name} with priority {priority}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add mirror: {str(e)}")
    
    def remove_mirror(self, package_name: str, mirror_url: str):
        """Remove mirror"""
        reply = QMessageBox.question(self, 'Remove Mirror', 
                                   f'Remove mirror for {package_name}?\n{mirror_url}',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                user_mirrors = self.downloader.load_user_mirrors()
                if package_name in user_mirrors and mirror_url in user_mirrors[package_name]:
                    user_mirrors[package_name].remove(mirror_url)
                    if not user_mirrors[package_name]:  # Remove empty package entry
                        del user_mirrors[package_name]
                    self.downloader.save_user_mirrors(user_mirrors)
                    self.refresh_mirrors()
                    QMessageBox.information(self, "Mirror Removed", f"Removed mirror for {package_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove mirror: {str(e)}")



    def add_global_mirror(self):
        """Add new global mirror"""
        mirror_url = self.global_url_edit.text().strip()
        
        if not mirror_url:
            QMessageBox.warning(self, "Invalid Input", "Please enter a mirror URL")
            return
        
        if not mirror_url.startswith(('http://', 'https://')):
            QMessageBox.warning(self, "Invalid URL", "Mirror URL must start with http:// or https://")
            return
        
        try:
            self.downloader.add_global_mirror(mirror_url)
            self.global_url_edit.clear()
            self.refresh_mirrors()
            QMessageBox.information(self, "Global Mirror Added", f"Added global mirror: {mirror_url}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add global mirror: {str(e)}")
    
    def remove_global_mirror(self, mirror_url: str):
        """Remove global mirror"""
        reply = QMessageBox.question(self, 'Remove Global Mirror', 
                                   f'Remove global mirror?\n{mirror_url}',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                global_mirrors = self.downloader.load_global_mirrors()
                if mirror_url in global_mirrors:
                    global_mirrors.remove(mirror_url)
                    self.downloader.save_global_mirrors(global_mirrors)
                    self.refresh_mirrors()
                    QMessageBox.information(self, "Global Mirror Removed", f"Removed global mirror: {mirror_url}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove global mirror: {str(e)}")

    def reset_mirror_grade(self, domain: str):
        """Reset mirror grade"""
        reply = QMessageBox.question(self, 'Reset Mirror Grade', 
                                   f'Reset performance grade for {domain}?\nThis will clear all statistics and the mirror will start with a neutral grade.',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.downloader.reset_mirror_grade(domain)
                self.refresh_mirrors()
                QMessageBox.information(self, "Grade Reset", f"Reset grade for {domain}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset grade: {str(e)}")

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
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
        self.settings = SettingsManager()
        self.db = DatabaseManager()
        self.repo_manager = RepositoryManager(self.db)
        self.build_engine = BuildEngine(self.db, self.repo_manager)
        
        # Setup callbacks
        self.build_engine.register_callback('stage_start', self.on_stage_start)
        self.build_engine.register_callback('stage_complete', self.on_stage_complete)
        self.build_engine.register_callback('build_complete', self.on_build_complete)
        self.build_engine.register_callback('build_error', self.on_build_error)
        
        # Connect downloader signals for live repository updates
        self.build_engine.downloader.package_cached.connect(self.on_package_cached)
        
        # Monitor thread
        self.monitor_thread = BuildMonitorThread(self.db)
        self.monitor_thread.build_updated.connect(self.update_build_display)
        
        self.current_build_id = None
        
        self.setup_ui()
        self.load_build_history()
        self.update_document_stats()
        self.load_all_documents()
        
        # Add status bar
        self.statusBar().showMessage("Ready")
    
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
        
        # Build Actions Menu
        self.build_menu_btn = QPushButton("Build Actions")
        self.build_menu = QMenu()
        
        self.new_build_action = self.build_menu.addAction("New Build")
        self.new_build_action.triggered.connect(self.new_build)
        
        self.start_build_action = self.build_menu.addAction("Start Build")
        self.start_build_action.triggered.connect(self.start_build)
        self.start_build_action.setEnabled(False)
        
        self.cancel_build_action = self.build_menu.addAction("Cancel Build")
        self.cancel_build_action.triggered.connect(self.cancel_build)
        self.cancel_build_action.setEnabled(False)
        
        self.build_menu.addSeparator()
        
        self.download_action = self.build_menu.addAction("Download Sources")
        self.download_action.triggered.connect(self.download_sources)
        
        self.package_manager_action = self.build_menu.addAction("Package Manager")
        self.package_manager_action.triggered.connect(self.open_package_manager)
        
        self.cleanup_action = self.build_menu.addAction("Cleanup Builds")
        self.cleanup_action.triggered.connect(self.cleanup_builds)
        
        self.build_menu.addSeparator()
        
        self.kernel_config_action = self.build_menu.addAction("Kernel Configuration")
        self.kernel_config_action.triggered.connect(self.open_kernel_config)
        
        self.settings_action = self.build_menu.addAction("Settings")
        self.settings_action.triggered.connect(self.open_settings)
        
        self.build_menu_btn.setMenu(self.build_menu)
        controls_layout.addWidget(self.build_menu_btn)
        
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
        self.status_filter.addItems(["All", "running", "success", "failed", "cancelled", "archived"])
        self.status_filter.currentTextChanged.connect(self.filter_builds)
        filter_layout.addWidget(self.status_filter)
        controls_layout.addLayout(filter_layout)
        
        left_layout.addWidget(controls_group)
        
        # Build history
        left_layout.addWidget(QLabel("Build History"))
        self.build_history = QTreeWidget()
        self.build_history.setHeaderLabels(["Build ID", "Status", "Date", "Duration"])
        self.build_history.itemClicked.connect(self.select_build)
        self.build_history.itemDoubleClicked.connect(self.show_build_details)
        self.build_history.setContextMenuPolicy(Qt.CustomContextMenu)
        self.build_history.customContextMenuRequested.connect(self.show_build_context_menu)
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
        
        # Download progress
        self.download_progress = QProgressBar()
        self.download_progress.setVisible(False)
        self.download_status = QLabel("")
        self.download_status.setVisible(False)
        overview_layout.addWidget(self.download_status)
        overview_layout.addWidget(self.download_progress)
        
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
        
        # Document search and stats
        doc_header_layout = QHBoxLayout()
        doc_header_layout.addWidget(QLabel("Search Documents:"))
        self.doc_search_edit = QLineEdit()
        self.doc_search_edit.textChanged.connect(self.search_documents)
        doc_header_layout.addWidget(self.doc_search_edit)
        
        # Document stats button
        self.doc_stats_btn = QPushButton("Stats")
        self.doc_stats_btn.clicked.connect(self.show_document_stats)
        doc_header_layout.addWidget(self.doc_stats_btn)
        docs_layout.addLayout(doc_header_layout)
        
        # Document status label
        self.doc_status_label = QLabel("Loading document statistics...")
        self.doc_status_label.setStyleSheet("color: #666; font-style: italic;")
        docs_layout.addWidget(self.doc_status_label)
        
        # Update stats on startup
        QTimer.singleShot(1000, self.update_document_stats)
        
        # Documents list
        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(4)
        self.documents_table.setHorizontalHeaderLabels(["Type", "Title", "Date", "Size"])
        self.documents_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
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
        
        # Repository summary
        self.repo_summary_label = QLabel("")
        self.repo_summary_label.setStyleSheet("font-weight: bold; padding: 5px; background-color: #f0f0f0; border: 1px solid #ccc;")
        repo_layout.addWidget(self.repo_summary_label)
        
        # Repository files
        repo_layout.addWidget(QLabel("Repository Files:"))
        self.repo_files_tree = QTreeWidget()
        self.repo_files_tree.setHeaderLabels(["File", "Size", "Type", "Date"])
        self.repo_files_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.repo_files_tree.customContextMenuRequested.connect(self.show_repo_file_context_menu)
        repo_layout.addWidget(self.repo_files_tree)
        self.update_repo_files()
        
        right_panel.addTab(repo_tab, "Repository")
        
        main_layout.addWidget(right_panel)
    
    def new_build(self):
        dialog = BuildConfigDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, config_content = dialog.get_config()
            if name and config_content:
                # Save config to repository
                config_path = self.repo_manager.add_build_config(name, config_content)
                QMessageBox.information(self, "Success", f"Configuration saved: {config_path}")
                self.start_build_action.setEnabled(True)
    
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
            
            self.start_build_action.setEnabled(False)
            self.cancel_build_action.setEnabled(True)
            
            self.load_build_history()
            
        except Exception as e:
            QMessageBox.critical(self, "Build Error", f"Failed to start build: {str(e)}")
    
    def cancel_build(self):
        # Cancel regular build
        if hasattr(self, 'current_build_id') and self.current_build_id:
            self.build_engine.cancel_build(self.current_build_id)
            if hasattr(self, 'monitor_thread'):
                self.monitor_thread.stop()
            self.start_build_action.setEnabled(True)
            self.cancel_build_action.setEnabled(False)
        
        # Cancel download
        if hasattr(self, 'download_thread') and self.download_thread.isRunning():
            self.download_thread.cancel()
            if hasattr(self, 'download_id'):
                self.db.update_build_status(self.download_id, 'cancelled', 0)
                self.db.add_document(
                    self.download_id, 'log', 'Download Cancelled',
                    'Download was cancelled by user', {'cancelled': True}
                )
            QMessageBox.information(self, "Download Cancelled", "Download has been cancelled.")
            self.reset_download_ui()
    
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
        self.current_build_id = build_id
        self.display_build_details(build_id)
        # Clear document search when selecting a build
        self.doc_search_edit.clear()
        # Update document stats
        self.update_document_stats()
    
    def show_build_details(self, item):
        """Show detailed build information dialog"""
        build_id = item.text(0)
        dialog = BuildDetailsDialog(self.db, build_id, self)
        dialog.show()
    
    def show_build_context_menu(self, position):
        """Show context menu for build history"""
        item = self.build_history.itemAt(position)
        if item:
            menu = QMenu()
            
            details_action = menu.addAction("Show Details")
            details_action.triggered.connect(lambda: self.show_build_details(item))
            
            menu.addSeparator()
            
            archive_action = menu.addAction("Archive Build")
            archive_action.triggered.connect(lambda: self.archive_build(item))
            
            menu.exec_(self.build_history.mapToGlobal(position))
    
    def archive_build(self, item):
        """Archive selected build (preserves documents)"""
        build_id = item.text(0)
        reply = QMessageBox.question(self, 'Archive Build', 
                                   f'Archive build {build_id}? This will hide it from the active list but preserve all documents and logs for historical reference.',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.db.update_build_status(build_id, 'archived')
                self.db.add_document(
                    build_id, 'log', 'Build Archived',
                    'Build was archived by user but all documents preserved for historical reference',
                    {'archived': True, 'archived_at': datetime.now().isoformat()}
                )
                
                QMessageBox.information(self, "Build Archived", f"Build {build_id} has been archived. All documents are preserved for historical reference.")
                self.load_build_history()
                
            except Exception as e:
                QMessageBox.critical(self, "Archive Error", f"Failed to archive build: {str(e)}")
    
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
        self.load_build_documents(build_id)
        
        # Update logs
        log_content = ""
        for stage in stages:
            log_content += f"=== {stage['stage_name']} ({stage['status']}) ===\n"
            if stage.get('output_log'):
                log_content += stage['output_log'] + "\n"
            if stage.get('error_log'):
                log_content += "ERRORS:\n" + stage['error_log'] + "\n"
            log_content += "\n"
        
        self.logs_text.setPlainText(log_content)
        # Auto-scroll to bottom for live updates
        scrollbar = self.logs_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_build_display(self, build_details):
        if build_details and build_details.get('build'):
            build_id = build_details['build']['build_id']
            self.display_build_details(build_id)
            # Update live logs for running builds
            if build_details['build']['status'] == 'running':
                self.update_live_logs(build_details)
    
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
        """Search documents across all builds"""
        query = self.doc_search_edit.text().strip()
        
        if not query:
            # Show all documents when no search query
            self.load_all_documents()
            return
        
        try:
            # Search documents across all builds
            documents = self.db.search_documents(query)
            
            self.documents_table.setRowCount(len(documents))
            for i, doc in enumerate(documents):
                # Add build ID column for global search
                if self.documents_table.columnCount() < 5:
                    self.documents_table.setColumnCount(5)
                    self.documents_table.setHorizontalHeaderLabels(["Build ID", "Type", "Title", "Date", "Size"])
                
                self.documents_table.setItem(i, 0, QTableWidgetItem(doc['build_id']))
                self.documents_table.setItem(i, 1, QTableWidgetItem(doc['document_type']))
                self.documents_table.setItem(i, 2, QTableWidgetItem(doc['title']))
                self.documents_table.setItem(i, 3, QTableWidgetItem(doc['created_at'].strftime('%Y-%m-%d %H:%M:%S')))
                self.documents_table.setItem(i, 4, QTableWidgetItem(f"{len(doc['content'])} chars"))
                
                # Store document data for viewing
                self.documents_table.item(i, 0).setData(Qt.UserRole, doc)
            
            # Update status
            if documents:
                self.document_viewer.setPlainText(f"Found {len(documents)} documents matching '{query}'\n\nClick on a document to view its content.")
            else:
                self.document_viewer.setPlainText(f"No documents found matching '{query}'")
                
        except Exception as e:
            QMessageBox.warning(self, "Search Error", f"Failed to search documents: {str(e)}")
    
    def load_build_documents(self, build_id: str):
        """Load documents for a specific build"""
        try:
            documents = self.db.get_build_documents(build_id)
            
            # Reset to 4 columns for build-specific view
            self.documents_table.setColumnCount(4)
            self.documents_table.setHorizontalHeaderLabels(["Type", "Title", "Date", "Size"])
            
            self.documents_table.setRowCount(len(documents))
            for i, doc in enumerate(documents):
                self.documents_table.setItem(i, 0, QTableWidgetItem(doc['document_type']))
                self.documents_table.setItem(i, 1, QTableWidgetItem(doc['title']))
                self.documents_table.setItem(i, 2, QTableWidgetItem(doc['created_at'].strftime('%Y-%m-%d %H:%M:%S')))
                self.documents_table.setItem(i, 3, QTableWidgetItem(f"{len(doc['content'])} chars"))
                
                # Store document data for viewing
                self.documents_table.item(i, 0).setData(Qt.UserRole, doc)
            
            if documents:
                self.document_viewer.setPlainText(f"Build {build_id} has {len(documents)} documents\n\nClick on a document to view its content.")
            else:
                self.document_viewer.setPlainText(f"No documents found for build {build_id}")
                
        except Exception as e:
            print(f"Error loading documents: {e}")
    
    def view_document(self, item):
        """View selected document content"""
        row = item.row()
        if row >= 0:
            # Get document data from the first column item
            doc_item = self.documents_table.item(row, 0)
            if doc_item:
                doc = doc_item.data(Qt.UserRole)
                if doc:
                    # Format document content for viewing
                    content = f"Document: {doc['title']}\n"
                    content += f"Type: {doc['document_type']}\n"
                    content += f"Build ID: {doc['build_id']}\n"
                    content += f"Created: {doc['created_at']}\n"
                    content += f"Size: {len(doc['content'])} characters\n"
                    content += "=" * 50 + "\n\n"
                    content += doc['content']
                    
                    self.document_viewer.setPlainText(content)
    
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
        self.start_build_action.setEnabled(True)
        self.cancel_build_action.setEnabled(False)
        self.load_build_history()
        self.update_document_stats()
    
    def on_build_error(self, data):
        print(f"Build error: {data.get('error', 'Unknown error')}")
        self.monitor_thread.stop()
        self.start_build_action.setEnabled(True)
        self.cancel_build_action.setEnabled(False)
        self.update_document_stats()
    
    def on_package_cached(self, package_name: str, cache_info: dict):
        """Handle package successfully cached - update repository view"""
        print(f"📦 Package {package_name} cached - updating repository view")
        
        # Update repository status and files
        self.update_repo_status()
        self.update_repo_files()
        
        # If package manager dialog is open, refresh it
        for widget in self.findChildren(PackageManagerDialog):
            if widget.isVisible():
                widget.refresh_package_status()
        
        # Show brief status message
        self.statusBar().showMessage(f"📦 Cached {package_name} in repository", 3000)
    
    def download_sources(self):
        """Download all LFS source packages"""
        try:
            # Create a build ID for tracking downloads
            self.download_id = f"download-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Create build record for downloads - ensure it exists before starting thread
            success = self.db.create_build(self.download_id, "download", 1)
            if not success:
                raise Exception("Failed to create build record for download tracking")
            
            # Setup UI for download
            self.download_action.setEnabled(False)
            self.download_action.setText("Downloading...")
            self.cancel_build_action.setEnabled(True)
            self.download_progress.setVisible(True)
            self.download_status.setVisible(True)
            self.download_progress.setMaximum(len(self.build_engine.downloader.get_package_list()))
            self.download_progress.setValue(0)
            
            # Start download thread
            self.download_thread = DownloadThread(self.build_engine, self.download_id)
            self.download_thread.finished.connect(self.on_download_finished)
            self.download_thread.error.connect(self.on_download_error)
            self.download_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Download Error", f"Failed to start download: {str(e)}")
            self.reset_download_ui()
    
    def on_download_finished(self, results):
        """Handle download completion"""
        cached_count = len(results.get('cached', []))
        download_count = len(results.get('success', []))
        failed_count = len(results.get('failed', []))
        total_acquired = cached_count + download_count
        
        # Update build status
        if failed_count == 0:
            self.db.update_build_status(self.download_id, 'success', 1)
            if cached_count > 0:
                QMessageBox.information(self, "Package Acquisition Complete", 
                                       f"All packages acquired successfully!\n\n"
                                       f"From cache: {cached_count} packages\n"
                                       f"Downloaded: {download_count} packages\n"
                                       f"Total: {total_acquired} packages")
            else:
                QMessageBox.information(self, "Download Complete", 
                                       f"Successfully downloaded all {download_count} packages!")
        else:
            self.db.update_build_status(self.download_id, 'failed', 0)
            QMessageBox.warning(self, "Package Acquisition Incomplete", 
                               f"Acquired {total_acquired} packages successfully:\n"
                               f"- From cache: {cached_count}\n"
                               f"- Downloaded: {download_count}\n"
                               f"- Failed: {failed_count}")
        
        # Commit sources to repository
        try:
            if download_count > 0:
                commit_msg = f"LFS sources: {cached_count} cached, {download_count} downloaded, {failed_count} failed"
                self.repo_manager.commit_changes(commit_msg, self.download_id)
                self.update_repo_status()
        except Exception as e:
            print(f"Commit error: {e}")
        
        self.reset_download_ui()
        self.update_document_stats()
    
    def on_download_error(self, error_msg):
        """Handle download error"""
        QMessageBox.critical(self, "Download Error", f"Download failed: {error_msg}")
        self.db.update_build_status(self.download_id, 'failed', 0)
        self.reset_download_ui()
        self.update_document_stats()
    
    def reset_download_ui(self):
        """Reset download UI elements"""
        self.download_action.setEnabled(True)
        self.download_action.setText("Download Sources")
        self.cancel_build_action.setEnabled(False)
        self.download_progress.setVisible(False)
        self.download_status.setVisible(False)
    
    def cleanup_builds(self):
        """Cleanup stuck/running builds"""
        reply = QMessageBox.question(self, 'Cleanup Builds', 
                                   'This will mark all running builds as cancelled. Continue?',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                conn = self.db.connect()
                cursor = conn.cursor()
                
                cursor.execute("SELECT build_id FROM builds WHERE status = 'running'")
                running_builds = cursor.fetchall()
                
                if not running_builds:
                    QMessageBox.information(self, "Cleanup Complete", "No running builds found.")
                    cursor.close()
                    return
                
                cursor.execute("UPDATE builds SET status = 'cancelled', end_time = NOW() WHERE status = 'running'")
                
                for build in running_builds:
                    build_id = build[0]
                    cursor.execute("""
                        INSERT INTO build_documents (build_id, document_type, title, content, metadata)
                        VALUES (%s, 'log', 'Build Cleanup', 'Build was marked as cancelled during cleanup', '{"cleanup": true}')
                    """, (build_id,))
                
                conn.commit()
                cursor.close()
                
                QMessageBox.information(self, "Cleanup Complete", 
                                       f"Cleaned up {len(running_builds)} running builds.")
                
                self.load_build_history()
                
            except Exception as e:
                QMessageBox.critical(self, "Cleanup Error", f"Failed to cleanup builds: {str(e)}")
    

    def open_kernel_config(self):
        """Open kernel configuration dialog"""
        dialog = KernelConfigDialog(self.settings, self)
        dialog.exec_()

    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_() == QDialog.Accepted:
            # Reinitialize repository manager with new path
            old_repo_path = self.repo_manager.repo_path
            new_repo_path = self.settings.get_repository_path()
            
            if str(old_repo_path) != new_repo_path:
                self.repo_manager = RepositoryManager(self.db)
                self.build_engine.repo = self.repo_manager
                self.build_engine.downloader.repo = self.repo_manager
                self.update_repo_status()
                self.update_repo_files()
                QMessageBox.information(self, "Settings Updated", 
                                       f"Repository path changed to: {new_repo_path}")
            else:
                QMessageBox.information(self, "Settings Updated", "Settings have been saved.")
    
    def update_document_stats(self):
        """Update document statistics display"""
        try:
            stats = self.db.get_document_stats()
            overall = stats['overall']
            
            if overall and overall.get('total_documents', 0) > 0:
                size_mb = (overall.get('total_content_size') or 0) / (1024 * 1024)
                status_text = f"📄 {overall['total_documents']} documents stored across {overall.get('builds_with_docs', 0)} builds ({size_mb:.1f} MB)"
            else:
                status_text = "📄 No documents stored yet - documents will appear here as builds run"
            
            self.doc_status_label.setText(status_text)
            
        except Exception as e:
            self.doc_status_label.setText(f"📄 Document stats unavailable: {str(e)}")
    
    def show_document_stats(self):
        """Show detailed document statistics"""
        try:
            stats = self.db.get_document_stats()
            overall = stats['overall']
            by_type = stats['by_type']
            
            stats_text = f"""Document Storage Statistics

Overall:
• Total Documents: {overall.get('total_documents', 0)}
• Builds with Documents: {overall.get('builds_with_docs', 0)}
• Total Content Size: {(overall.get('total_content_size') or 0) / (1024 * 1024):.1f} MB

By Document Type:
"""
            
            for type_stat in by_type:
                stats_text += f"• {type_stat['document_type']}: {type_stat['type_count']} documents\n"
            
            stats_text += "\nDocument Types:\n• log: Build stage execution logs\n• config: Build configurations\n• output: Build outputs and artifacts\n• error: Error messages and diagnostics\n• summary: Build summaries and reports"
            
            QMessageBox.information(self, "Document Statistics", stats_text)
            
        except Exception as e:
            QMessageBox.warning(self, "Stats Error", f"Failed to get document statistics: {str(e)}")
    
    def open_package_manager(self):
        """Open package management dialog"""
        dialog = PackageManagerDialog(self.build_engine.downloader, self)
        # Connect to live updates
        self.build_engine.downloader.package_cached.connect(dialog.refresh_package_status)
        dialog.exec_()
    
    def update_live_logs(self, build_details):
        """Update logs in real-time for running builds"""
        try:
            stages = build_details.get('stages', [])
            
            # Build live log content
            log_content = ""
            for stage in stages:
                log_content += f"=== {stage['stage_name']} ({stage['status']}) ===\n"
                if stage.get('output_log'):
                    log_content += stage['output_log'] + "\n"
                if stage.get('error_log'):
                    log_content += "ERRORS:\n" + stage['error_log'] + "\n"
                log_content += "\n"
            
            # Add current status
            build = build_details.get('build', {})
            log_content += f"\n=== BUILD STATUS ===\n"
            log_content += f"Status: {build.get('status', 'unknown')}\n"
            log_content += f"Completed Stages: {build.get('completed_stages', 0)}/{build.get('total_stages', 0)}\n"
            
            # Update logs text
            self.logs_text.setPlainText(log_content)
            
            # Auto-scroll to bottom
            scrollbar = self.logs_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            print(f"Error updating live logs: {e}")
    
    def load_all_documents(self):
        """Load all documents from all builds"""
        try:
            # Get all documents across all builds
            documents = self.db.get_all_documents()
            
            # Set to 5 columns for all documents view
            self.documents_table.setColumnCount(5)
            self.documents_table.setHorizontalHeaderLabels(["Build ID", "Type", "Title", "Date", "Size"])
            
            self.documents_table.setRowCount(len(documents))
            for i, doc in enumerate(documents):
                self.documents_table.setItem(i, 0, QTableWidgetItem(doc['build_id']))
                self.documents_table.setItem(i, 1, QTableWidgetItem(doc['document_type']))
                self.documents_table.setItem(i, 2, QTableWidgetItem(doc['title']))
                self.documents_table.setItem(i, 3, QTableWidgetItem(doc['created_at'].strftime('%Y-%m-%d %H:%M:%S')))
                self.documents_table.setItem(i, 4, QTableWidgetItem(f"{len(doc['content'])} chars"))
                
                # Store document data for viewing
                self.documents_table.item(i, 0).setData(Qt.UserRole, doc)
            
            if documents:
                self.document_viewer.setPlainText(f"Showing all {len(documents)} documents\n\nClick on a document to view its content.")
            else:
                self.document_viewer.setPlainText("No documents found in database")
                
        except Exception as e:
            print(f"Error loading all documents: {e}")
            self.document_viewer.setPlainText(f"Error loading documents: {str(e)}")
    
    def update_repo_files(self):
        """Update repository files display and summary"""
        self.repo_files_tree.clear()
        
        try:
            # Get package status
            all_packages = self.build_engine.downloader.get_package_list()
            cached_packages = self.build_engine.downloader.get_cached_packages() or []
            
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
            
            # Check for active downloads
            downloading_count = 0
            if hasattr(self, 'download_thread') and self.download_thread.isRunning():
                downloading_count = missing_count  # Assume all missing are being downloaded
            
            # Update summary
            summary_text = f"📦 Packages: {cached_count}/{total_packages} cached"
            if missing_count > 0:
                summary_text += f" | ⚠ {missing_count} missing"
            if downloading_count > 0:
                summary_text += f" | ⬇ {downloading_count} downloading"
            
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
            # Find matching package in our list
            packages = self.build_engine.downloader.get_package_list()
            matching_package = None
            
            for pkg in packages:
                pkg_filename = pkg['url'].split('/')[-1]
                if pkg_filename == filename:
                    matching_package = pkg
                    break
            
            if matching_package:
                # Verify checksum
                from pathlib import Path
                actual_md5 = self.build_engine.downloader.get_file_md5(Path(file_path))
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
                actual_md5 = self.build_engine.downloader.get_file_md5(Path(file_path))
                QMessageBox.information(self, "File Checksum", 
                                       f"File: {filename}\n"
                                       f"MD5: {actual_md5}\n\n"
                                       f"(No matching package found for verification)")
                
        except Exception as e:
            QMessageBox.critical(self, "Verification Error", f"Failed to verify checksum: {str(e)}")
    
    def show_missing_packages(self):
        """Show detailed missing packages information"""
        try:
            all_packages = self.build_engine.downloader.get_package_list()
            cached_packages = self.build_engine.downloader.get_cached_packages() or []
            
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
            download_btn.clicked.connect(lambda: self.download_missing_from_dialog(dialog))
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
    
    def download_missing_from_dialog(self, dialog):
        """Start downloading missing packages from the dialog"""
        dialog.accept()
        self.download_sources()
    
    def export_missing_urls(self, missing_packages):
        """Export missing package URLs to a file"""
        filename, _ = QFileDialog.getSaveFileName(self, "Save Missing Package URLs", "missing-packages.txt", "Text Files (*.txt)")
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(f"# Missing LFS Packages ({len(missing_packages)} packages)\n")
                    f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    for pkg in missing_packages:
                        f.write(f"# {pkg['name']} {pkg['version']}\n")
                        f.write(f"{pkg['url']}\n\n")
                
                QMessageBox.information(self, "Export Complete", f"Missing package URLs saved to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save URLs: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = LFSMainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()