#!/usr/bin/env python3
"""
Cleanup script for stuck/running builds in the LFS build system
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.db_manager import DatabaseManager

def cleanup_running_builds():
    """Mark all running builds as cancelled"""
    db = DatabaseManager()
    
    try:
        conn = db.connect()
        cursor = conn.cursor()
        
        # Find all running builds
        cursor.execute("SELECT build_id FROM builds WHERE status = 'running'")
        running_builds = cursor.fetchall()
        
        if not running_builds:
            print("No running builds found.")
            return
        
        print(f"Found {len(running_builds)} running builds:")
        for build in running_builds:
            print(f"  - {build[0]}")
        
        # Mark them as cancelled
        cursor.execute("UPDATE builds SET status = 'cancelled', end_time = NOW() WHERE status = 'running'")
        
        # Add cleanup documents
        for build in running_builds:
            build_id = build[0]
            cursor.execute("""
                INSERT INTO build_documents (build_id, document_type, title, content, metadata)
                VALUES (%s, 'log', 'Build Cleanup', 'Build was marked as cancelled during cleanup', '{"cleanup": true}')
            """, (build_id,))
        
        conn.commit()
        cursor.close()
        
        print(f"Successfully cleaned up {len(running_builds)} builds.")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    cleanup_running_builds()