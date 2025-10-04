#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing GUI startup...")
    from src.gui.main_window import LFSMainWindow
    from PyQt5.QtWidgets import QApplication, QTabWidget
    
    app = QApplication(sys.argv)
    print("QApplication created successfully")
    
    window = LFSMainWindow()
    print("Main window created successfully")
    
    print("Document stats label text:", window.doc_status_label.text())
    
    # Find the tab widget
    tab_widget = window.centralWidget().findChild(QTabWidget)
    if tab_widget:
        tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
        print("Available tabs:", tab_names)
        print("Documents tab exists:", "Documents" in tab_names)
    
    print("Document search box exists:", hasattr(window, 'doc_search_edit'))
    print("Document stats button exists:", hasattr(window, 'doc_stats_btn'))
    print("Document table exists:", hasattr(window, 'documents_table'))
    
    window.show()
    print("Window shown successfully - GUI should be visible now")
    
    # Start the event loop for 3 seconds to see the GUI
    from PyQt5.QtCore import QTimer
    QTimer.singleShot(3000, app.quit)
    app.exec_()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()