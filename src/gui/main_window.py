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
from .sudo_dialog import SudoPasswordDialog
from .git_interface import GitMainInterface
from ..analysis.fault_analyzer import FaultAnalyzer
from .advanced_analysis_methods import (
    format_performance_results, format_predictive_analysis_results,
    format_root_cause_analysis_results, generate_health_report, predict_next_build
)

class BuildMonitorThread(QThread):
    build_updated = pyqtSignal(dict)
    stage_updated = pyqtSignal(dict)
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.current_build_id = None
        self.running = False
        self.update_interval = 1500  # 1.5 seconds for more responsive live updates
    
    def set_build_id(self, build_id: str):
        self.current_build_id = build_id
    
    def run(self):
        self.running = True
        consecutive_errors = 0
        
        while self.running and self.current_build_id:
            try:
                # Use a fresh connection for each query to avoid cursor issues
                build_details = self.get_build_details_safe(self.current_build_id)
                if build_details:
                    self.build_updated.emit(build_details)
                    consecutive_errors = 0  # Reset error counter on success
                else:
                    # Build might be completed or not found
                    consecutive_errors += 1
                    if consecutive_errors > 5:
                        print(f"Build {self.current_build_id} not found after 5 attempts, stopping monitor")
                        break
                
                self.msleep(self.update_interval)
                
            except Exception as e:
                consecutive_errors += 1
                print(f"Monitor error (attempt {consecutive_errors}): {e}")
                
                # If too many consecutive errors, stop monitoring
                if consecutive_errors > 10:
                    print("Too many monitor errors, stopping thread")
                    break
                    
                # Exponential backoff on errors
                error_delay = min(10000, 1000 * consecutive_errors)
                self.msleep(error_delay)
    
    def get_build_details_safe(self, build_id: str):
        """Safely get build details with proper connection handling"""
        try:
            # Create a fresh connection for this query
            conn = self.db.connect()
            if not conn:
                return None
                
            cursor = conn.cursor(dictionary=True)
            
            # Get build info
            cursor.execute("SELECT * FROM builds WHERE build_id = %s", (build_id,))
            build = cursor.fetchone()
            
            if not build:
                cursor.close()
                conn.close()
                return None
            
            # Get stages
            cursor.execute("SELECT * FROM build_stages WHERE build_id = %s ORDER BY stage_order", (build_id,))
            stages = cursor.fetchall()
            
            # Get recent documents (limit to avoid memory issues)
            cursor.execute("""
                SELECT * FROM build_documents 
                WHERE build_id = %s 
                ORDER BY created_at DESC 
                LIMIT 50
            """, (build_id,))
            documents = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {
                'build': build,
                'stages': stages or [],
                'documents': documents or []
            }
            
        except Exception as e:
            print(f"Error in get_build_details_safe: {e}")
            return None
    
    def stop(self):
        self.running = False
        # Wait for thread to finish gracefully
        if self.isRunning():
            self.wait(3000)  # Wait up to 3 seconds

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
        self.fault_analyzer = FaultAnalyzer(self.db)
        import os
        
        # Bind advanced analysis methods
        self._format_performance_results = lambda x: format_performance_results(self, x)
        self._format_predictive_analysis_results = lambda: format_predictive_analysis_results(self)
        self._format_root_cause_analysis_results = lambda: format_root_cause_analysis_results(self)
        self.generate_health_report = lambda: generate_health_report(self)
        self.predict_next_build = lambda: predict_next_build(self)
        
        # Setup callbacks
        self.build_engine.register_callback('stage_start', self.on_stage_start)
        self.build_engine.register_callback('stage_complete', self.on_stage_complete)
        self.build_engine.register_callback('build_complete', self.on_build_complete)
        self.build_engine.register_callback('build_error', self.on_build_error)
        self.build_engine.register_callback('sudo_required', self.on_sudo_required)
        
        # Connect downloader signals for live repository updates
        self.build_engine.downloader.package_cached.connect(self.on_package_cached)
        
        # Monitor thread
        self.monitor_thread = BuildMonitorThread(self.db)
        self.monitor_thread.build_updated.connect(self.update_build_display)
        
        # Auto-refresh documents periodically
        self.doc_refresh_timer = QTimer()
        self.doc_refresh_timer.timeout.connect(self.refresh_current_build_documents)
        self.doc_refresh_timer.start(3000)  # Refresh every 3 seconds for more responsive updates
        
        # Live logs refresh timer
        self.logs_refresh_timer = QTimer()
        self.logs_refresh_timer.timeout.connect(self.refresh_logs_manually)
        self.logs_refresh_timer.start(2000)  # Refresh logs every 2 seconds
        
        # System status refresh timer
        self.status_refresh_timer = QTimer()
        self.status_refresh_timer.timeout.connect(self.refresh_system_status)
        self.status_refresh_timer.start(5000)  # Refresh system status every 5 seconds
        
        self.current_build_id = None
        
        # Pagination state
        self.current_page = 1
        self.page_size = 50
        self.total_documents = 0
        self.total_pages = 1
        self.browse_mode = False  # True when browsing all documents
        
        self.setup_ui()
        self.load_build_history()
        self.update_document_stats()
        self.load_all_documents()
        
        # Load documents for the most recent build
        builds = self.db.search_builds(limit=1)
        if builds:
            self.current_build_id = builds[0]['build_id']
            self.display_build_details(self.current_build_id)
        
        # Setup LFS permissions on startup
        self.setup_lfs_permissions()
        
        # Initial system status refresh
        self.refresh_system_status()
        
        # Add status bar
        self.statusBar().showMessage("Ready")
    
    def setup_lfs_permissions(self):
        """Setup LFS directory permissions on startup"""
        try:
            import subprocess
            import os
            
            # Check if LFS directory exists and needs setup
            lfs_dir = "/mnt/lfs"
            sources_dir = "/mnt/lfs/sources"
            
            if not os.path.exists(lfs_dir):
                self.statusBar().showMessage("LFS directory not found - please run setup first", 5000)
                return
            
            if not os.path.exists(sources_dir):
                self.statusBar().showMessage("Creating LFS sources directory...", 3000)
                subprocess.run(['sudo', 'mkdir', '-p', sources_dir], check=True)
            
            # Check if sources directory is writable
            if not os.access(sources_dir, os.W_OK):
                self.statusBar().showMessage("Setting up LFS permissions...", 3000)
                # Make sources directory writable for package copying
                subprocess.run(['sudo', 'chmod', '777', sources_dir], check=True)
                self.statusBar().showMessage("✓ LFS permissions configured", 3000)
            
        except subprocess.CalledProcessError:
            # Permissions setup failed - show helpful message
            self.statusBar().showMessage("⚠ LFS permissions setup needed - see installation guide", 8000)
        except Exception as e:
            print(f"LFS setup error: {e}")
            self.statusBar().showMessage("⚠ LFS setup check failed", 5000)
    
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
        
        self.lfs_setup_action = self.build_menu.addAction("Setup LFS Permissions")
        self.lfs_setup_action.triggered.connect(self.setup_lfs_permissions_interactive)
        
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
        
        # Logs header with refresh button
        logs_header = QHBoxLayout()
        logs_header.addWidget(QLabel("Live Build Logs:"))
        logs_header.addStretch()
        
        self.refresh_logs_btn = QPushButton("Refresh")
        self.refresh_logs_btn.clicked.connect(self.refresh_logs_manually)
        logs_header.addWidget(self.refresh_logs_btn)
        
        self.auto_scroll_btn = QPushButton("Auto-scroll")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        logs_header.addWidget(self.auto_scroll_btn)
        
        logs_layout.addLayout(logs_header)
        
        self.logs_text = QTextEdit()
        self.logs_text.setFont(QFont("Courier", 9))
        self.logs_text.setReadOnly(True)
        logs_layout.addWidget(self.logs_text)
        
        right_panel.addTab(logs_tab, "Build Logs")
        
        # Build Documents tab (build-specific)
        docs_tab = QWidget()
        docs_layout = QVBoxLayout(docs_tab)
        
        # Build documents header
        build_docs_header = QHBoxLayout()
        build_docs_header.addWidget(QLabel("Build Documents:"))
        build_docs_header.addStretch()
        
        # Document stats button
        self.doc_stats_btn = QPushButton("Stats")
        self.doc_stats_btn.clicked.connect(self.show_document_stats)
        build_docs_header.addWidget(self.doc_stats_btn)
        docs_layout.addLayout(build_docs_header)
        
        # Document status label
        self.doc_status_label = QLabel("Loading document statistics...")
        self.doc_status_label.setStyleSheet("color: #666; font-style: italic;")
        docs_layout.addWidget(self.doc_status_label)
        
        # Update stats on startup
        QTimer.singleShot(1000, self.update_document_stats)
        
        # Build documents list
        self.build_documents_table = QTableWidget()
        self.build_documents_table.setColumnCount(4)
        self.build_documents_table.setHorizontalHeaderLabels(["Type", "Title", "Date", "Size"])
        self.build_documents_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.build_documents_table.itemClicked.connect(self.view_build_document)
        docs_layout.addWidget(self.build_documents_table)
        
        # Build document viewer
        self.build_document_viewer = QTextEdit()
        self.build_document_viewer.setFont(QFont("Courier", 9))
        self.build_document_viewer.setReadOnly(True)
        docs_layout.addWidget(self.build_document_viewer)
        
        right_panel.addTab(docs_tab, "Build Documents")
        
        # Document Browser tab (all documents with pagination)
        browser_tab = QWidget()
        browser_layout = QVBoxLayout(browser_tab)
        
        # Document search and controls
        doc_header_layout = QHBoxLayout()
        doc_header_layout.addWidget(QLabel("Search Documents:"))
        self.doc_search_edit = QLineEdit()
        self.doc_search_edit.textChanged.connect(self.search_documents)
        doc_header_layout.addWidget(self.doc_search_edit)
        
        # Browse all button
        self.browse_all_btn = QPushButton("Browse All")
        self.browse_all_btn.clicked.connect(self.browse_all_documents)
        doc_header_layout.addWidget(self.browse_all_btn)
        
        browser_layout.addLayout(doc_header_layout)
        
        # Pagination controls
        pagination_layout = QHBoxLayout()
        
        self.first_page_btn = QPushButton("<<")
        self.first_page_btn.clicked.connect(self.go_to_first_page)
        self.first_page_btn.setMaximumWidth(40)
        pagination_layout.addWidget(self.first_page_btn)
        
        self.prev_page_btn = QPushButton("<")
        self.prev_page_btn.clicked.connect(self.go_to_prev_page)
        self.prev_page_btn.setMaximumWidth(40)
        pagination_layout.addWidget(self.prev_page_btn)
        
        self.page_info_label = QLabel("Page 1 of 1")
        self.page_info_label.setAlignment(Qt.AlignCenter)
        pagination_layout.addWidget(self.page_info_label)
        
        self.next_page_btn = QPushButton(">")
        self.next_page_btn.clicked.connect(self.go_to_next_page)
        self.next_page_btn.setMaximumWidth(40)
        pagination_layout.addWidget(self.next_page_btn)
        
        self.last_page_btn = QPushButton(">>")
        self.last_page_btn.clicked.connect(self.go_to_last_page)
        self.last_page_btn.setMaximumWidth(40)
        pagination_layout.addWidget(self.last_page_btn)
        
        pagination_layout.addStretch()
        
        # Page size selector
        pagination_layout.addWidget(QLabel("Per page:"))
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["25", "50", "100", "200"])
        self.page_size_combo.setCurrentText("50")
        self.page_size_combo.currentTextChanged.connect(self.change_page_size)
        pagination_layout.addWidget(self.page_size_combo)
        
        browser_layout.addLayout(pagination_layout)
        
        # Documents list
        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(5)
        self.documents_table.setHorizontalHeaderLabels(["Build ID", "Type", "Title", "Date", "Size"])
        self.documents_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.documents_table.itemClicked.connect(self.view_document)
        browser_layout.addWidget(self.documents_table)
        
        # Document viewer
        self.document_viewer = QTextEdit()
        self.document_viewer.setFont(QFont("Courier", 9))
        self.document_viewer.setReadOnly(True)
        browser_layout.addWidget(self.document_viewer)
        
        right_panel.addTab(browser_tab, "Document Browser")
        
        # System Status tab
        status_tab = QWidget()
        status_layout = QVBoxLayout(status_tab)
        
        # Status header with refresh button
        status_header = QHBoxLayout()
        status_header.addWidget(QLabel("System Status:"))
        status_header.addStretch()
        
        self.refresh_status_btn = QPushButton("Refresh")
        self.refresh_status_btn.clicked.connect(self.refresh_system_status)
        status_header.addWidget(self.refresh_status_btn)
        
        status_layout.addLayout(status_header)
        
        # Process status
        self.process_status = QTextEdit()
        self.process_status.setFont(QFont("Courier", 9))
        self.process_status.setReadOnly(True)
        self.process_status.setMaximumHeight(200)
        status_layout.addWidget(self.process_status)
        
        # Build activity
        status_layout.addWidget(QLabel("Build Activity:"))
        self.build_activity = QTextEdit()
        self.build_activity.setFont(QFont("Courier", 9))
        self.build_activity.setReadOnly(True)
        status_layout.addWidget(self.build_activity)
        
        right_panel.addTab(status_tab, "System Status")
        
        # Fault Analysis tab
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        
        # Analysis header with controls
        analysis_header = QHBoxLayout()
        analysis_header.addWidget(QLabel("Fault Analysis:"))
        analysis_header.addStretch()
        
        self.analyze_btn = QPushButton("Run Comprehensive Analysis")
        self.analyze_btn.clicked.connect(self.run_fault_analysis)
        analysis_header.addWidget(self.analyze_btn)
        
        # Pattern management buttons
        self.export_patterns_btn = QPushButton("Export Patterns")
        self.export_patterns_btn.clicked.connect(self.export_fault_patterns)
        analysis_header.addWidget(self.export_patterns_btn)
        
        self.import_patterns_btn = QPushButton("Import Patterns")
        self.import_patterns_btn.clicked.connect(self.import_fault_patterns)
        analysis_header.addWidget(self.import_patterns_btn)
        
        # Advanced analysis buttons
        self.health_report_btn = QPushButton("Health Report")
        self.health_report_btn.clicked.connect(self.generate_health_report)
        analysis_header.addWidget(self.health_report_btn)
        
        self.predict_build_btn = QPushButton("Predict Build")
        self.predict_build_btn.clicked.connect(self.predict_next_build)
        analysis_header.addWidget(self.predict_build_btn)
        
        self.learning_insights_btn = QPushButton("Learning Insights")
        self.learning_insights_btn.clicked.connect(self.show_learning_insights)
        analysis_header.addWidget(self.learning_insights_btn)
        
        # Days selector
        analysis_header.addWidget(QLabel("Days:"))
        self.days_combo = QComboBox()
        self.days_combo.addItems(["7", "14", "30", "60", "90"])
        self.days_combo.setCurrentText("30")
        analysis_header.addWidget(self.days_combo)
        
        analysis_layout.addLayout(analysis_header)
        
        # Analysis results with tabs
        self.analysis_results_tabs = QTabWidget()
        
        # Main analysis tab
        self.analysis_results = QTextEdit()
        self.analysis_results.setFont(QFont("Courier", 9))
        self.analysis_results.setReadOnly(True)
        self.analysis_results_tabs.addTab(self.analysis_results, "Analysis Results")
        
        # Stage analysis tab
        self.stage_results = QTextEdit()
        self.stage_results.setFont(QFont("Courier", 9))
        self.stage_results.setReadOnly(True)
        self.analysis_results_tabs.addTab(self.stage_results, "Stage Analysis")
        
        # Trends tab
        self.trends_results = QTextEdit()
        self.trends_results.setFont(QFont("Courier", 9))
        self.trends_results.setReadOnly(True)
        self.analysis_results_tabs.addTab(self.trends_results, "Trends")
        
        # New patterns tab
        self.new_patterns_results = QTextEdit()
        self.new_patterns_results.setFont(QFont("Courier", 9))
        self.new_patterns_results.setReadOnly(True)
        self.analysis_results_tabs.addTab(self.new_patterns_results, "New Patterns")
        
        # Performance analysis tab
        self.performance_results = QTextEdit()
        self.performance_results.setFont(QFont("Courier", 9))
        self.performance_results.setReadOnly(True)
        self.analysis_results_tabs.addTab(self.performance_results, "Performance")
        
        # Predictive analysis tab
        self.predictive_results = QTextEdit()
        self.predictive_results.setFont(QFont("Courier", 9))
        self.predictive_results.setReadOnly(True)
        self.analysis_results_tabs.addTab(self.predictive_results, "Predictions")
        
        # Root cause analysis tab
        self.root_cause_results = QTextEdit()
        self.root_cause_results.setFont(QFont("Courier", 9))
        self.root_cause_results.setReadOnly(True)
        self.analysis_results_tabs.addTab(self.root_cause_results, "Root Cause")
        
        # System health tab
        self.health_results = QTextEdit()
        self.health_results.setFont(QFont("Courier", 9))
        self.health_results.setReadOnly(True)
        self.analysis_results_tabs.addTab(self.health_results, "System Health")
        
        # Learning insights tab
        self.learning_results = QTextEdit()
        self.learning_results.setFont(QFont("Courier", 9))
        self.learning_results.setReadOnly(True)
        self.analysis_results_tabs.addTab(self.learning_results, "AI Learning")
        
        analysis_layout.addWidget(self.analysis_results_tabs)
        
        right_panel.addTab(analysis_tab, "Fault Analysis")
        
        # Git interface tab
        try:
            self.git_tab = GitMainInterface(self.repo_manager)
            right_panel.addTab(self.git_tab, "Git")
        except Exception as e:
            print(f"Warning: Git interface not available: {e}")
        
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
        
        # Request sudo password before starting build
        password = SudoPasswordDialog.get_sudo_password(self)
        if not password:
            return  # User cancelled
        
        # Set sudo password in build engine
        self.build_engine.set_sudo_password(password)
        
        # Use the most recent config for now
        config_path = configs[0]['path']
        
        try:
            build_id = self.build_engine.start_build(config_path)
            self.current_build_id = build_id
            
            # Enable build monitoring
            self.monitor_thread.set_build_id(build_id)
            self.monitor_thread.start()
            print("✓ Build monitoring enabled")
            
            # Start live logs refresh
            self.logs_refresh_timer.start(2000)
            
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
        # Load build-specific documents
        self.load_build_documents(build_id)
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
        
        # Update progress - count only truly completed stages
        if build['total_stages'] > 0:
            # Count stages that are actually 'success' status
            completed_count = sum(1 for stage in stages if isinstance(stage, dict) and stage.get('status') == 'success')
            progress = (completed_count / build['total_stages']) * 100
            self.progress_bar.setValue(int(min(progress, 100)))  # Cap at 100%
        else:
            self.progress_bar.setValue(0)
        
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
            # Always update live logs when build details change
            self.update_live_logs(build_details)
            # Update refresh button state
            self.refresh_logs_btn.setText(f"Refresh ({datetime.now().strftime('%H:%M:%S')})")
    
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
            # Return to browse mode when search is cleared
            self.browse_all_documents()
            return
        
        try:
            # Search documents across all builds
            documents = self.db.search_documents(query)
            
            # Set to 5 columns for search results
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
            
            # Update status
            if documents:
                self.document_viewer.setPlainText(f"Found {len(documents)} documents matching '{query}'\n\nClick on a document to view its content.")
            else:
                self.document_viewer.setPlainText(f"No documents found matching '{query}'")
                
        except Exception as e:
            QMessageBox.warning(self, "Search Error", f"Failed to search documents: {str(e)}")
    
    def load_build_documents(self, build_id: str):
        """Load documents for a specific build"""
        self.current_build_id = build_id
        self.load_build_documents_display(build_id)
    
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
        # Stop live logs refresh for completed builds
        self.logs_refresh_timer.stop()
        # Refresh documents for completed build
        if self.current_build_id:
            self.load_build_documents(self.current_build_id)
            self.refresh_logs_manually()
    
    def refresh_current_build_documents(self):
        """Refresh documents for current build"""
        if self.current_build_id:
            self.load_build_documents(self.current_build_id)
            self.update_document_stats()
    
    def view_build_document(self, item):
        """View selected build document content"""
        row = item.row()
        if row >= 0:
            # Get document data from the first column item
            doc_item = self.build_documents_table.item(row, 0)
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
                    
                    self.build_document_viewer.setPlainText(content)
    
    def refresh_logs_manually(self):
        """Manually refresh logs for current build"""
        if self.current_build_id:
            try:
                build_details = self.db.get_build_details(self.current_build_id)
                if build_details:
                    self.update_live_logs(build_details)
            except Exception as e:
                print(f"Error refreshing logs: {e}")
    
    def refresh_system_status(self):
        """Refresh system status display"""
        try:
            import subprocess
            
            # Get build-related processes
            result = subprocess.run(
                ['ps', 'aux'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                build_processes = []
                
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['python', 'bash', 'make', 'gcc', 'configure']):
                        if 'grep' not in line and line.strip():
                            build_processes.append(line)
                
                # Format process status
                process_text = f"Active Build Processes ({len(build_processes)} found):\n\n"
                for i, proc in enumerate(build_processes[:10]):  # Show top 10
                    parts = proc.split()
                    if len(parts) >= 11:
                        pid = parts[1]
                        cpu = parts[2]
                        mem = parts[3]
                        command = ' '.join(parts[10:])[:80] + '...' if len(' '.join(parts[10:])) > 80 else ' '.join(parts[10:])
                        process_text += f"PID {pid}: {cpu}% CPU, {mem}% MEM\n{command}\n\n"
                
                self.process_status.setPlainText(process_text)
                
                # Update build activity
                if self.current_build_id:
                    build_details = self.db.get_build_details(self.current_build_id)
                    if build_details:
                        build = build_details.get('build', {})
                        stages = build_details.get('stages', [])
                        
                        activity_text = f"Current Build: {self.current_build_id}\n"
                        activity_text += f"Status: {build.get('status', 'unknown')}\n"
                        activity_text += f"Progress: {build.get('completed_stages', 0)}/{build.get('total_stages', 0)} stages\n\n"
                        
                        # Show current stage status
                        running_stages = [s for s in stages if isinstance(s, dict) and s.get('status') == 'running']
                        if running_stages:
                            activity_text += "Currently Running:\n"
                            for stage in running_stages:
                                activity_text += f"• {stage.get('stage_name', 'Unknown')}\n"
                        
                        # Show recent completed stages
                        completed_stages = [s for s in stages if isinstance(s, dict) and s.get('status') == 'success']
                        if completed_stages:
                            activity_text += f"\nCompleted Stages ({len(completed_stages)}):\n"
                            for stage in completed_stages[-3:]:  # Show last 3
                                activity_text += f"✓ {stage.get('stage_name', 'Unknown')}\n"
                        
                        self.build_activity.setPlainText(activity_text)
                    else:
                        self.build_activity.setPlainText("No active build")
                else:
                    self.build_activity.setPlainText("No build selected")
                
                # Update refresh button
                self.refresh_status_btn.setText(f"Refresh ({datetime.now().strftime('%H:%M:%S')})")
            
        except Exception as e:
            self.process_status.setPlainText(f"Error getting system status: {str(e)}")
            self.build_activity.setPlainText("Status unavailable")
    
    def on_build_error(self, data):
        print(f"Build error: {data.get('error', 'Unknown error')}")
        self.monitor_thread.stop()
        self.start_build_action.setEnabled(True)
        self.cancel_build_action.setEnabled(False)
        self.update_document_stats()
    
    def on_sudo_required(self, data):
        """Handle sudo password request during build"""
        password = SudoPasswordDialog.get_sudo_password(self)
        if password:
            self.build_engine.set_sudo_password(password)
            # Resume the build stage that was waiting for password
            # This would require more complex build engine modifications
        else:
            # User cancelled - cancel the build
            self.build_engine.cancel_build(data['build_id'])
    
    def on_package_cached(self, package_name: str, cache_info: dict):
        """Handle package successfully cached - update repository view"""
        print(f"📦 Package {package_name} cached - updating repository view")
        
        # Update git tab repository files if available
        if hasattr(self, 'git_tab'):
            self.git_tab.update_repo_files()
        
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
                # Update git tab if available
                if hasattr(self, 'git_tab'):
                    self.git_tab.refresh_all()
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
                # Update git tab if available
                if hasattr(self, 'git_tab'):
                    self.git_tab.repo_manager = self.repo_manager
                    self.git_tab.refresh_all()
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
            if not isinstance(build_details, dict):
                return
                
            stages = build_details.get('stages', [])
            documents = build_details.get('documents', [])
            
            # Ensure stages and documents are lists
            if not isinstance(stages, list):
                stages = []
            if not isinstance(documents, list):
                documents = []
            
            # Build live log content from stages and real-time documents
            log_content = ""
            
            # Sort documents by creation time for chronological order
            valid_docs = [doc for doc in documents if isinstance(doc, dict)]
            sorted_docs = sorted(valid_docs, key=lambda x: x.get('created_at', datetime.min))
            
            # Group documents by stage for better organization
            stage_docs = {}
            general_docs = []
            
            for doc in sorted_docs:
                if not isinstance(doc, dict):
                    continue
                if doc.get('document_type') == 'log':
                    metadata = doc.get('metadata', {})
                    if isinstance(metadata, dict):
                        stage_order = metadata.get('stage_order')
                        if stage_order is not None:
                            if stage_order not in stage_docs:
                                stage_docs[stage_order] = []
                            stage_docs[stage_order].append(doc)
                        else:
                            general_docs.append(doc)
            
            # Add general documents first (config, setup, etc.)
            for doc in general_docs:
                if not isinstance(doc, dict):
                    continue
                metadata = doc.get('metadata', {})
                title = doc.get('title', '')
                if isinstance(metadata, dict) and isinstance(title, str):
                    if 'setup' in metadata or 'config' in title.lower():
                        log_content += f"=== {title} ===\n"
                        log_content += str(doc.get('content', '')) + "\n\n"
            
            # Add stage-specific content in order
            valid_stages = [stage for stage in stages if isinstance(stage, dict)]
            for stage in valid_stages:
                stage_order = stage.get('stage_order')
                stage_name = stage.get('stage_name', 'Unknown')
                stage_status = stage.get('status', 'unknown')
                log_content += f"=== {stage_name} ({stage_status}) ===\n"
                
                # Add real-time documents for this stage
                if stage_order in stage_docs:
                    for doc in stage_docs[stage_order]:
                        if not isinstance(doc, dict):
                            continue
                        metadata = doc.get('metadata', {})
                        if isinstance(metadata, dict):
                            if metadata.get('progress'):
                                # Show progress updates
                                line_count = metadata.get('line_count', 0)
                                log_content += f"[Progress: {line_count} lines processed]\n"
                                # Show recent output from progress document
                                content = str(doc.get('content', ''))
                                content_lines = content.split('\n')
                                for line in content_lines:
                                    if line.startswith('Recent output:'):
                                        # Show the recent output section
                                        remaining_lines = content_lines[content_lines.index(line):]
                                        log_content += '\n'.join(remaining_lines) + "\n"
                                        break
                            elif metadata.get('error_line'):
                                # Show error lines immediately
                                log_content += f"ERROR: {doc.get('content', '')}\n"
                            elif metadata.get('warnings'):
                                # Show warnings summary
                                warning_count = metadata.get('warning_count', 0)
                                log_content += f"[{warning_count} warnings collected]\n"
                
                # Add final stage output if available
                output_log = stage.get('output_log')
                error_log = stage.get('error_log')
                if output_log:
                    log_content += str(output_log) + "\n"
                if error_log:
                    log_content += "ERRORS:\n" + str(error_log) + "\n"
                log_content += "\n"
            
            # Add current status
            build = build_details.get('build', {})
            if isinstance(build, dict):
                log_content += f"\n=== BUILD STATUS ===\n"
                log_content += f"Status: {build.get('status', 'unknown')}\n"
                log_content += f"Completed Stages: {build.get('completed_stages', 0)}/{build.get('total_stages', 0)}\n"
            
            # Add timestamp
            log_content += f"Last Updated: {datetime.now().strftime('%H:%M:%S')}\n"
            
            # Update logs text
            self.logs_text.setPlainText(log_content)
            
            # Auto-scroll to bottom for live updates if enabled
            if self.auto_scroll_btn.isChecked():
                scrollbar = self.logs_text.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            # Silently handle errors to avoid spam
            pass
    
    def load_all_documents(self):
        """Load all documents from all builds (deprecated - use browse_all_documents)"""
        self.browse_all_documents()
    
    def browse_all_documents(self):
        """Browse all documents with pagination"""
        self.current_page = 1
        self.load_documents_page()
    
    def load_documents_page(self):
        """Load documents for current page (Document Browser tab)"""
        try:
            offset = (self.current_page - 1) * self.page_size
            
            # Get total count
            self.total_documents = self.db.get_documents_count()
            self.total_pages = max(1, (self.total_documents + self.page_size - 1) // self.page_size)
            
            # Get documents for current page
            documents = self.db.get_documents_paginated(offset, self.page_size)
            
            # Always use 5 columns for document browser
            self.documents_table.setColumnCount(5)
            self.documents_table.setHorizontalHeaderLabels(["Build ID", "Type", "Title", "Date", "Size"])
            
            info_text = f"Browsing all documents (Page {self.current_page} of {self.total_pages}, {self.total_documents} total)"
            
            self.documents_table.setRowCount(len(documents))
            
            for i, doc in enumerate(documents):
                self.documents_table.setItem(i, 0, QTableWidgetItem(doc['build_id']))
                self.documents_table.setItem(i, 1, QTableWidgetItem(doc['document_type']))
                self.documents_table.setItem(i, 2, QTableWidgetItem(doc['title']))
                self.documents_table.setItem(i, 3, QTableWidgetItem(doc['created_at'].strftime('%Y-%m-%d %H:%M:%S')))
                self.documents_table.setItem(i, 4, QTableWidgetItem(f"{len(doc['content'])} chars"))
                # Store document data for viewing
                self.documents_table.item(i, 0).setData(Qt.UserRole, doc)
            
            # Update pagination controls
            self.update_pagination_controls()
            
            if documents:
                self.document_viewer.setPlainText(f"{info_text}\n\nClick on a document to view its content.")
            else:
                self.document_viewer.setPlainText(f"{info_text}\n\nNo documents found.")
                
        except Exception as e:
            print(f"Error loading documents page: {e}")
            self.document_viewer.setPlainText(f"Error loading documents: {str(e)}")
    
    def load_build_documents_display(self, build_id: str):
        """Load documents for a specific build (Build Documents tab)"""
        try:
            documents = self.db.get_build_documents(build_id)
            
            # Set to 4 columns for build-specific view
            self.build_documents_table.setColumnCount(4)
            self.build_documents_table.setHorizontalHeaderLabels(["Type", "Title", "Date", "Size"])
            
            self.build_documents_table.setRowCount(len(documents))
            for i, doc in enumerate(documents):
                self.build_documents_table.setItem(i, 0, QTableWidgetItem(doc['document_type']))
                self.build_documents_table.setItem(i, 1, QTableWidgetItem(doc['title']))
                self.build_documents_table.setItem(i, 2, QTableWidgetItem(doc['created_at'].strftime('%Y-%m-%d %H:%M:%S')))
                self.build_documents_table.setItem(i, 3, QTableWidgetItem(f"{len(doc['content'])} chars"))
                
                # Store document data for viewing
                self.build_documents_table.item(i, 0).setData(Qt.UserRole, doc)
            
            if documents:
                self.build_document_viewer.setPlainText(f"Build {build_id} has {len(documents)} documents\n\nClick on a document to view its content.")
            else:
                self.build_document_viewer.setPlainText(f"No documents found for build {build_id}")
                
        except Exception as e:
            print(f"Error loading build documents: {e}")
            self.build_document_viewer.setPlainText(f"Error loading documents: {str(e)}")
    
    def update_pagination_controls(self):
        """Update pagination button states and labels"""
        self.page_info_label.setText(f"Page {self.current_page} of {self.total_pages} ({self.total_documents} docs)")
        
        # Enable/disable buttons
        self.first_page_btn.setEnabled(self.current_page > 1)
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages)
        self.last_page_btn.setEnabled(self.current_page < self.total_pages)
    
    def go_to_first_page(self):
        """Go to first page"""
        self.current_page = 1
        self.load_documents_page()
    
    def go_to_prev_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_documents_page()
    
    def go_to_next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_documents_page()
    
    def go_to_last_page(self):
        """Go to last page"""
        self.current_page = self.total_pages
        self.load_documents_page()
    
    def change_page_size(self):
        """Change page size and reload"""
        self.page_size = int(self.page_size_combo.currentText())
        self.current_page = 1  # Reset to first page
        self.load_documents_page()
    

    
    def setup_lfs_permissions_interactive(self):
        """Interactive LFS permissions setup with sudo password dialog"""
        try:
            password = SudoPasswordDialog.get_sudo_password(self, "LFS Setup Required", 
                "LFS directory permissions need to be configured for package copying.")
            if not password:
                return False
            
            import subprocess
            import tempfile
            import os
            
            # Create askpass script
            askpass_script = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh')
            askpass_script.write(f'#!/bin/bash\necho "{password}"\n')
            askpass_script.close()
            os.chmod(askpass_script.name, 0o755)
            
            # Set environment
            env = os.environ.copy()
            env['SUDO_ASKPASS'] = askpass_script.name
            
            try:
                # Setup LFS directories
                subprocess.run(['sudo', '-A', 'mkdir', '-p', '/mnt/lfs/sources'], 
                             env=env, check=True)
                subprocess.run(['sudo', '-A', 'chmod', '777', '/mnt/lfs/sources'], 
                             env=env, check=True)
                
                self.statusBar().showMessage("✓ LFS permissions configured successfully", 5000)
                return True
                
            finally:
                # Cleanup askpass script
                try:
                    os.unlink(askpass_script.name)
                except:
                    pass
                    
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Setup Error", f"Failed to setup LFS permissions: {e}")
            return False
        except Exception as e:
            QMessageBox.critical(self, "Setup Error", f"LFS setup failed: {str(e)}")
            return False
    
    def export_fault_patterns(self):
        """Export fault patterns to JSON file"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Fault Patterns", 
                f"lfs_fault_patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON Files (*.json)"
            )
            
            if filename:
                result = self.fault_analyzer.export_patterns(os.path.basename(filename))
                if "Export failed" in result:
                    QMessageBox.warning(self, "Export Failed", result)
                else:
                    QMessageBox.information(self, "Export Successful", f"Patterns exported to: {result}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export patterns: {str(e)}")
    
    def import_fault_patterns(self):
        """Import fault patterns from JSON file"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Import Fault Patterns", "",
                "JSON Files (*.json)"
            )
            
            if filename:
                result = self.fault_analyzer.import_patterns(filename)
                if result['success']:
                    QMessageBox.information(self, "Import Successful", result['message'])
                else:
                    QMessageBox.warning(self, "Import Failed", result['error'])
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import patterns: {str(e)}")
    
    def run_fault_analysis(self):
        """Run comprehensive fault analysis on recent build failures"""
        try:
            days = int(self.days_combo.currentText())
            
            # Show progress
            self.analysis_results.setPlainText("Running comprehensive fault analysis...")
            self.stage_results.setPlainText("Analyzing stage failures...")
            self.trends_results.setPlainText("Analyzing trends...")
            self.new_patterns_results.setPlainText("Detecting new patterns...")
            self.performance_results.setPlainText("Analyzing performance correlation...")
            self.predictive_results.setPlainText("Running predictive analysis...")
            self.root_cause_results.setPlainText("Analyzing root causes...")
            self.learning_results.setPlainText("Analyzing learning effectiveness...")
            QApplication.processEvents()
            
            # Run comprehensive analysis
            analysis_result = self.fault_analyzer.analyze_comprehensive(days)
            
            # Format and display results in different tabs
            if 'error' in analysis_result:
                error_msg = f"❌ Analysis Error: {analysis_result['error']}"
                self.analysis_results.setPlainText(error_msg)
                self.stage_results.setPlainText(error_msg)
                self.trends_results.setPlainText(error_msg)
                self.new_patterns_results.setPlainText(error_msg)
            else:
                # Main analysis results
                if 'failure_analysis' in analysis_result:
                    main_text = self._format_fault_analysis_results(analysis_result['failure_analysis'])
                    self.analysis_results.setPlainText(main_text)
                
                # Stage analysis results
                if 'stage_analysis' in analysis_result:
                    stage_text = self._format_stage_analysis_results(analysis_result['stage_analysis'])
                    self.stage_results.setPlainText(stage_text)
                
                # Trends and success rates
                if 'trend_analysis' in analysis_result and 'success_rates' in analysis_result:
                    trends_text = self._format_trends_and_success_results(
                        analysis_result['trend_analysis'], 
                        analysis_result['success_rates']
                    )
                    self.trends_results.setPlainText(trends_text)
                
                # New patterns
                if 'new_patterns' in analysis_result:
                    patterns_text = self._format_new_patterns_results(analysis_result['new_patterns'])
                    self.new_patterns_results.setPlainText(patterns_text)
                
                # Performance analysis
                if 'performance_analysis' in analysis_result:
                    performance_text = self._format_performance_results(analysis_result['performance_analysis'])
                    self.performance_results.setPlainText(performance_text)
                
                # Predictive analysis for recent builds
                predictive_text = self._format_predictive_analysis_results()
                self.predictive_results.setPlainText(predictive_text)
                
                # Root cause analysis for recent failures
                root_cause_text = self._format_root_cause_analysis_results()
                self.root_cause_results.setPlainText(root_cause_text)
                
                # Learning insights
                learning_text = self._format_learning_insights_results(days)
                self.learning_results.setPlainText(learning_text)
            
        except Exception as e:
            error_msg = f"❌ Analysis failed: {str(e)}"
            self.analysis_results.setPlainText(error_msg)
            self.stage_results.setPlainText(error_msg)
            self.trends_results.setPlainText(error_msg)
            self.new_patterns_results.setPlainText(error_msg)
            self.learning_results.setPlainText(error_msg)
    
    def _format_fault_analysis_results(self, analysis_result: dict) -> str:
        """Format fault analysis results for display"""
        if not analysis_result or 'patterns' not in analysis_result:
            return "No analysis results available"
        
        result_lines = []
        result_lines.append(f"🔍 FAULT ANALYSIS RESULTS")
        result_lines.append(f"📊 {analysis_result.get('summary', 'Analysis completed')}")
        result_lines.append(f"📈 Total Failures: {analysis_result.get('total_failures', 0)}")
        result_lines.append(f"🔬 Analyzed Builds: {analysis_result.get('analyzed_builds', 0)}")
        result_lines.append("")
        
        patterns = analysis_result.get('patterns', [])
        if patterns:
            result_lines.append("🚨 DETECTED ISSUES:")
            result_lines.append("=" * 60)
            
            for pattern in patterns:
                severity_icon = {
                    'Critical': '🔴',
                    'High': '🟠', 
                    'Medium': '🟡',
                    'Low': '🟢'
                }.get(pattern['severity'], '⚪')
                
                result_lines.append(f"{severity_icon} {pattern['name']} ({pattern['severity']})")
                result_lines.append(f"   📊 Occurrences: {pattern['count']}")
                result_lines.append(f"   📝 Description: {pattern['description']}")
                result_lines.append(f"   💡 Solution: {pattern['solution']}")
                
                if pattern.get('auto_fix_command'):
                    result_lines.append(f"   🔧 Auto-fix: {pattern['auto_fix_command']}")
                
                if pattern.get('most_common_stage'):
                    result_lines.append(f"   🎯 Most Common Stage: {pattern['most_common_stage']}")
                
                if pattern.get('recent_builds'):
                    recent_ids = [b['build_id'] for b in pattern['recent_builds'][-3:]]
                    result_lines.append(f"   🕒 Recent Builds: {', '.join(recent_ids)}")
                
                result_lines.append("")
        
        recommendations = analysis_result.get('recommendations', [])
        if recommendations:
            result_lines.append("💡 RECOMMENDATIONS:")
            result_lines.append("=" * 60)
            for rec in recommendations:
                result_lines.append(f"• {rec}")
            result_lines.append("")
        
        return "\n".join(result_lines)
    
    def _format_stage_analysis_results(self, stage_analysis: dict) -> str:
        """Format stage analysis results for display"""
        if 'error' in stage_analysis:
            return f"❌ Stage Analysis Error: {stage_analysis['error']}"
        
        result_lines = []
        result_lines.append("🎯 STAGE FAILURE ANALYSIS")
        result_lines.append("=" * 60)
        
        stages = stage_analysis.get('stages', [])
        if stages:
            result_lines.append(f"📊 Total Stage Failures: {stage_analysis.get('total_stage_failures', 0)}")
            if stage_analysis.get('most_problematic'):
                result_lines.append(f"⚠️  Most Problematic Stage: {stage_analysis['most_problematic']}")
            result_lines.append("")
            
            result_lines.append("📈 STAGE BREAKDOWN:")
            result_lines.append("-" * 60)
            
            for stage in stages:
                failure_rate = stage['failure_rate']
                rate_icon = "🔴" if failure_rate > 50 else "🟠" if failure_rate > 25 else "🟡" if failure_rate > 10 else "🟢"
                
                result_lines.append(f"{rate_icon} {stage['stage_name']}")
                result_lines.append(f"   Failures: {stage['failure_count']} | Successes: {stage['success_count']}")
                result_lines.append(f"   Failure Rate: {failure_rate}%")
                if stage['avg_duration'] > 0:
                    result_lines.append(f"   Avg Duration: {stage['avg_duration']} minutes")
                result_lines.append("")
        else:
            result_lines.append("✅ No stage failures found in the specified period")
        
        return "\n".join(result_lines)
    
    def _format_trends_and_success_results(self, trend_analysis: dict, success_rates: dict) -> str:
        """Format trends and success rate results for display"""
        result_lines = []
        
        # Trends section
        result_lines.append("📈 FAILURE TRENDS ANALYSIS")
        result_lines.append("=" * 60)
        
        if 'error' in trend_analysis:
            result_lines.append(f"❌ Trend Analysis Error: {trend_analysis['error']}")
        else:
            trend_direction = trend_analysis.get('trend_direction', 'unknown')
            trend_percentage = trend_analysis.get('trend_percentage', 0)
            
            direction_icon = {
                'improving': '📉 ✅',
                'worsening': '📈 ⚠️',
                'stable': '➡️ 📊'
            }.get(trend_direction, '❓')
            
            result_lines.append(f"{direction_icon} Trend: {trend_direction.upper()} ({trend_percentage:+.1f}%)")
            result_lines.append(f"Current Period: {trend_analysis.get('current_period_failures', 0)} failures")
            result_lines.append(f"Previous Period: {trend_analysis.get('previous_period_failures', 0)} failures")
            result_lines.append("")
            
            weekly_data = trend_analysis.get('weekly_breakdown', [])
            if weekly_data:
                result_lines.append("📅 WEEKLY BREAKDOWN:")
                for week_data in weekly_data:
                    result_lines.append(f"   {week_data['week']}: {week_data['failures']} failures")
                result_lines.append("")
        
        # Success rates section
        result_lines.append("✅ SUCCESS RATE ANALYSIS")
        result_lines.append("=" * 60)
        
        if 'error' in success_rates:
            result_lines.append(f"❌ Success Rate Error: {success_rates['error']}")
        else:
            overall_rate = success_rates.get('overall_success_rate', 0)
            rate_icon = "🟢" if overall_rate > 80 else "🟡" if overall_rate > 60 else "🟠" if overall_rate > 40 else "🔴"
            
            result_lines.append(f"{rate_icon} Overall Success Rate: {overall_rate}%")
            result_lines.append(f"📊 Total Builds: {success_rates.get('total_builds', 0)}")
            result_lines.append(f"✅ Successful: {success_rates.get('successful_builds', 0)}")
            result_lines.append("")
            
            if success_rates.get('most_reliable_stage'):
                most_reliable = success_rates['most_reliable_stage']
                result_lines.append(f"🏆 Most Reliable Stage: {most_reliable['stage_name']} ({most_reliable['success_rate']}%)")
            
            if success_rates.get('least_reliable_stage'):
                least_reliable = success_rates['least_reliable_stage']
                result_lines.append(f"⚠️  Least Reliable Stage: {least_reliable['stage_name']} ({least_reliable['success_rate']}%)")
            
            result_lines.append("")
            
            stage_rates = success_rates.get('stage_success_rates', [])
            if stage_rates:
                result_lines.append("📊 STAGE SUCCESS RATES:")
                result_lines.append("-" * 60)
                for stage in sorted(stage_rates, key=lambda x: x['success_rate'], reverse=True):
                    rate = stage['success_rate']
                    rate_icon = "🟢" if rate > 90 else "🟡" if rate > 75 else "🟠" if rate > 50 else "🔴"
                    result_lines.append(f"{rate_icon} {stage['stage_name']}: {rate}% ({stage['successes']}/{stage['total_attempts']})")
        
        return "\n".join(result_lines)
    
    def _format_new_patterns_results(self, new_patterns: dict) -> str:
        """Format new pattern detection results for display"""
        result_lines = []
        result_lines.append("🤖 NEW PATTERN DETECTION (ML Analysis)")
        result_lines.append("=" * 60)
        
        if 'error' in new_patterns:
            result_lines.append(f"❌ Pattern Detection Error: {new_patterns['error']}")
            return "\n".join(result_lines)
        
        result_lines.append(f"📊 {new_patterns.get('summary', 'Analysis completed')}")
        result_lines.append(f"🔍 Analyzed Lines: {new_patterns.get('total_analyzed_lines', 0)}")
        result_lines.append("")
        
        patterns = new_patterns.get('new_patterns', [])
        if patterns:
            result_lines.append("🆕 SUGGESTED NEW PATTERNS:")
            result_lines.append("-" * 60)
            
            for i, pattern in enumerate(patterns, 1):
                severity_icon = {
                    'Critical': '🔴',
                    'High': '🟠',
                    'Medium': '🟡', 
                    'Low': '🟢'
                }.get(pattern.get('suggested_severity', 'Medium'), '⚪')
                
                result_lines.append(f"{i}. {severity_icon} {pattern['suggested_name']} ({pattern.get('suggested_severity', 'Medium')})")
                result_lines.append(f"   📊 Occurrences: {pattern['occurrences']}")
                result_lines.append(f"   📝 Error Text: {pattern['error_text'][:100]}...")
                result_lines.append(f"   🔍 Suggested Pattern: {pattern['suggested_pattern'][:80]}...")
                result_lines.append("")
        else:
            result_lines.append("✅ No new patterns detected - existing patterns cover all common errors")
        
        result_lines.append("")
        result_lines.append("💡 TIP: Use 'Export Patterns' to save current patterns, then 'Import Patterns' to load community contributions")
        
        return "\n".join(result_lines)
    
    def show_learning_insights(self):
        """Show current learning insights and effectiveness"""
        try:
            days = int(self.days_combo.currentText())
            self.learning_results.setPlainText("Analyzing learning effectiveness...")
            QApplication.processEvents()
            
            learning_text = self._format_learning_insights_results(days)
            self.learning_results.setPlainText(learning_text)
            
            # Switch to learning insights tab
            self.analysis_results_tabs.setCurrentWidget(self.learning_results)
            
        except Exception as e:
            self.learning_results.setPlainText(f"❌ Learning insights failed: {str(e)}")
    
    def _format_learning_insights_results(self, days: int = 30) -> str:
        """Format learning insights and effectiveness results"""
        result_lines = []
        result_lines.append("🧠 AI LEARNING INSIGHTS & EFFECTIVENESS")
        result_lines.append("=" * 60)
        result_lines.append(f"Analysis Period: Last {days} days")
        result_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        result_lines.append("")
        
        try:
            # Get guidance effectiveness from fault analyzer
            effectiveness = self.fault_analyzer.get_guidance_effectiveness(days)
            
            if effectiveness and effectiveness.get('effectiveness_stats'):
                result_lines.append("📊 INTELLIGENT GUIDANCE EFFECTIVENESS:")
                result_lines.append("-" * 60)
                
                for stat in effectiveness['effectiveness_stats']:
                    total_attempts = stat.get('total_attempts', 0)
                    successful_attempts = stat.get('successful_attempts', 0)
                    success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0
                    avg_recovery_time = stat.get('avg_recovery_time', 0)
                    
                    success_icon = "🟢" if success_rate > 80 else "🟡" if success_rate > 60 else "🟠" if success_rate > 40 else "🔴"
                    
                    result_lines.append(f"{success_icon} {stat.get('recovery_type', 'Unknown')} Guidance:")
                    result_lines.append(f"   Success Rate: {success_rate:.1f}% ({successful_attempts}/{total_attempts})")
                    if avg_recovery_time > 0:
                        result_lines.append(f"   Avg Recovery Time: {avg_recovery_time:.1f} seconds")
                    result_lines.append("")
                
                # Top effective patterns
                if effectiveness.get('top_effective_patterns'):
                    result_lines.append("🏆 MOST EFFECTIVE PATTERNS:")
                    result_lines.append("-" * 60)
                    
                    for pattern in effectiveness['top_effective_patterns']:
                        pattern_name = pattern.get('pattern_name', 'Unknown')
                        usage_count = pattern.get('usage_count', 0)
                        success_rate = pattern.get('success_rate', 0)
                        
                        success_icon = "🟢" if success_rate > 80 else "🟡" if success_rate > 60 else "🟠"
                        result_lines.append(f"{success_icon} {pattern_name}")
                        result_lines.append(f"   Usage: {usage_count} times | Success: {success_rate:.1f}%")
                        result_lines.append("")
            else:
                result_lines.append("📊 INTELLIGENT GUIDANCE STATUS:")
                result_lines.append("-" * 60)
                result_lines.append("🔄 Learning system is active and collecting data")
                result_lines.append("📈 Effectiveness metrics will appear after guidance is used")
                result_lines.append("")
            
            # Pattern learning progress
            result_lines.append("🔍 PATTERN RECOGNITION LEARNING:")
            result_lines.append("-" * 60)
            
            # Get pattern detection stats from database
            try:
                pattern_stats = self.db.execute_query("""
                    SELECT 
                        COUNT(DISTINCT pattern_id) as unique_patterns,
                        COUNT(*) as total_detections,
                        AVG(confidence_score) as avg_confidence,
                        COUNT(CASE WHEN auto_fix_applied THEN 1 END) as auto_fixes_applied,
                        COUNT(CASE WHEN fix_successful THEN 1 END) as successful_fixes
                    FROM pattern_detections 
                    WHERE detected_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                """, (days,), fetch=True)
                
                if pattern_stats and pattern_stats[0]['total_detections'] > 0:
                    stats = pattern_stats[0]
                    total_detections = stats['total_detections']
                    unique_patterns = stats['unique_patterns']
                    avg_confidence = stats['avg_confidence'] or 0
                    auto_fixes = stats['auto_fixes_applied'] or 0
                    successful_fixes = stats['successful_fixes'] or 0
                    
                    fix_success_rate = (successful_fixes / auto_fixes * 100) if auto_fixes > 0 else 0
                    
                    result_lines.append(f"🎯 Pattern Detections: {total_detections} (across {unique_patterns} unique patterns)")
                    result_lines.append(f"🎯 Average Confidence: {avg_confidence:.1f}%")
                    result_lines.append(f"🔧 Auto-fixes Applied: {auto_fixes}")
                    result_lines.append(f"✅ Fix Success Rate: {fix_success_rate:.1f}% ({successful_fixes}/{auto_fixes})")
                else:
                    result_lines.append("🔄 Pattern detection system is active")
                    result_lines.append("📊 Detection statistics will appear as patterns are found")
                
            except Exception as e:
                result_lines.append(f"⚠️ Pattern stats unavailable: {str(e)}")
            
            result_lines.append("")
            
            # Database learning metrics
            result_lines.append("💾 DATABASE LEARNING METRICS:")
            result_lines.append("-" * 60)
            
            try:
                # Get recent data collection stats
                db_stats = self.db.execute_query("""
                    SELECT 
                        (SELECT COUNT(*) FROM builds WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)) as recent_builds,
                        (SELECT COUNT(*) FROM build_documents WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)) as recent_docs,
                        (SELECT COUNT(*) FROM system_metrics WHERE timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)) as system_metrics,
                        (SELECT COUNT(*) FROM stage_performance WHERE end_time >= DATE_SUB(NOW(), INTERVAL %s DAY)) as performance_records
                """, (days, days, days, days), fetch=True)
                
                if db_stats:
                    stats = db_stats[0]
                    result_lines.append(f"🏗️ Recent Builds Analyzed: {stats.get('recent_builds', 0)}")
                    result_lines.append(f"📄 Documents Collected: {stats.get('recent_docs', 0)}")
                    result_lines.append(f"📊 System Metrics Recorded: {stats.get('system_metrics', 0)}")
                    result_lines.append(f"⚡ Performance Records: {stats.get('performance_records', 0)}")
                
            except Exception as e:
                result_lines.append(f"⚠️ Database stats unavailable: {str(e)}")
            
            result_lines.append("")
            
            # Learning recommendations
            result_lines.append("💡 LEARNING SYSTEM RECOMMENDATIONS:")
            result_lines.append("-" * 60)
            
            # Check if we have enough data for good learning
            try:
                build_count = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM builds WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)",
                    (days,), fetch=True
                )[0]['count']
                
                if build_count < 5:
                    result_lines.append("📈 Run more builds to improve learning accuracy")
                    result_lines.append("🎯 Minimum 5-10 builds recommended for meaningful insights")
                elif build_count < 20:
                    result_lines.append("📊 Good data collection progress")
                    result_lines.append("🎯 Continue building to enhance pattern recognition")
                else:
                    result_lines.append("✅ Excellent data collection for robust learning")
                    result_lines.append("🧠 System has sufficient data for accurate predictions")
                
                # Check for pattern diversity
                failure_count = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM builds WHERE status IN ('failed', 'cancelled') AND start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)",
                    (days,), fetch=True
                )[0]['count']
                
                if failure_count > 0:
                    result_lines.append(f"🔍 {failure_count} failures analyzed for pattern learning")
                    result_lines.append("📚 System is learning from both successes and failures")
                else:
                    result_lines.append("✅ No recent failures - system learning from successful patterns")
                
            except Exception as e:
                result_lines.append(f"⚠️ Unable to generate recommendations: {str(e)}")
            
            result_lines.append("")
            result_lines.append("🔄 CONTINUOUS LEARNING FEATURES:")
            result_lines.append("-" * 60)
            result_lines.append("• 🎯 Real-time pattern detection during builds")
            result_lines.append("• 📊 Historical success rate tracking")
            result_lines.append("• 🔧 Auto-fix command effectiveness monitoring")
            result_lines.append("• 🧠 Machine learning pattern recognition")
            result_lines.append("• 📈 Predictive failure analysis")
            result_lines.append("• 🔍 Root cause correlation analysis")
            result_lines.append("• 💾 Comprehensive data retention for long-term learning")
            result_lines.append("")
            result_lines.append("💡 TIP: The system gets smarter with each build attempt!")
            
        except Exception as e:
            result_lines.append(f"❌ Error generating learning insights: {str(e)}")
            result_lines.append("")
            result_lines.append("🔄 Learning system is active but insights are temporarily unavailable")
        
        return "\n".join(result_lines)

def main():
    app = QApplication(sys.argv)
    window = LFSMainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()