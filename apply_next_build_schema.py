#!/usr/bin/env python3
"""Apply next build reports database schema"""

import mysql.connector
import os

def apply_schema():
    try:
        # Connect to database
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='G`/C#Pi"5uqHNrZ@r<pT',
            database='lfs_builds'
        )
        
        cursor = connection.cursor()
        
        # Read schema file
        schema_path = 'src/database/next_build_reports_schema.sql'
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Split and execute statements
        statements = schema_sql.split(';')
        
        for statement in statements:
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                    print(f"✅ Executed: {statement[:50]}...")
                except mysql.connector.Error as e:
                    if "already exists" in str(e):
                        print(f"⚠️ Already exists: {statement[:50]}...")
                    else:
                        print(f"❌ Error: {e}")
                        print(f"Statement: {statement}")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("\n✅ Next build reports schema applied successfully!")
        
        # Test the tables
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='G`/C#Pi"5uqHNrZ@r<pT',
            database='lfs_builds'
        )
        
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES LIKE 'next_build_reports'")
        if cursor.fetchone():
            print("✅ next_build_reports table created successfully")
        
        cursor.execute("SHOW TABLES LIKE 'report_access_log'")
        if cursor.fetchone():
            print("✅ report_access_log table created successfully")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"❌ Failed to apply schema: {e}")

if __name__ == "__main__":
    apply_schema()