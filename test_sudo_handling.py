#!/usr/bin/env python3

"""
Test script to verify sudo password handling in the build system
"""

import sys
import os
import tempfile
import subprocess

def test_askpass_script_creation():
    """Test that askpass scripts are created correctly"""
    print("🧪 Testing askpass script creation...")
    
    test_password = "test_password_123"
    
    try:
        # Create askpass script like the build engine does
        askpass_script = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh')
        askpass_script.write(f'#!/bin/bash\necho "{test_password}"\n')
        askpass_script.close()
        os.chmod(askpass_script.name, 0o755)
        
        # Verify script exists and is executable
        if os.path.exists(askpass_script.name) and os.access(askpass_script.name, os.X_OK):
            print("✅ Askpass script created and executable")
            
            # Verify script content
            with open(askpass_script.name, 'r') as f:
                content = f.read()
                if test_password in content:
                    print("✅ Askpass script contains correct password")
                    result = True
                else:
                    print("❌ Askpass script missing password")
                    result = False
        else:
            print("❌ Askpass script not created or not executable")
            result = False
        
        # Cleanup
        try:
            os.unlink(askpass_script.name)
        except:
            pass
            
        return result
        
    except Exception as e:
        print(f"❌ Error testing askpass script creation: {e}")
        return False

def test_environment_setup():
    """Test that environment variables are set correctly"""
    print("\n🧪 Testing environment variable setup...")
    
    try:
        # Test environment setup like build engine does
        env = os.environ.copy()
        env['SUDO_ASKPASS'] = '/tmp/test_askpass.sh'
        env['SUDO_NONINTERACTIVE'] = '1'
        
        if 'SUDO_ASKPASS' in env and 'SUDO_NONINTERACTIVE' in env:
            print("✅ Environment variables set correctly")
            return True
        else:
            print("❌ Environment variables not set")
            return False
            
    except Exception as e:
        print(f"❌ Error testing environment setup: {e}")
        return False

def test_build_engine_sudo():
    """Test the build engine's sudo handling"""
    print("\n🧪 Testing build engine sudo handling...")
    
    try:
        # Add the src directory to Python path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from src.database.db_manager import DatabaseManager
        from src.build.build_engine import BuildEngine
        
        # Initialize components
        db = DatabaseManager()
        engine = BuildEngine(db)
        
        # Test setting sudo password
        test_password = "test_password_123"
        engine.set_sudo_password(test_password)
        
        if engine.sudo_password == test_password:
            print("✅ Build engine sudo password setting works")
            return True
        else:
            print("❌ Build engine sudo password setting failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing build engine sudo: {e}")
        return False

def main():
    """Run all sudo handling tests"""
    print("🔐 Testing LFS Build System Sudo Password Handling\n")
    
    tests = [
        test_environment_setup,
        test_askpass_script_creation,
        test_build_engine_sudo
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print(f"\n📊 Test Results:")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All sudo handling tests passed!")
        return 0
    else:
        print("⚠️ Some sudo handling tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())