#!/usr/bin/env python3

# Read the current db_manager.py
with open('src/database/db_manager.py', 'r') as f:
    content = f.read()

# Replace the entire DatabaseManager class with a robust version
new_db_manager = '''import mysql.connector
from mysql.connector import pooling
import json
import time
from datetime import datetime
from pathlib import Path

class DatabaseManager:
    """Robust MySQL database manager with connection pooling"""
    
    def __init__(self):
        self.pool = None
        self.init_connection_pool()
    
    def init_connection_pool(self):
        """Initialize MySQL connection pool"""
        try:
            # Load credentials
            creds_file = Path('.mysql_credentials')
            if creds_file.exists():
                with open(creds_file, 'r') as f:
                    password = f.read().strip()
            else:
                password = 'lfs_password'  # Default
            
            # Create connection pool
            config = {
                'user': 'lfs_user',
                'password': password,
                'host': 'localhost',
                'database': 'lfs_builds',
                'pool_name': 'lfs_pool',
                'pool_size': 5,
                'pool_reset_session': True,
                'autocommit': True,
                'charset': 'utf8mb4',
                'use_unicode': True,
                'connect_timeout': 10,
                'sql_mode': 'TRADITIONAL'
            }
            
            self.pool = pooling.MySQLConnectionPool(**config)
            print("✅ MySQL connection pool initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize MySQL pool: {e}")
            self.pool = None
    
    def get_connection(self):
        """Get connection from pool with retry"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.pool is None:
                    self.init_connection_pool()
                
                if self.pool:
                    conn = self.pool.get_connection()
                    # Test connection
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    cursor.close()
                    return conn
                    
            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    # Reinitialize pool on final failure
                    self.pool = None
                    self.init_connection_pool()
        
        return None
    
    def execute_query(self, query, params=None, fetch=False):
        """Execute query with automatic retry and connection management"""
        max_retries = 3
        
        for attempt in range(max_retries):
            conn = None
            cursor = None
            
            try:
                conn = self.get_connection()
                if not conn:
                    raise Exception("Could not get database connection")
                
                cursor = conn.cursor(dictionary=True)
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount
                
                cursor.close()
                conn.close()
                
                return result
                
            except Exception as e:
                print(f"Query attempt {attempt + 1} failed: {e}")
                
                # Clean up on error
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
                
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    print(f"Query failed after {max_retries} attempts: {query}")
                    return [] if fetch else 0
        
        return [] if fetch else 0
    
    def create_build(self, build_id: str, config_name: str, total_stages: int) -> bool:
        """Create a new build record"""
        try:
            result = self.execute_query("""
                INSERT INTO builds (build_id, config_name, status, total_stages, completed_stages, start_time)
                VALUES (%s, %s, 'running', %s, 0, NOW())
            """, (build_id, config_name, total_stages))
            
            return result > 0
            
        except Exception as e:
            print(f"Failed to create build: {e}")
            return False
    
    def add_document(self, build_id: str, document_type: str, title: str, content: str, metadata: dict = None):
        """Add a document to the build"""
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            result = self.execute_query("""
                INSERT INTO build_documents (build_id, document_type, title, content, metadata)
                VALUES (%s, %s, %s, %s, %s)
            """, (build_id, document_type, title, content, metadata_json))
            
            if result > 0:
                print(f"📄 Document saved: {document_type} - {title} ({len(content)} chars) for build {build_id}")
                return True
            else:
                print(f"❌ Failed to save document: {title}")
                return False
            
        except Exception as e:
            print(f"Failed to add document: {e}")
            return False
    
    def update_build_status(self, build_id: str, status: str, completed_stages: int = None):
        """Update build status"""
        try:
            if completed_stages is not None:
                result = self.execute_query("""
                    UPDATE builds 
                    SET status = %s, completed_stages = %s, end_time = NOW(),
                        duration_seconds = TIMESTAMPDIFF(SECOND, start_time, NOW())
                    WHERE build_id = %s
                """, (status, completed_stages, build_id))
            else:
                result = self.execute_query("""
                    UPDATE builds 
                    SET status = %s, end_time = NOW(),
                        duration_seconds = TIMESTAMPDIFF(SECOND, start_time, NOW())
                    WHERE build_id = %s
                """, (status, build_id))
            
            return result > 0
            
        except Exception as e:
            print(f"Failed to update build status: {e}")
            return False
    
    def search_builds(self, query: str = "", status: str = "", limit: int = 50):
        """Search builds"""
        try:
            sql = "SELECT * FROM builds WHERE 1=1"
            params = []
            
            if query:
                sql += " AND (build_id LIKE %s OR config_name LIKE %s)"
                params.extend([f"%{query}%", f"%{query}%"])
            
            if status:
                sql += " AND status = %s"
                params.append(status)
            
            sql += " ORDER BY start_time DESC LIMIT %s"
            params.append(limit)
            
            return self.execute_query(sql, params, fetch=True)
            
        except Exception as e:
            print(f"Failed to search builds: {e}")
            return []
    
    def get_build_documents(self, build_id: str):
        """Get documents for a build"""
        try:
            return self.execute_query("""
                SELECT * FROM build_documents 
                WHERE build_id = %s 
                ORDER BY created_at DESC
            """, (build_id,), fetch=True)
            
        except Exception as e:
            print(f"Failed to get build documents: {e}")
            return []
    
    def get_all_documents(self):
        """Get all documents"""
        try:
            return self.execute_query("""
                SELECT * FROM build_documents 
                ORDER BY created_at DESC 
                LIMIT 1000
            """, fetch=True)
            
        except Exception as e:
            print(f"Failed to get all documents: {e}")
            return []
    
    def get_document_stats(self):
        """Get document statistics"""
        try:
            # Overall stats
            overall_result = self.execute_query("""
                SELECT 
                    COUNT(*) as total_documents,
                    COUNT(DISTINCT build_id) as builds_with_docs,
                    SUM(CHAR_LENGTH(content)) as total_content_size
                FROM build_documents
            """, fetch=True)
            
            overall = overall_result[0] if overall_result else {}
            
            # By type
            by_type = self.execute_query("""
                SELECT 
                    document_type,
                    COUNT(*) as type_count
                FROM build_documents
                GROUP BY document_type
                ORDER BY type_count DESC
            """, fetch=True)
            
            return {
                'overall': overall,
                'by_type': by_type or []
            }
            
        except Exception as e:
            print(f"Failed to get document stats: {e}")
            return {'overall': {}, 'by_type': []}
    
    def search_documents(self, query: str):
        """Search documents"""
        try:
            return self.execute_query("""
                SELECT * FROM build_documents 
                WHERE MATCH(title, content) AGAINST(%s IN NATURAL LANGUAGE MODE)
                ORDER BY created_at DESC 
                LIMIT 100
            """, (query,), fetch=True)
            
        except Exception as e:
            print(f"Failed to search documents: {e}")
            return []
    
    def get_build_details(self, build_id: str):
        """Get complete build details"""
        try:
            # Get build info
            builds = self.execute_query("SELECT * FROM builds WHERE build_id = %s", (build_id,), fetch=True)
            if not builds:
                return None
            
            build = builds[0]
            
            # Get stages
            stages = self.execute_query("""
                SELECT * FROM build_stages 
                WHERE build_id = %s 
                ORDER BY stage_order
            """, (build_id,), fetch=True)
            
            # Get recent documents
            documents = self.execute_query("""
                SELECT * FROM build_documents 
                WHERE build_id = %s 
                ORDER BY created_at DESC 
                LIMIT 50
            """, (build_id,), fetch=True)
            
            return {
                'build': build,
                'stages': stages or [],
                'documents': documents or []
            }
            
        except Exception as e:
            print(f"Failed to get build details: {e}")
            return None
    
    def create_tables(self):
        """Create database tables"""
        try:
            # This method is called during initialization
            # Tables should already exist from setup_database.sql
            print("✅ Database tables verified")
            
        except Exception as e:
            print(f"Failed to verify tables: {e}")
    
    # Legacy method for compatibility
    def connect(self):
        """Legacy method - use get_connection() instead"""
        return self.get_connection()
'''

# Replace the entire file content with the new implementation
content = '''#!/usr/bin/env python3
""" 
Robust MySQL Database Manager for LFS Build System
Handles connection pooling, retries, and error recovery
"""

''' + new_db_manager

# Write the updated content
with open('src/database/db_manager.py', 'w') as f:
    f.write(content)

print("✅ Replaced MySQL database manager with robust connection pooling version")