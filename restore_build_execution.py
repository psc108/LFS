#!/usr/bin/env python3

# Read the current build_engine.py
with open('src/build/build_engine.py', 'r') as f:
    content = f.read()

# Replace the minimal code with proper threaded execution
old_minimal = '''            print("🚀 Build start completed (minimal mode)")
            # Don't do any additional database operations to avoid crashes
            print("✅ Build created successfully - execution disabled for debugging")'''

new_threaded = '''            print("🚀 Starting build thread with robust database layer...")
            # Start build in background thread with robust error handling
            build_thread = threading.Thread(
                target=self._safe_execute_build, 
                args=(build_id, config),
                name=f"BuildThread-{build_id}"
            )
            build_thread.daemon = True
            build_thread.start()'''

content = content.replace(old_minimal, new_threaded)

# Write the updated content
with open('src/build/build_engine.py', 'w') as f:
    f.write(content)

print("✅ Restored build execution with robust database layer")