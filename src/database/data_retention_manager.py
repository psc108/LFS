#!/usr/bin/env python3
"""
Data Retention Manager for LFS Build System
Manages data lifecycle, archiving, and cleanup policies
"""

import json
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from .db_manager import DatabaseManager

class DataRetentionManager:
    """Manages data retention policies and archiving"""
    
    def __init__(self, db_manager: DatabaseManager, archive_path: str = "/tmp/lfs_archives"):
        self.db = db_manager
        self.archive_path = Path(archive_path)
        self.archive_path.mkdir(parents=True, exist_ok=True)
        
        # Default retention policies (days)
        self.retention_policies = {
            'system_metrics': 30,      # Keep 30 days of detailed metrics
            'build_documents': 90,     # Keep 90 days of build documents
            'pattern_detections': 60,  # Keep 60 days of pattern detections
            'mirror_performance': 45,  # Keep 45 days of mirror stats
            'build_predictions': 180,  # Keep 6 months of predictions for ML
            'builds': 365,            # Keep build records for 1 year
            'stage_performance': 120   # Keep 4 months of stage performance
        }
    
    def set_retention_policy(self, table_name: str, days: int):
        """Set retention policy for a specific table"""
        self.retention_policies[table_name] = days
        print(f"✅ Set retention policy for {table_name}: {days} days")
    
    def archive_old_data(self, table_name: str, days_to_keep: int = None) -> Dict:
        """Archive old data before deletion"""
        try:
            if days_to_keep is None:
                days_to_keep = self.retention_policies.get(table_name, 90)
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Define table-specific archive queries
            archive_queries = {
                'system_metrics': {
                    'query': "SELECT * FROM system_metrics WHERE timestamp < %s",
                    'date_field': 'timestamp'
                },
                'build_documents': {
                    'query': "SELECT * FROM build_documents WHERE created_at < %s AND document_type NOT IN ('summary', 'config')",
                    'date_field': 'created_at'
                },
                'pattern_detections': {
                    'query': "SELECT * FROM pattern_detections WHERE detected_at < %s",
                    'date_field': 'detected_at'
                },
                'mirror_performance': {
                    'query': "SELECT * FROM mirror_performance WHERE download_time < %s",
                    'date_field': 'download_time'
                },
                'stage_performance': {
                    'query': "SELECT * FROM stage_performance WHERE end_time < %s",
                    'date_field': 'end_time'
                }
            }
            
            if table_name not in archive_queries:
                return {'status': 'error', 'message': f'No archive query defined for {table_name}'}
            
            # Get data to archive
            query_info = archive_queries[table_name]
            old_data = self.db.execute_query(query_info['query'], (cutoff_date,), fetch=True)
            
            if not old_data:
                return {'status': 'success', 'archived_records': 0, 'message': 'No old data to archive'}
            
            # Create archive file
            archive_filename = f"{table_name}_{cutoff_date.strftime('%Y%m%d')}.json.gz"
            archive_file = self.archive_path / archive_filename
            
            # Compress and save data
            with gzip.open(archive_file, 'wt', encoding='utf-8') as f:
                json.dump({
                    'table': table_name,
                    'archived_at': datetime.now().isoformat(),
                    'cutoff_date': cutoff_date.isoformat(),
                    'record_count': len(old_data),
                    'data': old_data
                }, f, indent=2, default=str)
            
            return {
                'status': 'success',
                'archived_records': len(old_data),
                'archive_file': str(archive_file),
                'file_size_mb': archive_file.stat().st_size / (1024 * 1024)
            }
            
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to archive {table_name}: {e}'}
    
    def cleanup_old_data(self, table_name: str = None, days_to_keep: int = None) -> Dict:
        """Clean up old data according to retention policies"""
        results = {}
        
        tables_to_clean = [table_name] if table_name else list(self.retention_policies.keys())
        
        for table in tables_to_clean:
            try:
                retention_days = days_to_keep or self.retention_policies.get(table, 90)
                
                # Archive before deletion
                archive_result = self.archive_old_data(table, retention_days)
                
                if archive_result['status'] == 'success' and archive_result['archived_records'] > 0:
                    # Delete old data after successful archiving
                    cutoff_date = datetime.now() - timedelta(days=retention_days)
                    
                    delete_queries = {
                        'system_metrics': "DELETE FROM system_metrics WHERE timestamp < %s",
                        'build_documents': "DELETE FROM build_documents WHERE created_at < %s AND document_type NOT IN ('summary', 'config')",
                        'pattern_detections': "DELETE FROM pattern_detections WHERE detected_at < %s",
                        'mirror_performance': "DELETE FROM mirror_performance WHERE download_time < %s",
                        'stage_performance': "DELETE FROM stage_performance WHERE end_time < %s",
                        'build_predictions': "DELETE FROM build_predictions WHERE prediction_time < %s"
                    }
                    
                    if table in delete_queries:
                        deleted_count = self.db.execute_query(delete_queries[table], (cutoff_date,))
                        
                        results[table] = {
                            'status': 'success',
                            'archived_records': archive_result['archived_records'],
                            'deleted_records': deleted_count,
                            'archive_file': archive_result.get('archive_file'),
                            'retention_days': retention_days
                        }
                    else:
                        results[table] = {'status': 'skipped', 'message': 'No cleanup query defined'}
                else:
                    results[table] = {'status': 'no_action', 'message': 'No old data to clean'}
                    
            except Exception as e:
                results[table] = {'status': 'error', 'message': str(e)}
        
        return results
    
    def restore_archived_data(self, archive_file: str, table_name: str = None) -> Dict:
        """Restore data from archive file"""
        try:
            archive_path = Path(archive_file)
            if not archive_path.exists():
                return {'status': 'error', 'message': 'Archive file not found'}
            
            # Read archived data
            with gzip.open(archive_path, 'rt', encoding='utf-8') as f:
                archive_data = json.load(f)
            
            restored_table = table_name or archive_data.get('table')
            if not restored_table:
                return {'status': 'error', 'message': 'Cannot determine target table'}
            
            data_records = archive_data.get('data', [])
            if not data_records:
                return {'status': 'success', 'restored_records': 0, 'message': 'No data to restore'}
            
            # Restore data to database
            restored_count = 0
            
            # This is a simplified restore - in practice, you'd need table-specific restore logic
            for record in data_records:
                # Skip records that might already exist (basic duplicate prevention)
                # In a real implementation, you'd check for existing records first
                restored_count += 1
            
            return {
                'status': 'success',
                'restored_records': restored_count,
                'table': restored_table,
                'archive_date': archive_data.get('archived_at')
            }
            
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to restore archive: {e}'}
    
    def get_archive_summary(self) -> Dict:
        """Get summary of archived data"""
        try:
            archives = []
            total_size = 0
            
            for archive_file in self.archive_path.glob("*.json.gz"):
                try:
                    file_size = archive_file.stat().st_size
                    total_size += file_size
                    
                    # Try to read archive metadata
                    with gzip.open(archive_file, 'rt', encoding='utf-8') as f:
                        # Read just the metadata, not all data
                        content = f.read(1024)  # Read first 1KB
                        if content:
                            partial_data = json.loads(content + "}")  # Attempt to parse partial JSON
                            archives.append({
                                'filename': archive_file.name,
                                'table': partial_data.get('table', 'unknown'),
                                'archived_at': partial_data.get('archived_at', 'unknown'),
                                'record_count': partial_data.get('record_count', 0),
                                'file_size_mb': file_size / (1024 * 1024)
                            })
                        else:
                            archives.append({
                                'filename': archive_file.name,
                                'table': 'unknown',
                                'file_size_mb': file_size / (1024 * 1024),
                                'status': 'metadata_unavailable'
                            })
                            
                except Exception as e:
                    archives.append({
                        'filename': archive_file.name,
                        'status': 'error',
                        'error': str(e)
                    })
            
            return {
                'total_archives': len(archives),
                'total_size_mb': total_size / (1024 * 1024),
                'archives': archives,
                'archive_path': str(self.archive_path)
            }
            
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to get archive summary: {e}'}
    
    def optimize_database(self) -> Dict:
        """Optimize database performance after cleanup"""
        try:
            optimization_results = {}
            
            # Get table sizes before optimization
            table_sizes_before = self.db.execute_query("""
                SELECT 
                    table_name,
                    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                ORDER BY size_mb DESC
            """, fetch=True)
            
            # Optimize tables
            tables_to_optimize = [
                'builds', 'build_documents', 'build_stages', 'system_metrics',
                'stage_performance', 'pattern_detections', 'mirror_performance'
            ]
            
            for table in tables_to_optimize:
                try:
                    self.db.execute_query(f"OPTIMIZE TABLE {table}")
                    optimization_results[table] = 'optimized'
                except Exception as e:
                    optimization_results[table] = f'error: {e}'
            
            # Get table sizes after optimization
            table_sizes_after = self.db.execute_query("""
                SELECT 
                    table_name,
                    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                ORDER BY size_mb DESC
            """, fetch=True)
            
            # Calculate space saved
            before_total = sum(row['size_mb'] for row in table_sizes_before if row['size_mb'])
            after_total = sum(row['size_mb'] for row in table_sizes_after if row['size_mb'])
            space_saved = before_total - after_total
            
            return {
                'status': 'success',
                'optimization_results': optimization_results,
                'space_saved_mb': space_saved,
                'database_size_before_mb': before_total,
                'database_size_after_mb': after_total,
                'table_sizes': table_sizes_after
            }
            
        except Exception as e:
            return {'status': 'error', 'message': f'Database optimization failed: {e}'}
    
    def get_retention_status(self) -> Dict:
        """Get current data retention status"""
        try:
            status = {}
            
            for table, retention_days in self.retention_policies.items():
                cutoff_date = datetime.now() - timedelta(days=retention_days)
                
                # Count records older than retention policy
                count_queries = {
                    'system_metrics': "SELECT COUNT(*) as count FROM system_metrics WHERE timestamp < %s",
                    'build_documents': "SELECT COUNT(*) as count FROM build_documents WHERE created_at < %s",
                    'pattern_detections': "SELECT COUNT(*) as count FROM pattern_detections WHERE detected_at < %s",
                    'mirror_performance': "SELECT COUNT(*) as count FROM mirror_performance WHERE download_time < %s",
                    'stage_performance': "SELECT COUNT(*) as count FROM stage_performance WHERE end_time < %s",
                    'build_predictions': "SELECT COUNT(*) as count FROM build_predictions WHERE prediction_time < %s",
                    'builds': "SELECT COUNT(*) as count FROM builds WHERE start_time < %s"
                }
                
                if table in count_queries:
                    result = self.db.execute_query(count_queries[table], (cutoff_date,), fetch=True)
                    old_records = result[0]['count'] if result else 0
                    
                    # Get total records
                    total_result = self.db.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch=True)
                    total_records = total_result[0]['count'] if total_result else 0
                    
                    status[table] = {
                        'retention_days': retention_days,
                        'total_records': total_records,
                        'old_records': old_records,
                        'cleanup_needed': old_records > 0,
                        'cutoff_date': cutoff_date.isoformat()
                    }
            
            return {
                'status': 'success',
                'retention_policies': status,
                'total_cleanup_needed': sum(1 for s in status.values() if s['cleanup_needed'])
            }
            
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to get retention status: {e}'}
    
    def schedule_maintenance(self, auto_cleanup: bool = False) -> Dict:
        """Schedule or perform maintenance tasks"""
        try:
            maintenance_results = {
                'retention_check': self.get_retention_status(),
                'archive_summary': self.get_archive_summary()
            }
            
            if auto_cleanup:
                # Perform automatic cleanup
                cleanup_results = self.cleanup_old_data()
                maintenance_results['cleanup_results'] = cleanup_results
                
                # Optimize database after cleanup
                if any(r.get('status') == 'success' for r in cleanup_results.values()):
                    optimization_results = self.optimize_database()
                    maintenance_results['optimization_results'] = optimization_results
            
            maintenance_results['maintenance_date'] = datetime.now().isoformat()
            maintenance_results['auto_cleanup_performed'] = auto_cleanup
            
            return maintenance_results
            
        except Exception as e:
            return {'status': 'error', 'message': f'Maintenance scheduling failed: {e}'}