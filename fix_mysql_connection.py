#!/usr/bin/env python3

# Read the current db_manager.py
with open('src/database/db_manager.py', 'r') as f:
    content = f.read()

# Add connection recovery and better error handling
connection_fixes = '''
    def ensure_connection(self):
        """Ensure database connection is alive, reconnect if needed"""
        try:
            if hasattr(self, '_connection') and self._connection:
                # Test connection with a simple query
                cursor = self._connection.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                return self._connection
        except:
            # Connection is dead, clear it
            if hasattr(self, '_connection'):
                try:
                    self._connection.close()
                except:
                    pass
                self._connection = None
        
        # Create new connection
        return self.connect()
    
    def execute_with_retry(self, query, params=None, max_retries=3):
        """Execute query with automatic retry on connection failure"""
        for attempt in range(max_retries):
            try:
                conn = self.ensure_connection()
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                result = cursor.fetchall()
                conn.commit()
                cursor.close()
                return result
                
            except Exception as e:
                print(f"Database query attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                # Clear connection for retry
                if hasattr(self, '_connection'):
                    try:
                        self._connection.close()
                    except:
                        pass
                    self._connection = None
                time.sleep(1)  # Brief delay before retry
        
        return None
'''

# Insert the new methods after the connect method
content = content.replace(
    '        return conn\n    \n    def create_tables(self):',
    '        return conn\n    \n' + connection_fixes + '\n    def create_tables(self):'
)

# Update add_document method to use retry mechanism
old_add_document = '''    def add_document(self, build_id: str, document_type: str, title: str, content: str, metadata: dict = None):
        """Add a document to the build"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute("""
                INSERT INTO build_documents (build_id, document_type, title, content, metadata)
                VALUES (%s, %s, %s, %s, %s)
            """, (build_id, document_type, title, content, metadata_json))
            
            conn.commit()
            cursor.close()
            
            print(f"📄 Document saved: {document_type} - {title} ({len(content)} chars) for build {build_id}")
            return True
            
        except Exception as e:
            print(f"Failed to add document: {e}")
            return False'''

new_add_document = '''    def add_document(self, build_id: str, document_type: str, title: str, content: str, metadata: dict = None):
        """Add a document to the build"""
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            self.execute_with_retry("""
                INSERT INTO build_documents (build_id, document_type, title, content, metadata)
                VALUES (%s, %s, %s, %s, %s)
            """, (build_id, document_type, title, content, metadata_json))
            
            print(f"📄 Document saved: {document_type} - {title} ({len(content)} chars) for build {build_id}")
            return True
            
        except Exception as e:
            print(f"Failed to add document: {e}")
            return False'''

content = content.replace(old_add_document, new_add_document)

# Update create_build method
old_create_build = '''    def create_build(self, build_id: str, config_name: str, total_stages: int) -> bool:
        """Create a new build record"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO builds (build_id, config_name, status, total_stages, completed_stages, start_time)
                VALUES (%s, %s, 'running', %s, 0, NOW())
            """, (build_id, config_name, total_stages))
            
            conn.commit()
            cursor.close()
            return True
            
        except Exception as e:
            print(f"Failed to create build: {e}")
            return False'''

new_create_build = '''    def create_build(self, build_id: str, config_name: str, total_stages: int) -> bool:
        """Create a new build record"""
        try:
            self.execute_with_retry("""
                INSERT INTO builds (build_id, config_name, status, total_stages, completed_stages, start_time)
                VALUES (%s, %s, 'running', %s, 0, NOW())
            """, (build_id, config_name, total_stages))
            
            return True
            
        except Exception as e:
            print(f"Failed to create build: {e}")
            return False'''

content = content.replace(old_create_build, new_create_build)

# Add import for time module
if 'import time' not in content:
    content = content.replace('import json', 'import json\nimport time')

# Write the updated content
with open('src/database/db_manager.py', 'w') as f:
    f.write(content)

print("✅ Fixed MySQL connection handling with retry mechanism")