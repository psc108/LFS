#!/usr/bin/env python3

# Read the current main_window.py
with open('src/gui/main_window.py', 'r') as f:
    content = f.read()

# Add global mirror tab to the manage_mirrors method
old_tab_code = '''        # Graded mirrors tab
        graded_tab = QWidget()
        graded_layout = QVBoxLayout(graded_tab)
        
        self.graded_table = QTableWidget()
        self.graded_table.setColumnCount(6)
        self.graded_table.setHorizontalHeaderLabels(["Domain", "Grade", "Success Rate", "Avg Speed", "Total MB", "Actions"])
        self.graded_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        graded_layout.addWidget(self.graded_table)
        
        tab_widget.addTab(graded_tab, "Graded Mirrors")'''

new_tab_code = '''        # Global mirrors tab
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
        
        tab_widget.addTab(graded_tab, "Graded Mirrors")'''

content = content.replace(old_tab_code, new_tab_code)

# Add methods for global mirror management
global_methods = '''
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
                                   f'Remove global mirror?\\n{mirror_url}',
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
'''

# Insert the global methods before the reset_mirror_grade method
content = content.replace(
    '    def reset_mirror_grade(self, domain: str):',
    global_methods + '\n    def reset_mirror_grade(self, domain: str):'
)

# Update the refresh_mirrors method to include global mirrors
old_refresh = '''    def refresh_mirrors(self):
        """Refresh mirror list display"""
        # Refresh user mirrors
        user_mirrors = self.downloader.load_user_mirrors()'''

new_refresh = '''    def refresh_mirrors(self):
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
        user_mirrors = self.downloader.load_user_mirrors()'''

content = content.replace(old_refresh, new_refresh)

# Write the updated content
with open('src/gui/main_window.py', 'w') as f:
    f.write(content)

print("✅ Added global mirror management to GUI")