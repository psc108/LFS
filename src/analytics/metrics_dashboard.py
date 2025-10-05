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
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(created_at), status
                ORDER BY build_date
            """, (days,))
            
            build_data = cursor.fetchall()
            
            cursor.execute("""
                SELECT status, 
                       AVG(TIMESTAMPDIFF(MINUTE, created_at, updated_at)) as avg_duration_minutes,
                       COUNT(*) as count
                FROM builds 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                  AND updated_at IS NOT NULL
                GROUP BY status
            """, (days,))
            
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
    
    def get_performance_overview(self) -> Dict:
        """Get performance overview metrics"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_builds,
                    AVG(CASE WHEN status = 'success' THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
                    AVG(TIMESTAMPDIFF(MINUTE, created_at, updated_at)) as avg_duration,
                    MIN(TIMESTAMPDIFF(MINUTE, created_at, updated_at)) as fastest_build
                FROM builds 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                  AND updated_at IS NOT NULL
            """)
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    'total_builds': result[0] or 0,
                    'success_rate': round(result[1] or 0, 1),
                    'avg_build_duration': round(result[2] or 0, 1),
                    'fastest_build': round(result[3] or 0, 1)
                }
            else:
                return {'total_builds': 0, 'success_rate': 0, 'avg_build_duration': 0, 'fastest_build': 0}
                
        except Exception as e:
            print(f"Error getting performance overview: {e}")
            return {'total_builds': 0, 'success_rate': 0, 'avg_build_duration': 0, 'fastest_build': 0}
    
    def get_recent_performance(self, limit: int = 10) -> List[Dict]:
        """Get recent build performance data"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    build_id,
                    status,
                    TIMESTAMPDIFF(MINUTE, created_at, updated_at) / (24 * 60) as duration_days,
                    created_at
                FROM builds 
                WHERE updated_at IS NOT NULL
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                duration_minutes = (row[2] * 24 * 60) if row[2] else 0
                efficiency = min(100, max(0, 100 - (duration_minutes / 60) * 2))
                
                results.append({
                    'build_id': row[0],
                    'status': row[1],
                    'duration': round(duration_minutes, 1),
                    'efficiency': round(efficiency, 0)
                })
            
            cursor.close()
            return results
            
        except Exception as e:
            print(f"Error getting recent performance: {e}")
            return []
    
    def get_stage_performance(self) -> List[Dict]:
        """Get stage performance analysis"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    stage_name,
                    AVG(TIMESTAMPDIFF(MINUTE, start_time, end_time)) as avg_duration,
                    AVG(CASE WHEN status = 'success' THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
                    COUNT(*) as total_runs
                FROM build_stages 
                WHERE start_time IS NOT NULL AND end_time IS NOT NULL
                GROUP BY stage_name
                ORDER BY avg_duration DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                avg_duration = row[1] or 0
                success_rate = row[2] or 0
                
                if avg_duration > 30:
                    bottleneck_risk = "High"
                elif avg_duration > 15:
                    bottleneck_risk = "Medium"
                else:
                    bottleneck_risk = "Low"
                
                if success_rate < 80:
                    optimization = "Review error patterns"
                elif avg_duration > 20:
                    optimization = "Consider parallelization"
                else:
                    optimization = "Optimize for speed"
                
                results.append({
                    'name': row[0],
                    'avg_duration': round(avg_duration, 1),
                    'success_rate': round(success_rate, 1),
                    'bottleneck_risk': bottleneck_risk,
                    'optimization': optimization
                })
            
            cursor.close()
            return results
            
        except Exception as e:
            print(f"Error getting stage performance: {e}")
            return []
    
    def get_resource_metrics(self) -> Dict:
        """Get resource utilization metrics"""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            disk_io = psutil.disk_io_counters()
            net_io = psutil.net_io_counters()
            
            return {
                'avg_cpu': round(cpu_percent, 1),
                'peak_memory': round(memory.total / (1024**3), 1),
                'disk_io': round((disk_io.read_bytes + disk_io.write_bytes) / (1024**2), 1) if disk_io else 0,
                'network': round((net_io.bytes_sent + net_io.bytes_recv) / (1024**2), 1) if net_io else 0
            }
            
        except Exception as e:
            print(f"Error getting resource metrics: {e}")
            return {'avg_cpu': 0, 'peak_memory': 0, 'disk_io': 0, 'network': 0}