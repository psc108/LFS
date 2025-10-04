#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.gui.main_window import LFSMainWindow
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = LFSMainWindow()
    
    print("Document table row count:", window.documents_table.rowCount())
    print("Document table column count:", window.documents_table.columnCount())
    
    if window.documents_table.rowCount() > 0:
        print("First document:")
        for col in range(window.documents_table.columnCount()):
            item = window.documents_table.item(0, col)
            if item:
                print(f"  Column {col}: {item.text()}")
    
    print("Document viewer content preview:")
    print(window.document_viewer.toPlainText()[:200] + "...")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()