#!/usr/bin/env python3

# Add mirror grading view and reset functionality

import sys
import os

# Read the downloader.py file
with open('/home/scottp/IdeaProjects/LFS/src/build/downloader.py', 'r') as f:
    content = f.read()

# Add reset mirror grade method
reset_method = '''
    def reset_mirror_grade(self, domain: str):
        """Reset mirror grade statistics"""
        if domain in self.mirror_stats:
            del self.mirror_stats[domain]
            self.save_mirror_stats()
            print(f"Reset grade for mirror: {domain}")'''

# Insert after get_user_mirrors method
insert_point = content.find('    def record_mirror_success(self, url: str, download_time: float, file_size: int):')
if insert_point == -1:
    print("Could not find insertion point in downloader.py")
    sys.exit(1)

new_content = content[:insert_point] + reset_method + '\n    \n' + content[insert_point:]

# Write back to downloader.py
with open('/home/scottp/IdeaProjects/LFS/src/build/downloader.py', 'w') as f:
    f.write(new_content)

# Now update the GUI
with open('/home/scottp/IdeaProjects/LFS/src/gui/main_window.py', 'r') as f:
    gui_content = f.read()

# Update mirror management dialog to include graded mirrors
old_dialog = '''        # Mirror list
        self.mirror_table = QTableWidget()
        self.mirror_table.setColumnCount(4)
        self.mirror_table.setHorizontalHeaderLabels(["Package", "Mirror URL", "Priority", "Actions"])
        self.mirror_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.mirror_table)'''

new_dialog = '''        # Tabs for different mirror types
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
        
        # Graded mirrors tab
        graded_tab = QWidget()
        graded_layout = QVBoxLayout(graded_tab)
        
        self.graded_table = QTableWidget()
        self.graded_table.setColumnCount(6)
        self.graded_table.setHorizontalHeaderLabels(["Domain", "Grade", "Success Rate", "Avg Speed", "Total MB", "Actions"])
        self.graded_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        graded_layout.addWidget(self.graded_table)
        
        tab_widget.addTab(graded_tab, "Graded Mirrors")
        
        layout.addWidget(tab_widget)'''

gui_content = gui_content.replace(old_dialog, new_dialog)

# Update refresh_mirrors method to handle both tables
old_refresh = '''    def refresh_mirrors(self):
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
                
                row += 1'''

new_refresh = '''    def refresh_mirrors(self):
        """Refresh mirror list display"""
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
            
            row += 1'''

gui_content = gui_content.replace(old_refresh, new_refresh)

# Add reset mirror grade method
reset_gui_method = '''
    def reset_mirror_grade(self, domain: str):
        """Reset mirror grade"""
        reply = QMessageBox.question(self, 'Reset Mirror Grade', 
                                   f'Reset performance grade for {domain}?\\nThis will clear all statistics and the mirror will start with a neutral grade.',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.downloader.reset_mirror_grade(domain)
                self.refresh_mirrors()
                QMessageBox.information(self, "Grade Reset", f"Reset grade for {domain}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset grade: {str(e)}")'''

# Insert before the BuildConfigDialog class
insert_point = gui_content.find('class BuildConfigDialog(QDialog):')
if insert_point == -1:
    print("Could not find insertion point in main_window.py")
    sys.exit(1)

new_gui_content = gui_content[:insert_point] + reset_gui_method + '\n\n' + gui_content[insert_point:]

# Add QColor import
old_import = '''from PyQt5.QtGui import QFont, QIcon'''
new_import = '''from PyQt5.QtGui import QFont, QIcon, QColor'''

new_gui_content = new_gui_content.replace(old_import, new_import)

# Write back to main_window.py
with open('/home/scottp/IdeaProjects/LFS/src/gui/main_window.py', 'w') as f:
    f.write(new_gui_content)

print("✅ Added mirror grading view and reset functionality")