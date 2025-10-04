#!/usr/bin/env python3

import sys
import traceback

def test_imports():
    """Test all imports to find the problematic one"""
    print("🔍 Testing imports...")
    
    try:
        print("  - Testing database import...")
        from src.database.db_manager import DatabaseManager
        print("  ✅ Database import OK")
        
        print("  - Testing repository import...")
        from src.repository.repo_manager import RepositoryManager
        print("  ✅ Repository import OK")
        
        print("  - Testing build engine import...")
        from src.build.build_engine import BuildEngine
        print("  ✅ Build engine import OK")
        
        print("  - Testing settings import...")
        from src.config.settings_manager import SettingsManager
        print("  ✅ Settings import OK")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        traceback.print_exc()
        return False

def test_database():
    """Test database connection"""
    print("🔍 Testing database connection...")
    
    try:
        from src.database.db_manager import DatabaseManager
        db = DatabaseManager()
        
        print("  - Testing connection...")
        conn = db.connect()
        if conn:
            print("  ✅ Database connection OK")
            conn.close()
            return True
        else:
            print("  ❌ Database connection failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        traceback.print_exc()
        return False

def test_build_creation():
    """Test minimal build creation"""
    print("🔍 Testing build creation...")
    
    try:
        from src.database.db_manager import DatabaseManager
        from src.repository.repo_manager import RepositoryManager
        from src.build.build_engine import BuildEngine
        
        print("  - Creating components...")
        db = DatabaseManager()
        repo = RepositoryManager(db)
        engine = BuildEngine(db, repo)
        
        print("  - Testing build ID generation...")
        from datetime import datetime
        import os
        build_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.urandom(4).hex()}"
        print(f"  - Generated ID: {build_id}")
        
        print("  - Testing build record creation...")
        success = db.create_build(build_id, "test_build", 1)
        if success:
            print("  ✅ Build creation OK")
            return True
        else:
            print("  ❌ Build creation failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Build creation test failed: {e}")
        traceback.print_exc()
        return False

def main():
    print("🧪 LFS Build System - Minimal Test")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("❌ Import test failed - stopping")
        return False
    
    # Test database
    if not test_database():
        print("❌ Database test failed - stopping")
        return False
    
    # Test build creation
    if not test_build_creation():
        print("❌ Build creation test failed - stopping")
        return False
    
    print("=" * 50)
    print("✅ All tests passed! System appears to be working.")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Test script crashed: {e}")
        traceback.print_exc()
        sys.exit(1)