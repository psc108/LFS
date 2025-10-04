#!/usr/bin/env python3

# Create a debug wrapper for main.py
debug_wrapper = '''#!/usr/bin/env python3

import sys
import traceback
import signal
import os

def signal_handler(signum, frame):
    print(f"\\n🚨 Signal {signum} received!")
    print("Stack trace:")
    traceback.print_stack(frame)
    sys.exit(1)

def exception_handler(exc_type, exc_value, exc_traceback):
    print(f"\\n💥 Uncaught exception: {exc_type.__name__}: {exc_value}")
    print("Full traceback:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    sys.exit(1)

# Install signal handlers
signal.signal(signal.SIGSEGV, signal_handler)
signal.signal(signal.SIGABRT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Install exception handler
sys.excepthook = exception_handler

print("🔍 Debug mode enabled - catching all errors and signals")

try:
    # Import and run the main application
    from src.gui.main_window import main
    print("✅ Imported main successfully")
    
    print("🚀 Starting application...")
    main()
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Application error: {e}")
    traceback.print_exc()
    sys.exit(1)
'''

with open('debug_main.py', 'w') as f:
    f.write(debug_wrapper)

print("✅ Created debug wrapper: debug_main.py")