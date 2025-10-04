#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing GUI startup...")
    from src.gui.main_window import LFSMainWindow
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    print("QApplication created successfully")
    
    window = LFSMainWindow()
    print("Main window created successfully")
    
    print("Document stats label text:", window.doc_status_label.text())
    print("Documents tab exists:", "Documents" in [window.centralWidget().findChild(QTabWidget).tabText(i) for i in range(window.centralWidget().findChild(QTabWidget).count())])
    
    window.show()
    print("Window shown successfully")
    
    # Don't start event loop, just test creation
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()