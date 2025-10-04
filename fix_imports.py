#!/usr/bin/env python3

# Add missing QSpinBox import

import sys
import os

# Read the main_window.py file
with open('/home/scottp/IdeaProjects/LFS/src/gui/main_window.py', 'r') as f:
    content = f.read()

# Add QSpinBox to imports
old_import = '''from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem,
                            QSplitter, QTabWidget, QLabel, QLineEdit, QComboBox,
                            QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
                            QMessageBox, QFileDialog, QDialog, QDialogButtonBox, QMenu)'''

new_import = '''from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem,
                            QSplitter, QTabWidget, QLabel, QLineEdit, QComboBox,
                            QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
                            QMessageBox, QFileDialog, QDialog, QDialogButtonBox, QMenu, QSpinBox)'''

content = content.replace(old_import, new_import)

# Write back to file
with open('/home/scottp/IdeaProjects/LFS/src/gui/main_window.py', 'w') as f:
    f.write(content)

print("✅ Added QSpinBox import")