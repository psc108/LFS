#!/usr/bin/env python3
"""Simple GUI button test for LFS Build System"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from PyQt5.QtWidgets import QApplication

def test_gui_buttons():
    app = QApplication(sys.argv)
    
    try:
        from gui.enhanced_main_window import EnhancedMainWindow
        window = EnhancedMainWindow()
        
        tests = [
            ('Build Wizard', window.open_build_wizard),
            ('Fault Analysis', window.open_fault_analysis),
            ('Parallel Build', window.open_parallel_build),
            ('Security Scan', window.open_security_scan),
            ('ISO Generator', window.open_iso_generator),
            ('Performance Dashboard', window.open_performance_dashboard),
            ('System Health', window.open_system_health),
            ('User Management', window.open_user_management),
            ('API Server Toggle', window.toggle_api_server)
        ]
        
        results = {}
        
        for test_name, test_method in tests:
            try:
                test_method()
                results[test_name] = True
                print(f"✅ {test_name} - Works")
            except Exception as e:
                results[test_name] = False
                print(f"❌ {test_name} - Error: {str(e)[:100]}")
        
        passed = sum(results.values())
        total = len(results)
        
        print(f"\nResults: {passed}/{total} passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All GUI features working!")
            return 0
        else:
            print("⚠️ Some features need attention")
            return 1
            
    except Exception as e:
        print(f"Critical error: {e}")
        return 1
    finally:
        app.quit()

if __name__ == "__main__":
    sys.exit(test_gui_buttons())