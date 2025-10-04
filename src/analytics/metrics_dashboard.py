import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

class MetricsDashboard:
    def __init__(self, db_manager, cache_dir: str = "metrics_cache"):
        self.db = db_manager
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_build_metrics(self, days: int = 30) -> Dict:
        """Get build metrics for dashboard"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DATE(created_at) as build_date, 
                       status,
                       COUNT(*) as count
                FROM builds 
                WHERE created_at >= DATE('now', '-{} days')
                GROUP BY DATE(created_at), status
                ORDER BY build_date
            """.format(days))
            
            build_data = cursor.fetchall()
            
            cursor.execute("""
                SELECT status, 
                       AVG(JULIANDAY(updated_at) - JULIANDAY(created_at)) * 24 * 60 as avg_duration_minutes,
                       COUNT(*) as count
                FROM builds 
                WHERE created_at >= DATE('now', '-{} days')
                  AND updated_at IS NOT NULL
                GROUP BY status
            """.format(days))
            
            duration_data = cursor.fetchall()
            
            cursor.close()
            
            return {
                'build_trends': self._process_build_trends(build_data),
                'duration_stats': self._process_duration_stats(duration_data),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error generating metrics: {e}")
            return {}
    
    def _process_build_trends(self, data: List) -> Dict:
        """Process build trend data"""
        trends = {}
        for date, status, count in data:
            if date not in trends:
                trends[date] = {'success': 0, 'failed': 0, 'cancelled': 0}
            trends[date][status] = count
        
        for date in trends:
            total = sum(trends[date].values())
            trends[date]['success_rate'] = (trends[date]['success'] / total * 100) if total > 0 else 0
        
        return trends
    
    def _process_duration_stats(self, data: List) -> Dict:
        """Process build duration statistics"""
        stats = {}
        for status, avg_duration, count in data:
            stats[status] = {
                'avg_duration_minutes': round(avg_duration, 2) if avg_duration else 0,
                'count': count
            }
        return stats
    
    def get_resource_utilization(self) -> Dict:
        """Get system resource utilization metrics"""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu': {'percent': cpu_percent, 'count': psutil.cpu_count()},
                'memory': {
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'percent': memory.percent
                },
                'disk': {
                    'total_gb': round(disk.total / (1024**3), 2),
                    'free_gb': round(disk.free / (1024**3), 2),
                    'percent': round((disk.used / disk.total) * 100, 2)
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting resource utilization: {e}")
            return {}