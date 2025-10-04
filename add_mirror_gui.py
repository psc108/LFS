#!/usr/bin/env python3

# Add mirror management GUI to Package Manager

import sys
import os

# Read the main_window.py file
with open('/home/scottp/IdeaProjects/LFS/src/gui/main_window.py', 'r') as f:
    content = f.read()

# Add mirror management button to PackageManagerDialog
old_button_layout = '''        self.mirror_stats_btn = QPushButton("Mirror Stats")
        self.mirror_stats_btn.clicked.connect(self.show_mirror_stats)
        button_layout.addWidget(self.mirror_stats_btn)'''

new_button_layout = '''        self.mirror_stats_btn = QPushButton("Mirror Stats")
        self.mirror_stats_btn.clicked.connect(self.show_mirror_stats)
        button_layout.addWidget(self.mirror_stats_btn)
        
        self.manage_mirrors_btn = QPushButton("Manage Mirrors")
        self.manage_mirrors_btn.clicked.connect(self.manage_mirrors)
        button_layout.addWidget(self.manage_mirrors_btn)'''

content = content.replace(old_button_layout, new_button_layout)

# Add mirror management dialog method
mirror_dialog_method = '''
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
        
        # Mirror list
        self.mirror_table = QTableWidget()
        self.mirror_table.setColumnCount(4)
        self.mirror_table.setHorizontalHeaderLabels(["Package", "Mirror URL", "Priority", "Actions"])
        self.mirror_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.mirror_table)
        
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
                                   f'Remove mirror for {package_name}?\\n{mirror_url}',
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
                QMessageBox.critical(self, "Error", f"Failed to remove mirror: {str(e)}")'''

# Insert the method before the BuildConfigDialog class
insert_point = content.find('class BuildConfigDialog(QDialog):')
if insert_point == -1:
    print("Could not find insertion point")
    sys.exit(1)

new_content = content[:insert_point] + mirror_dialog_method + '\n\n' + content[insert_point:]

# Write back to file
with open('/home/scottp/IdeaProjects/LFS/src/gui/main_window.py', 'w') as f:
    f.write(new_content)

print("✅ Added mirror management GUI to Package Manager")