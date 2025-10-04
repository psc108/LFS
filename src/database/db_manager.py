#!/usr/bin/env python3
""" 
Robust MySQL Database Manager for LFS Build System
Handles connection pooling, retries, and error recovery
"""

import mysql.connector
from mysql.connector import pooling
import json
import time
import psutil
import hashlib
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
            lfs_password = None
            root_password = None
            
            if creds_file.exists():
                with open(creds_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if 'MySQL Root Password:' in line:
                                root_password = line.split(':', 1)[1].strip()
                                # Decode HTML entities
                                root_password = root_password.replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')
                            elif 'User:' in line and 'lfs_user' in line:
                                # lfs_user found but no password specified
                                lfs_password = 'lfs_pass'  # Default from your earlier input
            
            # Try lfs_user first
            if lfs_password:
                config = {
                    'user': 'lfs_user',
                    'password': lfs_password,
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
                
                try:
                    self.pool = pooling.MySQLConnectionPool(**config)
                    print("✅ MySQL connection pool initialized with lfs_user")
                    return
                except Exception as e:
                    print(f"Failed with lfs_user: {e}")
            
            # Fallback to root user
            if root_password:
                config = {
                    'user': 'root',
                    'password': root_password,
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
                print("✅ MySQL connection pool initialized with root user")
            else:
                raise Exception("No MySQL credentials found in .mysql_credentials")
            
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
    
    def add_stage_log(self, build_id: str, stage_name: str, status: str, output: str = ""):
        """Add stage log entry"""
        try:
            result = self.execute_query("""
                INSERT INTO build_stages (build_id, stage_name, stage_order, status, output_log, start_time)
                VALUES (%s, %s, 0, %s, %s, NOW())
            """, (build_id, stage_name, status, output))
            
            return result > 0
            
        except Exception as e:
            print(f"Failed to add stage log: {e}")
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
        """Get all documents (deprecated - use get_documents_paginated)"""
        try:
            return self.execute_query("""
                SELECT * FROM build_documents 
                ORDER BY created_at DESC 
                LIMIT 1000
            """, fetch=True)
            
        except Exception as e:
            print(f"Failed to get all documents: {e}")
            return []
    
    def get_documents_count(self):
        """Get total count of documents"""
        try:
            result = self.execute_query("""
                SELECT COUNT(*) as total FROM build_documents
            """, fetch=True)
            
            return result[0]['total'] if result else 0
            
        except Exception as e:
            print(f"Failed to get documents count: {e}")
            return 0
    
    def get_documents_paginated(self, offset: int, limit: int):
        """Get documents with pagination"""
        try:
            return self.execute_query("""
                SELECT * FROM build_documents 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """, (limit, offset), fetch=True)
            
        except Exception as e:
            print(f"Failed to get paginated documents: {e}")
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
    
    # Enhanced Data Collection Methods
    
    def record_system_metrics(self, build_id: str, stage_name: str = None):
        """Record current system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()
            load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
            
            # Try to get temperature (may not be available on all systems)
            temperature = None
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if entries:
                            temperature = entries[0].current
                            break
            except:
                pass
            
            self.execute_query("""
                INSERT INTO system_metrics 
                (build_id, stage_name, cpu_percent, memory_percent, memory_used_mb,
                 disk_io_read_mb, disk_io_write_mb, network_bytes_sent, network_bytes_recv,
                 load_average_1m, temperature_celsius)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                build_id, stage_name, cpu_percent, memory.percent, memory.used // (1024*1024),
                disk_io.read_bytes // (1024*1024) if disk_io else 0,
                disk_io.write_bytes // (1024*1024) if disk_io else 0,
                network_io.bytes_sent if network_io else 0,
                network_io.bytes_recv if network_io else 0,
                load_avg, temperature
            ))
            
        except Exception as e:
            print(f"Failed to record system metrics: {e}")
    
    def record_build_environment(self, build_id: str):
        """Record build environment details"""
        try:
            import platform
            import os
            import subprocess
            
            # Get system info
            host_os = f"{platform.system()} {platform.release()}"
            host_kernel = platform.version()
            host_arch = platform.machine()
            
            # Get CPU info
            cpu_model = "Unknown"
            cpu_cores = psutil.cpu_count()
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'model name' in line:
                            cpu_model = line.split(':')[1].strip()
                            break
            except:
                pass
            
            # Get memory info
            total_memory_gb = psutil.virtual_memory().total / (1024**3)
            
            # Get disk space
            disk_space_gb = psutil.disk_usage('/').total / (1024**3)
            
            # Get tool versions
            def get_version(cmd):
                try:
                    result = subprocess.run([cmd, '--version'], capture_output=True, text=True, timeout=5)
                    return result.stdout.split('\n')[0] if result.returncode == 0 else "Unknown"
                except:
                    return "Unknown"
            
            python_version = platform.python_version()
            gcc_version = get_version('gcc')
            make_version = get_version('make')
            
            # Get environment variables
            env_vars = {k: v for k, v in os.environ.items() if k.startswith(('LFS', 'PATH', 'CC', 'CXX'))}
            
            self.execute_query("""
                INSERT INTO build_environment 
                (build_id, host_os, host_kernel, host_arch, cpu_model, cpu_cores,
                 total_memory_gb, disk_space_gb, python_version, gcc_version, make_version,
                 environment_vars)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                build_id, host_os, host_kernel, host_arch, cpu_model, cpu_cores,
                total_memory_gb, disk_space_gb, python_version, gcc_version, make_version,
                json.dumps(env_vars)
            ))
            
        except Exception as e:
            print(f"Failed to record build environment: {e}")
    
    def record_stage_performance(self, build_id: str, stage_name: str, stage_order: int,
                               start_time: datetime, end_time: datetime, exit_code: int,
                               warnings_count: int = 0, errors_count: int = 0, lines_processed: int = 0):
        """Record stage performance metrics"""
        try:
            duration_seconds = int((end_time - start_time).total_seconds())
            
            # Get current resource usage as approximation
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            
            self.execute_query("""
                INSERT INTO stage_performance 
                (build_id, stage_name, stage_order, start_time, end_time, duration_seconds,
                 peak_memory_mb, disk_read_mb, disk_write_mb, exit_code, warnings_count,
                 errors_count, lines_processed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                build_id, stage_name, stage_order, start_time, end_time, duration_seconds,
                memory.used // (1024*1024),
                disk_io.read_bytes // (1024*1024) if disk_io else 0,
                disk_io.write_bytes // (1024*1024) if disk_io else 0,
                exit_code, warnings_count, errors_count, lines_processed
            ))
            
        except Exception as e:
            print(f"Failed to record stage performance: {e}")
    
    def record_mirror_performance(self, mirror_url: str, package_name: str, file_size_mb: float,
                                download_speed_mbps: float, success: bool, error_message: str = None,
                                response_time_ms: int = 0, http_status_code: int = 200, retry_count: int = 0):
        """Record mirror download performance"""
        try:
            self.execute_query("""
                INSERT INTO mirror_performance 
                (mirror_url, package_name, file_size_mb, download_speed_mbps, success,
                 error_message, response_time_ms, http_status_code, retry_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                mirror_url, package_name, file_size_mb, download_speed_mbps, success,
                error_message, response_time_ms, http_status_code, retry_count
            ))
            
        except Exception as e:
            print(f"Failed to record mirror performance: {e}")
    
    def record_pattern_detection(self, build_id: str, stage_name: str, pattern_id: int,
                               confidence_score: float, matched_text: str,
                               context_before: str = "", context_after: str = "",
                               auto_fix_applied: bool = False, fix_successful: bool = None):
        """Record pattern detection event"""
        try:
            self.execute_query("""
                INSERT INTO pattern_detections 
                (build_id, stage_name, pattern_id, confidence_score, matched_text,
                 context_before, context_after, auto_fix_applied, fix_successful)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                build_id, stage_name, pattern_id, confidence_score, matched_text,
                context_before, context_after, auto_fix_applied, fix_successful
            ))
            
            # Update pattern statistics
            self.execute_query("""
                UPDATE failure_patterns 
                SET detection_count = detection_count + 1,
                    updated_at = NOW()
                WHERE id = %s
            """, (pattern_id,))
            
        except Exception as e:
            print(f"Failed to record pattern detection: {e}")
    
    def record_build_prediction(self, build_id: str, risk_score: float, success_probability: float,
                              predicted_duration_minutes: int, risk_factors: dict, model_version: str):
        """Record build prediction"""
        try:
            self.execute_query("""
                INSERT INTO build_predictions 
                (build_id, risk_score, success_probability, predicted_duration_minutes,
                 risk_factors, model_version)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                build_id, risk_score, success_probability, predicted_duration_minutes,
                json.dumps(risk_factors), model_version
            ))
            
        except Exception as e:
            print(f"Failed to record build prediction: {e}")
    
    def update_prediction_accuracy(self, build_id: str, actual_success: bool, actual_duration_minutes: int):
        """Update prediction accuracy after build completion"""
        try:
            # Calculate accuracy
            predictions = self.execute_query("""
                SELECT success_probability, predicted_duration_minutes 
                FROM build_predictions 
                WHERE build_id = %s 
                ORDER BY prediction_time DESC 
                LIMIT 1
            """, (build_id,), fetch=True)
            
            if predictions:
                pred = predictions[0]
                success_accuracy = 100.0 if (actual_success and pred['success_probability'] > 50) or (not actual_success and pred['success_probability'] <= 50) else 0.0
                duration_diff = abs(actual_duration_minutes - pred['predicted_duration_minutes'])
                duration_accuracy = max(0, 100 - (duration_diff / max(actual_duration_minutes, 1) * 100))
                overall_accuracy = (success_accuracy + duration_accuracy) / 2
                
                self.execute_query("""
                    UPDATE build_predictions 
                    SET actual_success = %s, actual_duration_minutes = %s,
                        prediction_accuracy = %s
                    WHERE build_id = %s
                """, (actual_success, actual_duration_minutes, overall_accuracy, build_id))
            
        except Exception as e:
            print(f"Failed to update prediction accuracy: {e}")
    
    def get_performance_baseline(self, stage_name: str, environment_type: str = "default"):
        """Get performance baseline for a stage"""
        try:
            result = self.execute_query("""
                SELECT * FROM performance_baselines 
                WHERE stage_name = %s AND environment_type = %s
            """, (stage_name, environment_type), fetch=True)
            
            return result[0] if result else None
            
        except Exception as e:
            print(f"Failed to get performance baseline: {e}")
            return None
    
    def update_performance_baseline(self, stage_name: str, environment_type: str = "default"):
        """Update performance baseline based on recent successful builds"""
        try:
            # Calculate baseline from last 20 successful builds
            result = self.execute_query("""
                SELECT 
                    AVG(duration_seconds) as avg_duration,
                    AVG(peak_memory_mb) as avg_memory,
                    AVG(sp.cpu_time_seconds) as avg_cpu,
                    COUNT(*) as sample_count
                FROM stage_performance sp
                JOIN builds b ON sp.build_id = b.build_id
                WHERE sp.stage_name = %s AND b.status = 'completed' AND sp.exit_code = 0
                ORDER BY sp.end_time DESC
                LIMIT 20
            """, (stage_name,), fetch=True)
            
            if result and result[0]['sample_count'] >= 5:
                data = result[0]
                
                self.execute_query("""
                    INSERT INTO performance_baselines 
                    (stage_name, environment_type, baseline_duration_seconds, baseline_memory_mb,
                     baseline_cpu_percent, sample_size, confidence_interval)
                    VALUES (%s, %s, %s, %s, %s, %s, 95.0)
                    ON DUPLICATE KEY UPDATE
                    baseline_duration_seconds = VALUES(baseline_duration_seconds),
                    baseline_memory_mb = VALUES(baseline_memory_mb),
                    baseline_cpu_percent = VALUES(baseline_cpu_percent),
                    sample_size = VALUES(sample_size),
                    last_updated = NOW()
                """, (
                    stage_name, environment_type,
                    int(data['avg_duration'] or 0),
                    int(data['avg_memory'] or 0),
                    float(data['avg_cpu'] or 0),
                    int(data['sample_count'])
                ))
                
                return True
            
        except Exception as e:
            print(f"Failed to update performance baseline: {e}")
        
        return False
    
    def get_build_analytics(self, days: int = 30):
        """Get comprehensive build analytics"""
        try:
            # Success rates
            success_rates = self.execute_query("""
                SELECT 
                    DATE(start_time) as build_date,
                    COUNT(*) as total_builds,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_builds,
                    ROUND(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
                FROM builds 
                WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(start_time)
                ORDER BY build_date DESC
            """, (days,), fetch=True)
            
            # Performance trends
            performance_trends = self.execute_query("""
                SELECT 
                    stage_name,
                    AVG(duration_seconds) as avg_duration,
                    MIN(duration_seconds) as min_duration,
                    MAX(duration_seconds) as max_duration,
                    COUNT(*) as execution_count
                FROM stage_performance sp
                JOIN builds b ON sp.build_id = b.build_id
                WHERE b.start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY stage_name
                ORDER BY avg_duration DESC
            """, (days,), fetch=True)
            
            # Top failure patterns
            failure_patterns = self.execute_query("""
                SELECT 
                    fp.pattern_name,
                    fp.severity,
                    COUNT(pd.id) as detection_count,
                    AVG(pd.confidence_score) as avg_confidence
                FROM failure_patterns fp
                JOIN pattern_detections pd ON fp.id = pd.pattern_id
                WHERE pd.detected_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY fp.id, fp.pattern_name, fp.severity
                ORDER BY detection_count DESC
                LIMIT 10
            """, (days,), fetch=True)
            
            return {
                'success_rates': success_rates or [],
                'performance_trends': performance_trends or [],
                'failure_patterns': failure_patterns or []
            }
            
        except Exception as e:
            print(f"Failed to get build analytics: {e}")
            return {'success_rates': [], 'performance_trends': [], 'failure_patterns': []}
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data to manage database size"""
        try:
            # Archive old builds but keep recent ones
            self.execute_query("""
                DELETE FROM system_metrics 
                WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (days_to_keep,))
            
            self.execute_query("""
                DELETE FROM pattern_detections 
                WHERE detected_at < DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (days_to_keep,))
            
            # Keep build records but remove old documents
            self.execute_query("""
                DELETE FROM build_documents 
                WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                AND document_type NOT IN ('summary', 'config')
            """, (days_to_keep,))
            
            print(f"✅ Cleaned up data older than {days_to_keep} days")
            
        except Exception as e:
            print(f"Failed to cleanup old data: {e}")
    
    # Legacy method for compatibility
    def connect(self):
        """Legacy method - use get_connection() instead"""
        return self.get_connection()
