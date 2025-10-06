#!/usr/bin/env python3
"""
Update database schema for download tracking integration
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.db_manager import DatabaseManager

def main():
    """Apply download schema updates"""
    try:
        # Initialize database manager
        db = DatabaseManager()
        
        # Read and apply schema
        schema_path = os.path.join('src', 'database', 'download_schema.sql')
        if not os.path.exists(schema_path):
            print(f"Schema file not found: {schema_path}")
            return False
        
        with open(schema_path, 'r') as f:
            schema = f.read()
        
        # Split and execute statements
        statements = schema.split(';')
        for statement in statements:
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    db.execute_query(statement)
                    print(f"✅ Executed: {statement[:50]}...")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"⚠️  Already exists: {statement[:50]}...")
                    else:
                        print(f"❌ Error: {statement[:50]}... - {e}")
        
        print("\n🎉 Download schema update completed!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update schema: {e}")
        return False

if __name__ == "__main__":
    main()