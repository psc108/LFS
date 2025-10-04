import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

class SQLiteManager:
    """SQLite-based database manager as MySQL fallback"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path.home() / ".lfs_builds" / "lfs_builds.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.create_tables()
    
    def connect(self):
        """Create SQLite connection"""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def create_tables(self):
        """Create database tables"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Builds table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS builds (
                build_id TEXT PRIMARY KEY,
                config_name TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                total_stages INTEGER DEFAULT 0,
                completed_stages INTEGER DEFAULT 0,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP NULL,
                duration_seconds INTEGER DEFAULT 0
            )
        """)
        
        # Build stages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS build_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                build_id TEXT NOT NULL,
                stage_name TEXT NOT NULL,
                stage_order INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                start_time TIMESTAMP NULL,
                end_time TIMESTAMP NULL,
                output_log TEXT,
                error_log TEXT,
                FOREIGN KEY (build_id) REFERENCES builds (build_id)
            )
        """)
        
        # Build documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS build_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                build_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (build_id) REFERENCES builds (build_id)
            )
        """)
        
        # Repository snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repo_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                build_id TEXT NOT NULL,
                snapshot_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (build_id) REFERENCES builds (build_id)
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ SQLite database initialized")
    
    def create_build(self, build_id: str, config_name: str, total_stages: int) -> bool:
        """Create a new build record"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO builds (build_id, config_name, status, total_stages, completed_stages)
                VALUES (?, ?, 'running', ?, 0)
            """, (build_id, config_name, total_stages))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Failed to create build: {e}")
            return False
    
    def add_document(self, build_id: str, document_type: str, title: str, content: str, metadata: dict = None):
        """Add a document to the build"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute("""
                INSERT INTO build_documents (build_id, document_type, title, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (build_id, document_type, title, content, metadata_json))
            
            conn.commit()
            conn.close()
            
            print(f"📄 Document saved: {document_type} - {title} ({len(content)} chars) for build {build_id}")
            return True
            
        except Exception as e:
            print(f"Failed to add document: {e}")
            return False
    
    def update_build_status(self, build_id: str, status: str, completed_stages: int = None):
        """Update build status"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            if completed_stages is not None:
                cursor.execute("""
                    UPDATE builds 
                    SET status = ?, completed_stages = ?, end_time = CURRENT_TIMESTAMP
                    WHERE build_id = ?
                """, (status, completed_stages, build_id))
            else:
                cursor.execute("""
                    UPDATE builds 
                    SET status = ?, end_time = CURRENT_TIMESTAMP
                    WHERE build_id = ?
                """, (status, build_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Failed to update build status: {e}")
            return False
    
    def search_builds(self, query: str = "", status: str = "", limit: int = 50):
        """Search builds"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            sql = "SELECT * FROM builds WHERE 1=1"
            params = []
            
            if query:
                sql += " AND (build_id LIKE ? OR config_name LIKE ?)"
                params.extend([f"%{query}%", f"%{query}%"])
            
            if status:
                sql += " AND status = ?"
                params.append(status)
            
            sql += " ORDER BY start_time DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            builds = cursor.fetchall()
            
            # Convert to list of dicts
            result = []
            for build in builds:
                build_dict = dict(build)
                if build_dict['start_time']:
                    build_dict['start_time'] = datetime.fromisoformat(build_dict['start_time'])
                if build_dict['end_time']:
                    build_dict['end_time'] = datetime.fromisoformat(build_dict['end_time'])
                result.append(build_dict)
            
            conn.close()
            return result
            
        except Exception as e:
            print(f"Failed to search builds: {e}")
            return []
    
    def get_build_documents(self, build_id: str):
        """Get documents for a build"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM build_documents 
                WHERE build_id = ? 
                ORDER BY created_at DESC
            """, (build_id,))
            
            documents = cursor.fetchall()
            
            # Convert to list of dicts
            result = []
            for doc in documents:
                doc_dict = dict(doc)
                if doc_dict['created_at']:
                    doc_dict['created_at'] = datetime.fromisoformat(doc_dict['created_at'])
                if doc_dict['metadata']:
                    try:
                        doc_dict['metadata'] = json.loads(doc_dict['metadata'])
                    except:
                        doc_dict['metadata'] = {}
                result.append(doc_dict)
            
            conn.close()
            return result
            
        except Exception as e:
            print(f"Failed to get build documents: {e}")
            return []
    
    def get_all_documents(self):
        """Get all documents"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM build_documents 
                ORDER BY created_at DESC 
                LIMIT 1000
            """)
            
            documents = cursor.fetchall()
            
            # Convert to list of dicts
            result = []
            for doc in documents:
                doc_dict = dict(doc)
                if doc_dict['created_at']:
                    doc_dict['created_at'] = datetime.fromisoformat(doc_dict['created_at'])
                result.append(doc_dict)
            
            conn.close()
            return result
            
        except Exception as e:
            print(f"Failed to get all documents: {e}")
            return []
    
    def get_document_stats(self):
        """Get document statistics"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Overall stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_documents,
                    COUNT(DISTINCT build_id) as builds_with_docs,
                    SUM(LENGTH(content)) as total_content_size
                FROM build_documents
            """)
            overall = dict(cursor.fetchone())
            
            # By type
            cursor.execute("""
                SELECT 
                    document_type,
                    COUNT(*) as type_count
                FROM build_documents
                GROUP BY document_type
                ORDER BY type_count DESC
            """)
            by_type = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                'overall': overall,
                'by_type': by_type
            }
            
        except Exception as e:
            print(f"Failed to get document stats: {e}")
            return {'overall': {}, 'by_type': []}