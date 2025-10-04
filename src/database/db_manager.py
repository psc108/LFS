import mysql.connector
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

class DatabaseManager:
    def __init__(self, host='localhost', user='lfs_user', password='lfs_pass', database='lfs_builds'):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }
        self.connection = None
        self.init_database()
    
    def connect(self):
        if not self.connection or not self.connection.is_connected():
            self.connection = mysql.connector.connect(**self.config)
        return self.connection
    
    def init_database(self):
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS builds (
                id INT AUTO_INCREMENT PRIMARY KEY,
                build_id VARCHAR(64) UNIQUE NOT NULL,
                status ENUM('running', 'success', 'failed', 'cancelled') NOT NULL,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP NULL,
                config_hash VARCHAR(64),
                total_stages INT DEFAULT 0,
                completed_stages INT DEFAULT 0,
                INDEX idx_status (status),
                INDEX idx_start_time (start_time)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS build_stages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                build_id VARCHAR(64) NOT NULL,
                stage_name VARCHAR(128) NOT NULL,
                stage_order INT NOT NULL,
                status ENUM('pending', 'running', 'success', 'failed', 'skipped') NOT NULL,
                start_time TIMESTAMP NULL,
                end_time TIMESTAMP NULL,
                output_log LONGTEXT,
                error_log LONGTEXT,
                FOREIGN KEY (build_id) REFERENCES builds(build_id) ON DELETE CASCADE,
                INDEX idx_build_stage (build_id, stage_order)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS build_documents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                build_id VARCHAR(64) NOT NULL,
                document_type ENUM('log', 'config', 'output', 'error', 'summary') NOT NULL,
                title VARCHAR(255) NOT NULL,
                content LONGTEXT NOT NULL,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (build_id) REFERENCES builds(build_id) ON DELETE CASCADE,
                FULLTEXT(title, content)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repo_snapshots (
                id INT AUTO_INCREMENT PRIMARY KEY,
                build_id VARCHAR(64) NOT NULL,
                commit_hash VARCHAR(64) NOT NULL,
                branch_name VARCHAR(128) DEFAULT 'main',
                snapshot_data LONGBLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (build_id) REFERENCES builds(build_id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        cursor.close()
    
    def create_build(self, build_id: str, config_hash: str, total_stages: int) -> bool:
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO builds (build_id, status, config_hash, total_stages)
                VALUES (%s, 'running', %s, %s)
            """, (build_id, config_hash, total_stages))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Error creating build: {e}")
            return False
    
    def update_build_status(self, build_id: str, status: str, completed_stages: int = None):
        conn = self.connect()
        cursor = conn.cursor()
        
        update_fields = ["status = %s"]
        params = [status]
        
        if status in ['success', 'failed', 'cancelled']:
            update_fields.append("end_time = NOW()")
        
        if completed_stages is not None:
            update_fields.append("completed_stages = %s")
            params.append(completed_stages)
        
        params.append(build_id)
        
        cursor.execute(f"""
            UPDATE builds SET {', '.join(update_fields)}
            WHERE build_id = %s
        """, params)
        conn.commit()
        cursor.close()
    
    def add_stage_log(self, build_id: str, stage_name: str, stage_order: int, 
                     status: str, output_log: str = "", error_log: str = ""):
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO build_stages 
            (build_id, stage_name, stage_order, status, start_time, output_log, error_log)
            VALUES (%s, %s, %s, %s, NOW(), %s, %s)
            ON DUPLICATE KEY UPDATE
            status = VALUES(status),
            end_time = IF(VALUES(status) IN ('success', 'failed'), NOW(), end_time),
            output_log = CONCAT(output_log, VALUES(output_log)),
            error_log = CONCAT(error_log, VALUES(error_log))
        """, (build_id, stage_name, stage_order, status, output_log, error_log))
        conn.commit()
        cursor.close()
    
    def add_document(self, build_id: str, doc_type: str, title: str, 
                    content: str, metadata: Dict = None):
        conn = self.connect()
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute("""
            INSERT INTO build_documents (build_id, document_type, title, content, metadata)
            VALUES (%s, %s, %s, %s, %s)
        """, (build_id, doc_type, title, content, metadata_json))
        conn.commit()
        cursor.close()
    
    def search_builds(self, query: str = "", status: str = "", limit: int = 100) -> List[Dict]:
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        
        where_conditions = []
        params = []
        
        if status:
            where_conditions.append("b.status = %s")
            params.append(status)
        
        if query:
            where_conditions.append("""
                (b.build_id LIKE %s OR 
                 EXISTS (SELECT 1 FROM build_documents bd 
                        WHERE bd.build_id = b.build_id 
                        AND MATCH(bd.title, bd.content) AGAINST(%s IN NATURAL LANGUAGE MODE)))
            """)
            params.extend([f"%{query}%", query])
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        cursor.execute(f"""
            SELECT b.*, 
                   TIMESTAMPDIFF(SECOND, b.start_time, COALESCE(b.end_time, NOW())) as duration_seconds
            FROM builds b
            {where_clause}
            ORDER BY b.start_time DESC
            LIMIT %s
        """, params + [limit])
        
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def get_build_details(self, build_id: str) -> Dict:
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM builds WHERE build_id = %s", (build_id,))
        build = cursor.fetchone()
        
        if not build:
            return {}
        
        cursor.execute("""
            SELECT * FROM build_stages 
            WHERE build_id = %s 
            ORDER BY stage_order
        """, (build_id,))
        stages = cursor.fetchall()
        
        cursor.execute("""
            SELECT * FROM build_documents 
            WHERE build_id = %s 
            ORDER BY created_at
        """, (build_id,))
        documents = cursor.fetchall()
        
        cursor.close()
        
        return {
            'build': build,
            'stages': stages,
            'documents': documents
        }