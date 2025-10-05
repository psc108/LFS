#!/usr/bin/env python3
"""
Comprehensive GUI button test script for LFS Build System Enterprise Edition.
Tests all buttons and menu items to ensure they work as claimed.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from PyQt5.QtTest import QTest

def test_gui_buttons():
    """Test all GUI buttons and menu items"""
    
    print("🧪 Starting GUI Button Tests...")
    
    # Create QApplication
    app = QApplication(sys.argv)
    
    try:
        # Import and create main window
        from gui.enhanced_main_window import EnhancedMainWindow
        window = EnhancedMainWindow()
        window.show()
        
        # Test results
        test_results = {}
        
        # Test Build Menu Actions
        print("\n🔨 Testing Build Menu Actions...")
        
        try:
            window.open_build_wizard()
            test_results['Build Wizard'] = True
            print("  ✅ Build Wizard - Opens successfully")
        except Exception as e:
            test_results['Build Wizard'] = False
            print(f"  ❌ Build Wizard - Error: {e}")
        
        try:
            window.open_parallel_build()
            test_results['Parallel Build'] = True
            print("  ✅ Parallel Build - Opens successfully")
        except Exception as e:
            test_results['Parallel Build'] = False
            print(f"  ❌ Parallel Build - Error: {e}")
        
        try:
            window.open_iso_generator()
            test_results['ISO Generator'] = True
            print("  ✅ ISO Generator - Opens successfully")
        except Exception as e:
            test_results['ISO Generator'] = False
            print(f"  ❌ ISO Generator - Error: {e}")
        
        # Test Analysis Menu Actions
        print("\n🔍 Testing Analysis Menu Actions...")
        
        try:
            window.open_fault_analysis()
            test_results['Fault Analysis'] = True
            print("  ✅ Fault Analysis - Opens successfully")
        except Exception as e:
            test_results['Fault Analysis'] = False
            print(f"  ❌ Fault Analysis - Error: {e}")
        
        try:
            window.open_performance_dashboard()
            test_results['Performance Dashboard'] = True
            print("  ✅ Performance Dashboard - Opens successfully")
        except Exception as e:
            test_results['Performance Dashboard'] = False
            print(f"  ❌ Performance Dashboard - Error: {e}")
        
        try:
            window.open_security_scan()
            test_results['Security Scanner'] = True
            print("  ✅ Security Scanner - Opens successfully")
        except Exception as e:
            test_results['Security Scanner'] = False
            print(f"  ❌ Security Scanner - Error: {e}")
        
        try:
            window.open_system_health()
            test_results['System Health'] = True
            print("  ✅ System Health - Opens successfully")
        except Exception as e:
            test_results['System Health'] = False
            print(f"  ❌ System Health - Error: {e}")
        
        # Test Collaboration Menu Actions
        print("\n👥 Testing Collaboration Menu Actions...")
        
        try:
            window.open_user_management()
            test_results['User Management'] = True
            print("  ✅ User Management - Opens successfully")
        except Exception as e:
            test_results['User Management'] = False
            print(f"  ❌ User Management - Error: {e}")
        
        # Test Integration Menu Actions
        print("\n🔗 Testing Integration Menu Actions...")
        
        try:
            window.toggle_api_server()
            test_results['API Server Toggle'] = True
            print("  ✅ API Server Toggle - Works successfully")
        except Exception as e:
            test_results['API Server Toggle'] = False
            print(f"  ❌ API Server Toggle - Error: {e}")
        
        # Test Feature Panel Buttons
        print("\n🎛️ Testing Feature Panel Buttons...")
        
        # Build Features
        build_features = [
            ('Build Wizard', window.open_build_wizard),
            ('Templates', window.open_templates),
            ('Parallel Builds', window.open_parallel_build),
            ('Container Builds', window.open_container_build),
            ('Cloud Builds', window.open_cloud_build)
        ]
        
        for feature_name, feature_method in build_features:
            try:
                if hasattr(feature_method, '__call__'):
                    feature_method()
                    test_results[f'Panel - {feature_name}'] = True
                    print(f"  ✅ {feature_name} - Panel button works")
                else:
                    test_results[f'Panel - {feature_name}'] = False
                    print(f"  ⚠️  {feature_name} - Method not callable")
            except Exception as e:
                test_results[f'Panel - {feature_name}'] = False
                print(f"  ❌ {feature_name} - Panel button error: {e}")
        
        # Analysis Features
        analysis_features = [
            ('Fault Analysis', window.open_fault_analysis),
            ('Performance Dashboard', window.open_performance_dashboard),
            ('Security Scanner', window.open_security_scan),
            ('System Health', window.open_system_health),
            ('Metrics Dashboard', window.open_metrics_dashboard)
        ]
        
        for feature_name, feature_method in analysis_features:
            try:
                if hasattr(feature_method, '__call__'):
                    feature_method()
                    test_results[f'Analysis - {feature_name}'] = True
                    print(f"  ✅ {feature_name} - Analysis button works")
                else:
                    test_results[f'Analysis - {feature_name}'] = False
                    print(f"  ⚠️  {feature_name} - Method not callable")
            except Exception as e:
                test_results[f'Analysis - {feature_name}'] = False
                print(f"  ❌ {feature_name} - Analysis button error: {e}")
        
        # Deployment Features
        deployment_features = [
            ('ISO Generator', window.open_iso_generator),
            ('VM Images', window.open_vm_generator),
            ('Network Boot', window.open_network_boot),
            ('Cloud Deploy', window.open_cloud_deploy)
        ]
        
        for feature_name, feature_method in deployment_features:
            try:
                if hasattr(feature_method, '__call__'):
                    feature_method()
                    test_results[f'Deployment - {feature_name}'] = True
                    print(f"  ✅ {feature_name} - Deployment button works")
                else:
                    test_results[f'Deployment - {feature_name}'] = False
                    print(f"  ⚠️  {feature_name} - Method not callable")
            except Exception as e:
                test_results[f'Deployment - {feature_name}'] = False
                print(f"  ❌ {feature_name} - Deployment button error: {e}")
        
        # Collaboration Features
        collaboration_features = [
            ('Users', window.open_user_management),
            ('Team Dashboard', window.open_team_dashboard),
            ('Reviews', window.open_build_reviews),
            ('Notifications', window.open_notifications)
        ]
        
        for feature_name, feature_method in collaboration_features:
            try:
                if hasattr(feature_method, '__call__'):
                    feature_method()
                    test_results[f'Collaboration - {feature_name}'] = True
                    print(f"  ✅ {feature_name} - Collaboration button works")
                else:
                    test_results[f'Collaboration - {feature_name}'] = False
                    print(f"  ⚠️  {feature_name} - Method not callable")
            except Exception as e:
                test_results[f'Collaboration - {feature_name}'] = False
                print(f"  ❌ {feature_name} - Collaboration button error: {e}")
        
        # Test Toolbar Actions
        print("\n🛠️ Testing Toolbar Actions...")
        
        toolbar_actions = [
            ('Build Wizard Toolbar', window.open_build_wizard),
            ('Parallel Build Toolbar', window.open_parallel_build),
            ('Fault Analysis Toolbar', window.open_fault_analysis),
            ('Security Scan Toolbar', window.open_security_scan),
            ('ISO Generator Toolbar', window.open_iso_generator),
            ('API Server Toolbar', window.toggle_api_server)
        ]
        
        for action_name, action_method in toolbar_actions:
            try:
                action_method()
                test_results[f'Toolbar - {action_name}'] = True
                print(f"  ✅ {action_name} - Toolbar action works")
            except Exception as e:
                test_results[f'Toolbar - {action_name}'] = False
                print(f"  ❌ {action_name} - Toolbar action error: {e}")
        
        # Test Quick Actions Panel
        print("\n⚡ Testing Quick Actions Panel...")
        
        quick_actions = [
            ('Start Wizard', window.open_build_wizard),
            ('Security Scan', window.open_security_scan),
            ('Generate ISO', window.open_iso_generator)
        ]
        
        for action_name, action_method in quick_actions:
            try:
                action_method()
                test_results[f'Quick - {action_name}'] = True
                print(f"  ✅ {action_name} - Quick action works")
            except Exception as e:
                test_results[f'Quick - {action_name}'] = False
                print(f"  ❌ {action_name} - Quick action error: {e}")
        
        # Test Additional Methods
        print("\n🔧 Testing Additional Methods...")
        
        additional_methods = [
            ('Add User Dialog', window.add_user_dialog),
            ('Collaboration Settings', window.open_collaboration_settings),
            ('Health Alerts Config', window.configure_health_alerts)
        ]
        
        for method_name, method in additional_methods:
            try:
                method()
                test_results[f'Additional - {method_name}'] = True
                print(f"  ✅ {method_name} - Method works")
            except Exception as e:
                test_results[f'Additional - {method_name}'] = False
                print(f"  ❌ {method_name} - Method error: {e}")
        
        # Summary
        print(f"\n{'='*60}")
        print("📋 GUI BUTTON TEST SUMMARY")
        print(f"{'='*60}")
        
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        # Group results by category
        categories = {}\n        for test_name, result in test_results.items():\n            if ' - ' in test_name:\n                category = test_name.split(' - ')[0]\n            else:\n                category = 'Main'\n            \n            if category not in categories:\n                categories[category] = {'passed': 0, 'total': 0}\n            \n            categories[category]['total'] += 1\n            if result:\n                categories[category]['passed'] += 1\n        \n        # Display by category\n        for category, stats in categories.items():\n            pass_rate = (stats['passed'] / stats['total']) * 100\n            status = \"✅\" if pass_rate == 100 else \"⚠️\" if pass_rate >= 80 else \"❌\"\n            print(f\"{category:20} {status} {stats['passed']:2}/{stats['total']:2} ({pass_rate:5.1f}%)\")\n        \n        print(f\"\\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)\")\n        \n        # Detailed failures\n        failures = [name for name, result in test_results.items() if not result]\n        if failures:\n            print(f\"\\n❌ Failed Tests ({len(failures)}):\")\n            for failure in failures:\n                print(f\"   • {failure}\")\n        \n        if passed == total:\n            print(\"\\n🎉 All GUI buttons and features are working correctly!\")\n            return 0\n        else:\n            print(f\"\\n⚠️  {total - passed} features need attention.\")\n            return 1\n            \n    except Exception as e:\n        print(f\"❌ Critical error during GUI testing: {e}\")\n        import traceback\n        traceback.print_exc()\n        return 1\n    \n    finally:\n        # Clean up\n        if 'app' in locals():\n            app.quit()\n\ndef main():\n    \"\"\"Main test function\"\"\"\n    return test_gui_buttons()\n\nif __name__ == \"__main__\":\n    sys.exit(main())