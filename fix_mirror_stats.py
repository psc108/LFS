#!/usr/bin/env python3

# Quick fix for mirror stats dialog - make it scrollable and smaller

import sys
import os

# Read the main_window.py file
with open('/home/scottp/IdeaProjects/LFS/src/gui/main_window.py', 'r') as f:
    content = f.read()

# Replace the show_mirror_stats method
old_method = '''    def show_mirror_stats(self):
        """Show mirror performance statistics"""
        stats = self.downloader.mirror_stats
        if not stats:
            QMessageBox.information(self, "Mirror Statistics", "No mirror statistics available yet.\\nStatistics will be collected as packages are downloaded.")
            return
        
        stats_text = "Mirror Performance Statistics\\n\\n"
        
        # Sort mirrors by grade
        sorted_mirrors = sorted(stats.items(), key=lambda x: self.downloader.get_mirror_grade(x[0]), reverse=True)
        
        for domain, data in sorted_mirrors:
            grade = self.downloader.get_mirror_grade(domain)
            total_attempts = data['successes'] + data['failures']
            success_rate = (data['successes'] / total_attempts * 100) if total_attempts > 0 else 0
            avg_speed_mb = data['avg_speed'] / (1024 * 1024) if data['avg_speed'] > 0 else 0
            
            stats_text += f"🌐 {domain}\\n"
            stats_text += f"   Grade: {grade:.1f}/100\\n"
            stats_text += f"   Success Rate: {success_rate:.1f}% ({data['successes']}/{total_attempts})\\n"
            stats_text += f"   Avg Speed: {avg_speed_mb:.1f} MB/s\\n"
            stats_text += f"   Total Downloaded: {data['total_bytes']/(1024*1024):.1f} MB\\n\\n"
        
        stats_text += "\\nMirrors are automatically prioritized by grade for future downloads."
        
        QMessageBox.information(self, "Mirror Statistics", stats_text)'''

new_method = '''    def show_mirror_stats(self):
        """Show mirror performance statistics"""
        stats = self.downloader.mirror_stats
        if not stats:
            QMessageBox.information(self, "Mirror Statistics", "No mirror statistics available yet.\\nStatistics will be collected as packages are downloaded.")
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
        
        stats_text = "Mirror Performance Statistics\\n\\n"
        
        # Sort mirrors by grade
        sorted_mirrors = sorted(stats.items(), key=lambda x: self.downloader.get_mirror_grade(x[0]), reverse=True)
        
        for domain, data in sorted_mirrors:
            grade = self.downloader.get_mirror_grade(domain)
            total_attempts = data['successes'] + data['failures']
            success_rate = (data['successes'] / total_attempts * 100) if total_attempts > 0 else 0
            avg_speed_mb = data['avg_speed'] / (1024 * 1024) if data['avg_speed'] > 0 else 0
            
            stats_text += f"🌐 {domain}\\n"
            stats_text += f"   Grade: {grade:.1f}/100\\n"
            stats_text += f"   Success Rate: {success_rate:.1f}% ({data['successes']}/{total_attempts})\\n"
            stats_text += f"   Avg Speed: {avg_speed_mb:.1f} MB/s\\n"
            stats_text += f"   Total Downloaded: {data['total_bytes']/(1024*1024):.1f} MB\\n\\n"
        
        stats_text += "\\nMirrors are automatically prioritized by grade for future downloads."
        
        text_widget.setPlainText(stats_text)
        layout.addWidget(text_widget)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()'''

# Replace the method
new_content = content.replace(old_method, new_method)

# Write back to file
with open('/home/scottp/IdeaProjects/LFS/src/gui/main_window.py', 'w') as f:
    f.write(new_content)

print("✅ Fixed mirror stats dialog - now scrollable and fits window")