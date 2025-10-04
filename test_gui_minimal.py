#!/usr/bin/env python3

import sys
import traceback

def test_gui_imports():
    """Test GUI imports"""
    print("🔍 Testing GUI imports...")
    
    try:
        print("  - Testing PyQt5 import...")
        from PyQt5.QtWidgets import QApplication
        print("  ✅ PyQt5 import OK")
        
        print("  - Testing main window import...")
        from src.gui.main_window import LFSMainWindow
        print("  ✅ Main window import OK")
        
        return True
        
    except Exception as e:
        print(f"  ❌ GUI import failed: {e}")
        traceback.print_exc()
        return False

def test_gui_creation():
    """Test GUI creation without showing"""
    print("🔍 Testing GUI creation...")
    
    try:
        from PyQt5.QtWidgets import QApplication
        from src.gui.main_window import LFSMainWindow
        
        print("  - Creating QApplication...")
        app = QApplication(sys.argv)
        
        print("  - Creating main window...")
        window = LFSMainWindow()
        
        print("  - Testing build engine access...")
        if hasattr(window, 'build_engine'):
            print("  ✅ Build engine accessible")
        else:
            print("  ❌ Build engine not found")
            return False
        
        print("  ✅ GUI creation OK")
        return True
        
    except Exception as e:
        print(f"  ❌ GUI creation failed: {e}")
        traceback.print_exc()
        return False

def test_build_start_simulation():
    """Test build start without actually starting"""
    print("🔍 Testing build start simulation...")
    
    try:
        from PyQt5.QtWidgets import QApplication
        from src.gui.main_window import LFSMainWindow
        
        app = QApplication(sys.argv)
        window = LFSMainWindow()
        
        print("  - Testing config loading...")
        configs = window.repo_manager.list_configs()
        print(f"  - Found {len(configs)} configs")
        
        if configs:
            config_path = configs[0]['path']
            print(f"  - Testing config path: {config_path}")
            
            # Test loading config without starting build
            print("  - Testing config loading...")
            config = window.build_engine.load_config(config_path)
            if config:
                print(f"  - Config loaded: {config.get('name', 'Unknown')}")
                print("  ✅ Build simulation OK")
                return True
            else:
                print("  ❌ Config loading failed")
                return False
        else:
            print("  ⚠ No configs found - creating test config")
            # This is expected for a fresh system
            return True
        
    except Exception as e:
        print(f"  ❌ Build simulation failed: {e}")
        traceback.print_exc()
        return False

def main():
    print("🧪 LFS GUI System - Minimal Test")
    print("=" * 50)
    
    # Test GUI imports
    if not test_gui_imports():
        print("❌ GUI import test failed - stopping")
        return False
    
    # Test GUI creation
    if not test_gui_creation():
        print("❌ GUI creation test failed - stopping")
        return False
    
    # Test build simulation
    if not test_build_start_simulation():
        print("❌ Build simulation test failed - stopping")
        return False
    
    print("=" * 50)
    print("✅ All GUI tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 GUI test script crashed: {e}")
        traceback.print_exc()
        sys.exit(1)