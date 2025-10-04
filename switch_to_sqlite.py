#!/usr/bin/env python3

# Read the current main_window.py
with open('src/gui/main_window.py', 'r') as f:
    content = f.read()

# Replace MySQL import with SQLite
content = content.replace(
    'from ..database.db_manager import DatabaseManager',
    'from ..database.sqlite_manager import SQLiteManager as DatabaseManager'
)

# Write the updated content
with open('src/gui/main_window.py', 'w') as f:
    f.write(content)

# Also update build_engine.py if it imports DatabaseManager directly
try:
    with open('src/build/build_engine.py', 'r') as f:
        build_content = f.read()
    
    if 'from ..database.db_manager import DatabaseManager' in build_content:
        build_content = build_content.replace(
            'from ..database.db_manager import DatabaseManager',
            'from ..database.sqlite_manager import SQLiteManager as DatabaseManager'
        )
        
        with open('src/build/build_engine.py', 'w') as f:
            f.write(build_content)
        
        print("✅ Updated build_engine.py to use SQLite")
    
except:
    pass

print("✅ Switched from MySQL to SQLite - should eliminate connection issues")