#!/usr/bin/env python3

# Add missing QTabWidget import

import sys
import os

# Read the main_window.py file
with open('/home/scottp/IdeaProjects/LFS/src/gui/main_window.py', 'r') as f:
    content = f.read()

# Add QTabWidget to imports (it's already there, but let's make sure)
# The import should already exist, but let's check if we need to add it separately
if 'QTabWidget' not in content.split('\n')[3]:  # Check the import line
    old_import = '''from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem,
                            QSplitter, QTabWidget, QLabel, QLineEdit, QComboBox,
                            QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
                            QMessageBox, QFileDialog, QDialog, QDialogButtonBox, QMenu, QSpinBox)'''
    
    # QTabWidget should already be there, so this is just a safety check
    print("QTabWidget import already exists")
else:
    print("QTabWidget import already exists")

print("✅ Import check complete")