#!/usr/bin/env python3

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import os
import shutil
import psutil
import subprocess
from pathlib import Path
import json

class StorageManagerDialog(QDialog):
    """Storage management interface for moving data retention to different locations"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Storage Manager - Data Retention Location")
        self.setModal(True)
        self.resize(1000, 700)
        
        # Current storage paths
        self.current_paths = {
            'database': '/var/lib/mysql',
            'builds': '/home/scottp/IdeaProjects/LFS/builds',
            'documents': '/home/scottp/IdeaProjects/LFS/documents',
            'logs': '/home/scottp/IdeaProjects/LFS/logs',
            'repository': '/home/scottp/IdeaProjects/LFS/repository'
        }
        
        # Sudo authentication
        self.sudo_password = None
        self.is_authenticated = False
        
        self.init_ui()
        self.refresh_storage_info()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("📁 Storage Manager - Data Retention Configuration")
        header.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(header)
        
        # Main content in splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Storage overview
        left_panel = self.create_storage_overview()
        splitter.addWidget(left_panel)
        
        # Right panel - File browser
        right_panel = self.create_file_browser()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([400, 600])
        layout.addWidget(splitter)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.clicked.connect(self.apply_changes)
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def create_storage_overview(self):
        """Create storage overview panel"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Current storage locations
        storage_group = QGroupBox("Current Storage Locations")
        storage_layout = QVBoxLayout()
        
        self.storage_tree = QTreeWidget()
        self.storage_tree.setHeaderLabels(["Component", "Path", "Size", "Free Space"])
        self.storage_tree.itemDoubleClicked.connect(self.edit_storage_location)
        
        storage_layout.addWidget(self.storage_tree)
        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)
        
        # Available drives
        drives_group = QGroupBox("Available Storage Devices")
        drives_layout = QVBoxLayout()
        
        self.drives_tree = QTreeWidget()
        self.drives_tree.setHeaderLabels(["Device", "Mount Point", "Total", "Free", "Type"])
        self.drives_tree.itemClicked.connect(self.select_drive)
        
        drives_layout.addWidget(self.drives_tree)
        
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh Drives")
        refresh_btn.clicked.connect(self.refresh_drives)
        button_layout.addWidget(refresh_btn)
        
        debug_btn = QPushButton("🔍 Debug USB")
        debug_btn.clicked.connect(self.debug_usb_detection)
        button_layout.addWidget(debug_btn)
        
        drives_layout.addLayout(button_layout)
        
        drives_group.setLayout(drives_layout)
        layout.addWidget(drives_group)
        
        # Migration status
        status_group = QGroupBox("Migration Status")
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        widget.setLayout(layout)
        return widget
        
    def create_file_browser(self):
        """Create file browser panel"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Navigation
        nav_layout = QHBoxLayout()
        
        self.path_edit = QLineEdit("/")
        self.path_edit.returnPressed.connect(self.navigate_to_path)
        nav_layout.addWidget(QLabel("Path:"))
        nav_layout.addWidget(self.path_edit)
        
        self.up_btn = QPushButton("⬆️ Up")
        self.up_btn.clicked.connect(self.navigate_up)
        nav_layout.addWidget(self.up_btn)
        
        self.home_btn = QPushButton("🏠 Home")
        self.home_btn.clicked.connect(self.navigate_home)
        nav_layout.addWidget(self.home_btn)
        
        layout.addLayout(nav_layout)
        
        # File browser
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["Name", "Size", "Type", "Modified"])
        self.file_tree.itemDoubleClicked.connect(self.navigate_to_item)
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.file_tree)
        
        # Actions
        action_layout = QHBoxLayout()
        
        self.create_folder_btn = QPushButton("📁 New Folder")
        self.create_folder_btn.clicked.connect(self.create_folder)
        action_layout.addWidget(self.create_folder_btn)
        
        self.select_path_btn = QPushButton("✅ Select This Path")
        self.select_path_btn.clicked.connect(self.select_current_path)
        action_layout.addWidget(self.select_path_btn)
        
        layout.addLayout(action_layout)
        
        widget.setLayout(layout)
        return widget
        
    def refresh_storage_info(self):
        """Refresh storage information"""
        self.storage_tree.clear()
        
        for component, path in self.current_paths.items():
            item = QTreeWidgetItem([component, path, self.get_dir_size(path), self.get_free_space(path)])
            
            # Color code based on available space
            free_space = self.get_free_space_bytes(path)
            if free_space < 1024**3:  # Less than 1GB
                item.setBackground(0, QColor(255, 200, 200))
            elif free_space < 5 * 1024**3:  # Less than 5GB
                item.setBackground(0, QColor(255, 255, 200))
            else:
                item.setBackground(0, QColor(200, 255, 200))
                
            self.storage_tree.addTopLevelItem(item)
            
        self.refresh_drives()
        self.navigate_to_path()
        
    def refresh_drives(self):
        """Refresh available drives"""
        self.drives_tree.clear()
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                
                device = partition.device
                mount = partition.mountpoint
                total = self.format_bytes(usage.total)
                free = self.format_bytes(usage.free)
                fstype = partition.fstype
                
                # Create item with USB indicator
                device_name = device
                is_removable = self.is_removable_media(partition)
                if is_removable:
                    device_name = f"🔌 {device} (USB/Removable)"
                    
                item = QTreeWidgetItem([device_name, mount, total, free, fstype])
                
                # Highlight removable media
                if is_removable:
                    item.setBackground(0, QColor(200, 255, 200))  # Light green for USB
                    item.setToolTip(0, "USB/Removable storage device")
                else:
                    item.setBackground(0, QColor(240, 240, 240))  # Light gray for internal
                    
                self.drives_tree.addTopLevelItem(item)
                
            except PermissionError:
                continue
                
    def navigate_to_path(self):
        """Navigate to specified path"""
        path = self.path_edit.text()
        if not os.path.exists(path):
            path = "/"
            self.path_edit.setText(path)
            
        self.file_tree.clear()
        
        try:
            # Add parent directory entry
            if path != "/":
                parent_item = QTreeWidgetItem(["📁 ..", "", "Directory", ""])
                parent_item.setData(0, Qt.UserRole, os.path.dirname(path))
                self.file_tree.addTopLevelItem(parent_item)
                
            # List directory contents
            for item_name in sorted(os.listdir(path)):
                item_path = os.path.join(path, item_name)
                
                if os.path.isdir(item_path):
                    icon = "📁"
                    size = ""
                    item_type = "Directory"
                else:
                    icon = "📄"
                    size = self.format_bytes(os.path.getsize(item_path))
                    item_type = "File"
                    
                modified = self.get_modified_time(item_path)
                
                tree_item = QTreeWidgetItem([f"{icon} {item_name}", size, item_type, modified])
                tree_item.setData(0, Qt.UserRole, item_path)
                self.file_tree.addTopLevelItem(tree_item)
                
        except PermissionError:
            # Try with sudo if permission denied
            if not self.is_authenticated:
                reply = QMessageBox.question(self, "Permission Required", 
                    f"Access denied to {path}. Use sudo to access?",
                    QMessageBox.Yes | QMessageBox.No)
                if reply != QMessageBox.Yes:
                    self.status_text.append(f"Permission denied accessing {path}")
                    return
                    
            success, output = self.run_sudo_command(['ls', '-la', path])
            if success:
                self.parse_sudo_ls_output(path, output)
            else:
                self.status_text.append(f"Permission denied accessing {path}")
            
    def navigate_to_item(self, item):
        """Navigate to selected item"""
        path = item.data(0, Qt.UserRole)
        if os.path.isdir(path):
            self.path_edit.setText(path)
            self.navigate_to_path()
            
    def navigate_up(self):
        """Navigate to parent directory"""
        current = self.path_edit.text()
        parent = os.path.dirname(current)
        if parent != current:
            self.path_edit.setText(parent)
            self.navigate_to_path()
            
    def navigate_home(self):
        """Navigate to home directory"""
        self.path_edit.setText(os.path.expanduser("~"))
        self.navigate_to_path()
        
    def select_drive(self, item):
        """Select drive and navigate to it"""
        mount_point = item.text(1)
        self.path_edit.setText(mount_point)
        self.navigate_to_path()
        
    def create_folder(self):
        """Create new folder"""
        name, ok = QInputDialog.getText(self, "Create Folder", "Folder name:")
        if ok and name:
            current_path = self.path_edit.text()
            new_path = os.path.join(current_path, name)
            
            try:
                os.makedirs(new_path, exist_ok=True)
                self.navigate_to_path()
                self.status_text.append(f"Created folder: {new_path}")
            except PermissionError:
                success, output = self.run_sudo_command(['mkdir', '-p', new_path])
                if success:
                    self.navigate_to_path()
                    self.status_text.append(f"Created folder with sudo: {new_path}")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to create folder: {output}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to create folder: {e}")
                
    def select_current_path(self):
        """Select current path for storage location"""
        current_path = self.path_edit.text()
        
        # Show dialog to select which component to move
        components = list(self.current_paths.keys())
        component, ok = QInputDialog.getItem(self, "Select Component", 
                                           "Which component to move to this location:", 
                                           components, 0, False)
        
        if ok and component:
            self.move_component(component, current_path)
            
    def move_component(self, component, new_path):
        """Move component to new storage location"""
        old_path = self.current_paths[component]
        
        # Confirm move
        reply = QMessageBox.question(self, "Confirm Move", 
                                   f"Move {component} from:\n{old_path}\n\nTo:\n{new_path}\n\nThis operation may take time. Continue?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.perform_migration(component, old_path, new_path)
            
    def perform_migration(self, component, old_path, new_path):
        """Perform actual data migration"""
        try:
            self.status_text.append(f"Starting migration of {component}...")
            
            # Create destination directory
            dest_path = os.path.join(new_path, component)
            os.makedirs(dest_path, exist_ok=True)
            
            if component == 'database':
                self.migrate_database(dest_path)
            else:
                self.migrate_directory(old_path, dest_path)
                
            # Update current paths
            self.current_paths[component] = dest_path
            
            self.status_text.append(f"✅ Successfully migrated {component}")
            self.refresh_storage_info()
            
        except Exception as e:
            self.status_text.append(f"❌ Migration failed: {e}")
            QMessageBox.critical(self, "Migration Error", f"Failed to migrate {component}: {e}")
            
    def migrate_database(self, dest_path):
        """Migrate MySQL database"""
        self.status_text.append("Stopping MySQL service...")
        success, output = self.run_sudo_command(['systemctl', 'stop', 'mysql'])
        if not success:
            raise Exception(f"Failed to stop MySQL: {output}")
        
        try:
            # Copy database files
            self.status_text.append("Copying database files...")
            success, output = self.run_sudo_command(['cp', '-r', '/var/lib/mysql', dest_path])
            if not success:
                raise Exception(f"Failed to copy database: {output}")
            
            # Update MySQL configuration
            config_content = f"""
[mysqld]
datadir = {dest_path}
socket = {dest_path}/mysql.sock
"""
            
            config_file = '/etc/mysql/conf.d/custom-datadir.cnf'
            with open('/tmp/mysql_config.tmp', 'w') as f:
                f.write(config_content)
                
            success, output = self.run_sudo_command(['cp', '/tmp/mysql_config.tmp', config_file])
            if not success:
                raise Exception(f"Failed to update MySQL config: {output}")
                
            self.status_text.append("Starting MySQL service...")
            success, output = self.run_sudo_command(['systemctl', 'start', 'mysql'])
            if not success:
                raise Exception(f"Failed to start MySQL: {output}")
            
        except Exception as e:
            # Restore MySQL service
            self.run_sudo_command(['systemctl', 'start', 'mysql'])
            raise e
            
    def migrate_directory(self, old_path, new_path):
        """Migrate regular directory"""
        if os.path.exists(old_path):
            self.status_text.append(f"Copying {old_path} to {new_path}...")
            shutil.copytree(old_path, new_path, dirs_exist_ok=True)
            
            # Verify copy
            if self.verify_copy(old_path, new_path):
                self.status_text.append("Removing old location...")
                shutil.rmtree(old_path)
            else:
                raise Exception("Copy verification failed")
                
    def verify_copy(self, old_path, new_path):
        """Verify directory copy was successful"""
        try:
            old_size = self.get_dir_size_bytes(old_path)
            new_size = self.get_dir_size_bytes(new_path)
            return abs(old_size - new_size) < 1024  # Allow 1KB difference
        except:
            return False
            
    def show_context_menu(self, position):
        """Show context menu for file operations"""
        item = self.file_tree.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        
        if item.text(2) == "Directory":
            menu.addAction("📁 Open", lambda: self.navigate_to_item(item))
            menu.addAction("📋 Copy Path", lambda: self.copy_path(item))
            menu.addAction("🗑️ Delete", lambda: self.delete_item(item))
        else:
            menu.addAction("📋 Copy Path", lambda: self.copy_path(item))
            menu.addAction("🗑️ Delete", lambda: self.delete_item(item))
            
        menu.exec_(self.file_tree.mapToGlobal(position))
        
    def copy_path(self, item):
        """Copy item path to clipboard"""
        path = item.data(0, Qt.UserRole)
        QApplication.clipboard().setText(path)
        self.status_text.append(f"Copied path: {path}")
        
    def delete_item(self, item):
        """Delete selected item"""
        path = item.data(0, Qt.UserRole)
        
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Delete {path}?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                    
                self.navigate_to_path()
                self.status_text.append(f"Deleted: {path}")
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete: {e}")
                
    def edit_storage_location(self, item):
        """Edit storage location"""
        component = item.text(0)
        current_path = item.text(1)
        
        new_path, ok = QInputDialog.getText(self, f"Edit {component} Location", 
                                          "New path:", text=current_path)
        
        if ok and new_path != current_path:
            self.move_component(component, os.path.dirname(new_path))
            
    def apply_changes(self):
        """Apply storage configuration changes"""
        # Save configuration
        config = {
            'storage_paths': self.current_paths,
            'last_updated': QDateTime.currentDateTime().toString()
        }
        
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'storage.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        QMessageBox.information(self, "Success", "Storage configuration saved successfully!")
        self.accept()
        
    def get_dir_size(self, path):
        """Get directory size as formatted string"""
        try:
            return self.format_bytes(self.get_dir_size_bytes(path))
        except:
            return "Unknown"
            
    def get_dir_size_bytes(self, path):
        """Get directory size in bytes"""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total += os.path.getsize(filepath)
                except:
                    continue
        return total
        
    def get_free_space(self, path):
        """Get free space as formatted string"""
        try:
            return self.format_bytes(self.get_free_space_bytes(path))
        except:
            return "Unknown"
            
    def get_free_space_bytes(self, path):
        """Get free space in bytes"""
        try:
            usage = psutil.disk_usage(path)
            return usage.free
        except:
            return 0
            
    def get_modified_time(self, path):
        """Get file modification time"""
        try:
            mtime = os.path.getmtime(path)
            return QDateTime.fromSecsSinceEpoch(int(mtime)).toString("yyyy-MM-dd hh:mm")
        except:
            return "Unknown"
            
    def format_bytes(self, bytes_val):
        """Format bytes as human readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} PB"
        
    def is_removable_media(self, partition):
        """Check if partition is removable media"""
        try:
            device_name = partition.device.replace('/dev/', '')
            
            # Handle different device types
            if device_name.startswith('sd'):  # SCSI/SATA/USB devices
                base_device = device_name.rstrip('0123456789')
            elif device_name.startswith('nvme'):
                base_device = device_name.split('p')[0] if 'p' in device_name else device_name
            elif device_name.startswith('mmcblk'):
                base_device = device_name.split('p')[0] if 'p' in device_name else device_name
            else:
                # For complex names like mapper devices, skip sys check
                base_device = None
            
            # Check if it's a removable device
            if base_device:
                removable_path = f"/sys/block/{base_device}/removable"
                if os.path.exists(removable_path):
                    with open(removable_path, 'r') as f:
                        if f.read().strip() == '1':
                            return True
                            
                # Check if it's a USB device by looking at the device path
                device_path = f"/sys/block/{base_device}"
                if os.path.exists(device_path):
                    try:
                        real_path = os.path.realpath(device_path)
                        if '/usb' in real_path.lower():
                            return True
                    except:
                        pass
                        
        except Exception as e:
            pass
            
        # Check mount point patterns for removable media
        removable_patterns = ['/media/', '/mnt/', '/run/media/', '/Volumes/']
        if any(partition.mountpoint.startswith(pattern) for pattern in removable_patterns):
            return True
            
        # Check filesystem types commonly used on removable media
        removable_fs = ['vfat', 'exfat', 'ntfs', 'hfsplus']
        if partition.fstype.lower() in removable_fs:
            return True
            
        return False
        
    def debug_usb_detection(self):
        """Debug USB device detection"""
        debug_info = []
        debug_info.append("=== USB Device Detection Debug ===")
        
        for partition in psutil.disk_partitions():
            debug_info.append(f"\nDevice: {partition.device}")
            debug_info.append(f"Mountpoint: {partition.mountpoint}")
            debug_info.append(f"Filesystem: {partition.fstype}")
            
            # Check removable status
            device_name = partition.device.replace('/dev/', '')
            base_device = ''.join(c for c in device_name if not c.isdigit())
            
            removable_path = f"/sys/block/{base_device}/removable"
            debug_info.append(f"Removable path: {removable_path}")
            debug_info.append(f"Path exists: {os.path.exists(removable_path)}")
            
            if os.path.exists(removable_path):
                try:
                    with open(removable_path, 'r') as f:
                        removable_value = f.read().strip()
                        debug_info.append(f"Removable value: {removable_value}")
                except Exception as e:
                    debug_info.append(f"Error reading removable: {e}")
                    
            debug_info.append(f"Is removable: {self.is_removable_media(partition)}")
            debug_info.append("-" * 30)
            
        # Show debug dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("USB Detection Debug")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setPlainText("\n".join(debug_info))
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
    def authenticate_sudo(self):
        """Authenticate sudo access"""
        if self.is_authenticated:
            return True
            
        password, ok = QInputDialog.getText(
            self, "Sudo Authentication", 
            "Enter sudo password for administrative operations:",
            QLineEdit.Password
        )
        
        if not ok or not password:
            return False
            
        # Test sudo authentication
        try:
            result = subprocess.run(
                ['sudo', '-S', 'echo', 'test'],
                input=password + '\n',
                text=True,
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.sudo_password = password
                self.is_authenticated = True
                self.status_text.append("✅ Sudo authentication successful")
                return True
            else:
                QMessageBox.warning(self, "Authentication Failed", "Invalid sudo password")
                return False
                
        except Exception as e:
            QMessageBox.warning(self, "Authentication Error", f"Failed to authenticate: {e}")
            return False
            
    def run_sudo_command(self, command):
        """Run command with sudo privileges"""
        if not self.is_authenticated:
            if not self.authenticate_sudo():
                return False, "Authentication required"
                
        try:
            if isinstance(command, str):
                command = command.split()
                
            result = subprocess.run(
                ['sudo', '-S'] + command,
                input=self.sudo_password + '\n',
                text=True,
                capture_output=True,
                timeout=30
            )
            
            return result.returncode == 0, result.stdout + result.stderr
            
        except Exception as e:
            return False, str(e)
            
    def parse_sudo_ls_output(self, path, output):
        """Parse sudo ls -la output and populate file tree"""
        lines = output.strip().split('\n')
        
        # Add parent directory entry
        if path != "/":
            parent_item = QTreeWidgetItem(["📁 ..", "", "Directory", ""])
            parent_item.setData(0, Qt.UserRole, os.path.dirname(path))
            self.file_tree.addTopLevelItem(parent_item)
            
        for line in lines[1:]:  # Skip first line (total)
            if not line or line.startswith('total'):
                continue
                
            parts = line.split()
            if len(parts) < 9:
                continue
                
            permissions = parts[0]
            name = ' '.join(parts[8:])
            
            if name in ['.', '..']:
                continue
                
            item_path = os.path.join(path, name)
            
            if permissions.startswith('d'):
                icon = "📁"
                size = ""
                item_type = "Directory"
            else:
                icon = "📄"
                size = parts[4]
                item_type = "File"
                
            modified = f"{parts[5]} {parts[6]} {parts[7]}"
            
            tree_item = QTreeWidgetItem([f"{icon} {name}", size, item_type, modified])
            tree_item.setData(0, Qt.UserRole, item_path)
            self.file_tree.addTopLevelItem(tree_item)