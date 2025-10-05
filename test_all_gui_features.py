#!/usr/bin/env python3
"""Complete GUI feature test for all buttons and methods"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from PyQt5.QtWidgets import QApplication

def test_all_gui_features():
    app = QApplication(sys.argv)
    
    try:
        from gui.enhanced_main_window import EnhancedMainWindow
        window = EnhancedMainWindow()
        
        # All GUI methods to test
        all_tests = [
            # Core features
            ('Build Wizard', window.open_build_wizard),
            ('Fault Analysis', window.open_fault_analysis),
            ('Parallel Build', window.open_parallel_build),
            ('Security Scan', window.open_security_scan),
            ('ISO Generator', window.open_iso_generator),
            ('Performance Dashboard', window.open_performance_dashboard),
            ('System Health', window.open_system_health),
            ('User Management', window.open_user_management),
            ('API Server Toggle', window.toggle_api_server),
            
            # Additional features
            ('Templates', window.open_templates),
            ('Container Build', window.open_container_build),
            ('Cloud Build', window.open_cloud_build),
            ('Metrics Dashboard', window.open_metrics_dashboard),
            ('Team Dashboard', window.open_team_dashboard),
            ('Build Reviews', window.open_build_reviews),
            ('Notifications', window.open_notifications),
            ('Plugin Manager', window.open_plugin_manager),
            ('Build Scheduler', window.open_build_scheduler),
            ('CI/CD Setup', window.open_cicd_setup),
            ('Kernel Config', window.open_kernel_config),
            ('Package Manager', window.open_package_manager),
            ('Compliance Check', window.open_compliance_check),
            ('Network Boot', window.open_network_boot),
            ('VM Generator', window.open_vm_generator),
            ('Cloud Deploy', window.open_cloud_deploy),
            ('API Interface', window.open_api_interface),
            
            # Helper methods
            ('Add User Dialog', window.add_user_dialog),
            ('Collaboration Settings', window.open_collaboration_settings),
            ('Health Alerts Config', window.configure_health_alerts)
        ]
        
        results = {}
        
        print("🧪 Testing All GUI Features...")
        print("=" * 50)
        
        for test_name, test_method in all_tests:
            try:
                test_method()
                results[test_name] = True
                print(f"✅ {test_name}")
            except Exception as e:
                results[test_name] = False
                print(f"❌ {test_name} - Error: {str(e)[:80]}")
        
        # Summary
        passed = sum(results.values())
        total = len(results)
        
        print("=" * 50)
        print(f"RESULTS: {passed}/{total} features working ({passed/total*100:.1f}%)")
        
        # Category breakdown
        categories = {
            'Core Features': ['Build Wizard', 'Fault Analysis', 'Parallel Build', 'Security Scan', 'ISO Generator', 'Performance Dashboard', 'System Health', 'User Management', 'API Server Toggle'],
            'Build & Deploy': ['Templates', 'Container Build', 'Cloud Build', 'VM Generator', 'Cloud Deploy'],
            'Analytics & Monitoring': ['Metrics Dashboard', 'System Health', 'Performance Dashboard'],
            'Collaboration': ['Team Dashboard', 'Build Reviews', 'Notifications', 'User Management'],
            'Integration': ['Plugin Manager', 'Build Scheduler', 'CI/CD Setup', 'API Interface'],
            'Tools': ['Kernel Config', 'Package Manager', 'Compliance Check', 'Network Boot']
        }
        
        print("\nCategory Breakdown:")
        for category, features in categories.items():
            category_passed = sum(1 for f in features if results.get(f, False))
            category_total = len(features)
            if category_total > 0:
                print(f"  {category}: {category_passed}/{category_total} ({category_passed/category_total*100:.0f}%)")
        
        if passed == total:
            print("\n🎉 ALL GUI FEATURES ARE WORKING PERFECTLY!")
            return 0
        else:
            failed = [name for name, result in results.items() if not result]
            print(f"\n⚠️ Failed features: {', '.join(failed)}")
            return 1
            
    except Exception as e:
        print(f"Critical error: {e}")
        return 1
    finally:
        app.quit()

if __name__ == "__main__":
    sys.exit(test_all_gui_features())