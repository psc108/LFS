#!/usr/bin/env python3

import psutil
import time
import logging
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from collections import deque

class AnomalyDetector:
    """System health anomaly detection"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.baseline_metrics = {}
        self.metric_history = {
            'cpu': deque(maxlen=100),
            'memory': deque(maxlen=100),
            'disk': deque(maxlen=100),
            'network': deque(maxlen=100),
            'processes': deque(maxlen=100)
        }
        self.thresholds = self._load_thresholds()
        
    def _load_thresholds(self) -> Dict:
        """Load anomaly detection thresholds"""
        return {
            'cpu_usage': {'warning': 80, 'critical': 95},
            'memory_usage': {'warning': 85, 'critical': 95},
            'disk_usage': {'warning': 85, 'critical': 95},
            'disk_io_wait': {'warning': 20, 'critical': 40},
            'load_average': {'warning': 4.0, 'critical': 8.0},
            'process_count': {'warning': 300, 'critical': 500},
            'network_errors': {'warning': 10, 'critical': 50}
        }
    
    def collect_system_metrics(self) -> Dict:
        """Collect current system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network metrics
            network_io = psutil.net_io_counters()
            
            # Process metrics
            process_count = len(psutil.pids())
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'usage_percent': cpu_percent,
                    'count': cpu_count,
                    'load_average_1m': load_avg[0],
                    'load_average_5m': load_avg[1],
                    'load_average_15m': load_avg[2]
                },
                'memory': {
                    'total_gb': memory.total / (1024**3),
                    'available_gb': memory.available / (1024**3),
                    'usage_percent': memory.percent,
                    'swap_usage_percent': swap.percent
                },
                'disk': {
                    'total_gb': disk_usage.total / (1024**3),
                    'free_gb': disk_usage.free / (1024**3),
                    'usage_percent': (disk_usage.used / disk_usage.total) * 100,
                    'read_bytes': disk_io.read_bytes if disk_io else 0,
                    'write_bytes': disk_io.write_bytes if disk_io else 0
                },
                'network': {
                    'bytes_sent': network_io.bytes_sent,
                    'bytes_recv': network_io.bytes_recv,
                    'packets_sent': network_io.packets_sent,
                    'packets_recv': network_io.packets_recv,
                    'errors_in': network_io.errin,
                    'errors_out': network_io.errout
                },
                'processes': {
                    'count': process_count
                }
            }
            
            # Update history
            self._update_metric_history(metrics)
            
            return metrics
            
        except Exception as e:
            logging.error(f"Failed to collect system metrics: {e}")
            return {'error': str(e)}
    
    def _update_metric_history(self, metrics: Dict):
        """Update metric history for trend analysis"""
        self.metric_history['cpu'].append(metrics['cpu']['usage_percent'])
        self.metric_history['memory'].append(metrics['memory']['usage_percent'])
        self.metric_history['disk'].append(metrics['disk']['usage_percent'])
        self.metric_history['processes'].append(metrics['processes']['count'])
    
    def detect_anomalies(self, metrics: Dict = None) -> Dict:
        """Detect system anomalies"""
        if metrics is None:
            metrics = self.collect_system_metrics()
        
        if 'error' in metrics:
            return metrics
        
        anomalies = []
        
        # Store metrics in database for historical analysis
        if self.db_manager and 'timestamp' in metrics:
            try:
                # Create system_metrics table if not exists
                self.db_manager.execute_query("""
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        build_id VARCHAR(50),
                        cpu_percent DECIMAL(5,2),
                        memory_percent DECIMAL(5,2),
                        disk_usage_percent DECIMAL(5,2),
                        load_average_1m DECIMAL(5,2),
                        process_count INT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_build_id (build_id),
                        INDEX idx_timestamp (timestamp)
                    )
                """)
                
                self.db_manager.execute_query(
                    "INSERT INTO system_metrics (build_id, cpu_percent, memory_percent, disk_usage_percent, load_average_1m, process_count, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    ('system_health', metrics['cpu']['usage_percent'], metrics['memory']['usage_percent'], 
                     metrics['disk']['usage_percent'], metrics['cpu']['load_average_1m'], 
                     metrics['processes']['count'], metrics['timestamp'])
                )
                
            except Exception as e:
                logging.warning(f"Failed to store system metrics: {e}")
        
        # CPU anomalies
        cpu_usage = metrics['cpu']['usage_percent']
        if cpu_usage >= self.thresholds['cpu_usage']['critical']:
            anomalies.append({
                'type': 'cpu_critical',
                'severity': 'critical',
                'message': f'Critical CPU usage: {cpu_usage:.1f}%',
                'value': cpu_usage,
                'threshold': self.thresholds['cpu_usage']['critical']
            })
        elif cpu_usage >= self.thresholds['cpu_usage']['warning']:
            anomalies.append({
                'type': 'cpu_warning',
                'severity': 'warning',
                'message': f'High CPU usage: {cpu_usage:.1f}%',
                'value': cpu_usage,
                'threshold': self.thresholds['cpu_usage']['warning']
            })
        
        # Memory anomalies
        memory_usage = metrics['memory']['usage_percent']
        if memory_usage >= self.thresholds['memory_usage']['critical']:
            anomalies.append({
                'type': 'memory_critical',
                'severity': 'critical',
                'message': f'Critical memory usage: {memory_usage:.1f}%',
                'value': memory_usage,
                'threshold': self.thresholds['memory_usage']['critical']
            })
        elif memory_usage >= self.thresholds['memory_usage']['warning']:
            anomalies.append({
                'type': 'memory_warning',
                'severity': 'warning',
                'message': f'High memory usage: {memory_usage:.1f}%',
                'value': memory_usage,
                'threshold': self.thresholds['memory_usage']['warning']
            })
        
        # Disk anomalies
        disk_usage = metrics['disk']['usage_percent']
        if disk_usage >= self.thresholds['disk_usage']['critical']:
            anomalies.append({
                'type': 'disk_critical',
                'severity': 'critical',
                'message': f'Critical disk usage: {disk_usage:.1f}%',
                'value': disk_usage,
                'threshold': self.thresholds['disk_usage']['critical']
            })
        elif disk_usage >= self.thresholds['disk_usage']['warning']:
            anomalies.append({
                'type': 'disk_warning',
                'severity': 'warning',
                'message': f'High disk usage: {disk_usage:.1f}%',
                'value': disk_usage,
                'threshold': self.thresholds['disk_usage']['warning']
            })
        
        # Load average anomalies
        load_avg = metrics['cpu']['load_average_1m']
        if load_avg >= self.thresholds['load_average']['critical']:
            anomalies.append({
                'type': 'load_critical',
                'severity': 'critical',
                'message': f'Critical system load: {load_avg:.2f}',
                'value': load_avg,
                'threshold': self.thresholds['load_average']['critical']
            })
        elif load_avg >= self.thresholds['load_average']['warning']:
            anomalies.append({
                'type': 'load_warning',
                'severity': 'warning',
                'message': f'High system load: {load_avg:.2f}',
                'value': load_avg,
                'threshold': self.thresholds['load_average']['warning']
            })
        
        # Process count anomalies
        process_count = metrics['processes']['count']
        if process_count >= self.thresholds['process_count']['critical']:
            anomalies.append({
                'type': 'process_critical',
                'severity': 'critical',
                'message': f'Critical process count: {process_count}',
                'value': process_count,
                'threshold': self.thresholds['process_count']['critical']
            })
        elif process_count >= self.thresholds['process_count']['warning']:
            anomalies.append({
                'type': 'process_warning',
                'severity': 'warning',
                'message': f'High process count: {process_count}',
                'value': process_count,
                'threshold': self.thresholds['process_count']['warning']
            })
        
        # Trend-based anomalies
        trend_anomalies = self._detect_trend_anomalies()
        anomalies.extend(trend_anomalies)
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'anomalies': anomalies,
            'anomaly_count': len(anomalies),
            'severity_counts': self._count_by_severity(anomalies),
            'system_health_score': self._calculate_health_score(anomalies, metrics)
        }
        
        # Store anomaly detection results in database
        if self.db_manager and anomalies:
            try:
                # Create anomaly_reports table if not exists
                self.db_manager.execute_query("""
                    CREATE TABLE IF NOT EXISTS anomaly_reports (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        anomaly_type VARCHAR(50),
                        severity VARCHAR(20),
                        message TEXT,
                        value_detected DECIMAL(10,2),
                        threshold_value DECIMAL(10,2),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_severity (severity),
                        INDEX idx_type (anomaly_type),
                        INDEX idx_created_at (created_at)
                    )
                """)
                
                for anomaly in anomalies:
                    self.db_manager.execute_query(
                        "INSERT INTO anomaly_reports (anomaly_type, severity, message, value_detected, threshold_value) VALUES (%s, %s, %s, %s, %s)",
                        (anomaly['type'], anomaly['severity'], anomaly['message'], 
                         anomaly['value'], anomaly['threshold'])
                    )
                
            except Exception as e:
                logging.warning(f"Failed to store anomaly results: {e}")
        
        return result
    
    def _detect_trend_anomalies(self) -> List[Dict]:
        """Detect anomalies based on trends"""
        anomalies = []
        
        # CPU trend analysis
        if len(self.metric_history['cpu']) >= 10:
            cpu_trend = np.polyfit(range(len(self.metric_history['cpu'])), 
                                 list(self.metric_history['cpu']), 1)[0]
            if cpu_trend > 2.0:  # Increasing by more than 2% per measurement
                anomalies.append({
                    'type': 'cpu_trend',
                    'severity': 'warning',
                    'message': f'CPU usage trending upward: +{cpu_trend:.1f}% per measurement',
                    'value': cpu_trend,
                    'threshold': 2.0
                })
        
        # Memory trend analysis
        if len(self.metric_history['memory']) >= 10:
            memory_trend = np.polyfit(range(len(self.metric_history['memory'])), 
                                    list(self.metric_history['memory']), 1)[0]
            if memory_trend > 1.5:  # Increasing by more than 1.5% per measurement
                anomalies.append({
                    'type': 'memory_trend',
                    'severity': 'warning',
                    'message': f'Memory usage trending upward: +{memory_trend:.1f}% per measurement',
                    'value': memory_trend,
                    'threshold': 1.5
                })
        
        return anomalies
    
    def _count_by_severity(self, anomalies: List[Dict]) -> Dict:
        """Count anomalies by severity"""
        counts = {'critical': 0, 'warning': 0, 'info': 0}
        for anomaly in anomalies:
            severity = anomaly.get('severity', 'info')
            counts[severity] = counts.get(severity, 0) + 1
        return counts
    
    def _calculate_health_score(self, anomalies: List[Dict], metrics: Dict) -> float:
        """Calculate overall system health score (0-100)"""
        base_score = 100.0
        
        # Deduct points for anomalies
        for anomaly in anomalies:
            if anomaly['severity'] == 'critical':
                base_score -= 20
            elif anomaly['severity'] == 'warning':
                base_score -= 10
            else:
                base_score -= 5
        
        # Additional deductions for high resource usage
        cpu_usage = metrics['cpu']['usage_percent']
        memory_usage = metrics['memory']['usage_percent']
        disk_usage = metrics['disk']['usage_percent']
        
        # Gradual deduction for resource usage
        if cpu_usage > 50:
            base_score -= (cpu_usage - 50) * 0.5
        if memory_usage > 50:
            base_score -= (memory_usage - 50) * 0.3
        if disk_usage > 50:
            base_score -= (disk_usage - 50) * 0.2
        
        return max(0.0, min(100.0, base_score))
    
    def get_health_summary(self) -> Dict:
        """Get comprehensive system health summary"""
        metrics = self.collect_system_metrics()
        if 'error' in metrics:
            return metrics
        
        anomalies = self.detect_anomalies(metrics)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'anomalies': anomalies,
            'recommendations': self._generate_health_recommendations(anomalies, metrics)
        }
    
    def _generate_health_recommendations(self, anomalies: Dict, metrics: Dict) -> List[Dict]:
        """Generate health-based recommendations"""
        recommendations = []
        
        # Critical anomaly recommendations
        for anomaly in anomalies.get('anomalies', []):
            if anomaly['severity'] == 'critical':
                if anomaly['type'].startswith('cpu'):
                    recommendations.append({
                        'priority': 'critical',
                        'title': 'Reduce CPU Load',
                        'description': 'Stop non-essential processes or increase CPU resources',
                        'action': 'immediate'
                    })
                elif anomaly['type'].startswith('memory'):
                    recommendations.append({
                        'priority': 'critical',
                        'title': 'Free Memory',
                        'description': 'Close applications or increase system memory',
                        'action': 'immediate'
                    })
                elif anomaly['type'].startswith('disk'):
                    recommendations.append({
                        'priority': 'critical',
                        'title': 'Free Disk Space',
                        'description': 'Delete unnecessary files or add storage capacity',
                        'action': 'immediate'
                    })
        
        # Preventive recommendations
        health_score = anomalies.get('system_health_score', 100)
        if health_score < 80:
            recommendations.append({
                'priority': 'medium',
                'title': 'System Optimization',
                'description': 'Consider system maintenance and optimization',
                'action': 'scheduled'
            })
        
        return recommendations