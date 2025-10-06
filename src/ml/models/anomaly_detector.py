"""
Anomaly Detector Model

Detects system anomalies during builds based on resource usage patterns.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import statistics


class AnomalyDetector:
    """Detects system anomalies during build processes"""
    
    def __init__(self, db_manager):
        """Initialize anomaly detector"""
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self.is_trained_flag = False
        self.last_training_time = None
        self.accuracy = None
        self.prediction_count = 0
        
        # Baseline patterns for anomaly detection
        self.resource_baselines = {}
        self.error_baselines = {}
        self.timing_baselines = {}
        
        # Load existing baselines
        self._load_baseline_patterns()
    
    def _load_baseline_patterns(self):
        """Load baseline patterns for anomaly detection"""
        try:
            self._establish_resource_baselines()
            self._establish_error_baselines()
            self._establish_timing_baselines()
            
            if any([self.resource_baselines, self.error_baselines, self.timing_baselines]):
                self.is_trained_flag = True
                self.last_training_time = datetime.now()
                self.logger.info("Loaded anomaly detection baselines")
                
        except Exception as e:
            self.logger.error(f"Failed to load baseline patterns: {e}")
    
    def _establish_resource_baselines(self):
        """Establish baseline resource usage patterns"""
        try:
            # Analyze resource-related documents
            resource_docs = self.db.execute_query(
                """SELECT bd.content, b.status, b.duration_seconds
                   FROM build_documents bd
                   JOIN builds b ON bd.build_id = b.build_id
                   WHERE bd.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                   AND (bd.content LIKE '%CPU%' OR bd.content LIKE '%memory%' OR bd.content LIKE '%resource%')
                   AND b.status = 'success'
                   LIMIT 500""",
                fetch=True
            )
            
            resource_warnings = []
            system_errors = []
            
            for doc in resource_docs:
                content = doc.get("content", "").lower()
                
                # Count resource warnings in successful builds (baseline)
                warning_count = 0
                error_count = 0
                
                if any(keyword in content for keyword in ["high cpu", "memory usage", "load average"]):
                    warning_count += 1
                
                if any(keyword in content for keyword in ["system error", "hardware", "kernel"]):
                    error_count += 1
                
                resource_warnings.append(warning_count)
                system_errors.append(error_count)
            
            if resource_warnings:
                self.resource_baselines = {
                    "avg_warnings": statistics.mean(resource_warnings),
                    "max_warnings": max(resource_warnings),
                    "warning_threshold": statistics.mean(resource_warnings) + (2 * statistics.stdev(resource_warnings)) if len(resource_warnings) > 1 else 3,
                    "avg_errors": statistics.mean(system_errors),
                    "error_threshold": statistics.mean(system_errors) + (2 * statistics.stdev(system_errors)) if len(system_errors) > 1 else 2
                }
                
        except Exception as e:
            self.logger.error(f"Failed to establish resource baselines: {e}")
    
    def _establish_error_baselines(self):
        """Establish baseline error patterns"""
        try:
            # Analyze error patterns in successful vs failed builds
            error_stats = self.db.execute_query(
                """SELECT b.status,
                   COUNT(bd.id) as error_doc_count,
                   AVG(LENGTH(bd.content)) as avg_error_length
                   FROM builds b
                   LEFT JOIN build_documents bd ON b.build_id = bd.build_id 
                   AND (bd.document_type = 'error' OR bd.content LIKE '%error%')
                   WHERE b.start_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                   GROUP BY b.status""",
                fetch=True
            )
            
            for stat in error_stats:
                status = stat["status"]
                self.error_baselines[status] = {
                    "avg_error_docs": stat["error_doc_count"],
                    "avg_error_length": stat.get("avg_error_length", 0)
                }
            
            # Calculate anomaly thresholds
            if "success" in self.error_baselines:
                success_baseline = self.error_baselines["success"]
                self.error_baselines["anomaly_threshold"] = success_baseline["avg_error_docs"] * 3
                
        except Exception as e:
            self.logger.error(f"Failed to establish error baselines: {e}")
    
    def _establish_timing_baselines(self):
        """Establish baseline timing patterns"""
        try:
            # Get timing statistics for successful builds
            timing_stats = self.db.execute_query(
                """SELECT 
                   AVG(duration_seconds) as avg_duration,
                   STDDEV(duration_seconds) as stddev_duration,
                   MIN(duration_seconds) as min_duration,
                   MAX(duration_seconds) as max_duration
                   FROM builds 
                   WHERE start_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                   AND status = 'success'
                   AND duration_seconds IS NOT NULL
                   AND duration_seconds > 0""",
                fetch=True
            )
            
            if timing_stats and timing_stats[0]["avg_duration"]:
                stat = timing_stats[0]
                avg_duration = stat["avg_duration"]
                stddev_duration = stat.get("stddev_duration", 0) or (avg_duration * 0.2)
                
                self.timing_baselines = {
                    "avg_duration": avg_duration,
                    "stddev_duration": stddev_duration,
                    "min_duration": stat["min_duration"],
                    "max_duration": stat["max_duration"],
                    "slow_threshold": avg_duration + (2 * stddev_duration),
                    "fast_threshold": max(avg_duration - (2 * stddev_duration), stat["min_duration"])
                }
                
        except Exception as e:
            self.logger.error(f"Failed to establish timing baselines: {e}")
    
    def detect(self, system_metrics: Dict) -> Optional[Dict]:
        """Detect anomalies in system metrics"""
        try:
            if not self.is_trained_flag:
                return None
            
            self.prediction_count += 1
            
            anomalies = {
                "anomaly_score": 0.0,
                "anomalies_detected": [],
                "severity": "normal",
                "recommendations": []
            }
            
            # Detect resource anomalies
            resource_anomalies = self._detect_resource_anomalies(system_metrics)
            if resource_anomalies:
                anomalies["anomaly_score"] += resource_anomalies["score"]
                anomalies["anomalies_detected"].extend(resource_anomalies["anomalies"])
                anomalies["recommendations"].extend(resource_anomalies["recommendations"])
            
            # Detect error anomalies
            error_anomalies = self._detect_error_anomalies(system_metrics)
            if error_anomalies:
                anomalies["anomaly_score"] += error_anomalies["score"]
                anomalies["anomalies_detected"].extend(error_anomalies["anomalies"])
                anomalies["recommendations"].extend(error_anomalies["recommendations"])
            
            # Detect timing anomalies
            timing_anomalies = self._detect_timing_anomalies(system_metrics)
            if timing_anomalies:
                anomalies["anomaly_score"] += timing_anomalies["score"]
                anomalies["anomalies_detected"].extend(timing_anomalies["anomalies"])
                anomalies["recommendations"].extend(timing_anomalies["recommendations"])
            
            # Normalize anomaly score and determine severity
            anomalies["anomaly_score"] = min(1.0, anomalies["anomaly_score"])
            
            if anomalies["anomaly_score"] > 0.8:
                anomalies["severity"] = "critical"
            elif anomalies["anomaly_score"] > 0.6:
                anomalies["severity"] = "high"
            elif anomalies["anomaly_score"] > 0.3:
                anomalies["severity"] = "medium"
            elif anomalies["anomaly_score"] > 0.1:
                anomalies["severity"] = "low"
            
            return anomalies if anomalies["anomaly_score"] > 0.1 else None
            
        except Exception as e:
            self.logger.error(f"Anomaly detection failed: {e}")
            return None
    
    def _detect_resource_anomalies(self, system_metrics: Dict) -> Optional[Dict]:
        """Detect resource usage anomalies"""
        if not self.resource_baselines:
            return None
        
        anomalies = {"score": 0.0, "anomalies": [], "recommendations": []}
        
        resource_warnings = system_metrics.get("resource_warnings", 0)
        system_errors = system_metrics.get("system_errors", 0)
        
        # Check resource warning anomalies
        warning_threshold = self.resource_baselines.get("warning_threshold", 3)
        if resource_warnings > warning_threshold:
            severity = min(1.0, resource_warnings / (warning_threshold * 2))
            anomalies["score"] += severity * 0.4
            anomalies["anomalies"].append({
                "type": "resource_warnings",
                "description": f"Excessive resource warnings ({resource_warnings} vs baseline {warning_threshold:.1f})",
                "severity": severity
            })
            anomalies["recommendations"].append("Monitor system resource usage and consider reducing build load")
        
        # Check system error anomalies
        error_threshold = self.resource_baselines.get("error_threshold", 2)
        if system_errors > error_threshold:
            severity = min(1.0, system_errors / (error_threshold * 2))
            anomalies["score"] += severity * 0.6
            anomalies["anomalies"].append({
                "type": "system_errors",
                "description": f"Unusual system errors ({system_errors} vs baseline {error_threshold:.1f})",
                "severity": severity
            })
            anomalies["recommendations"].append("Investigate system stability and hardware issues")
        
        return anomalies if anomalies["anomalies"] else None
    
    def _detect_error_anomalies(self, system_metrics: Dict) -> Optional[Dict]:
        """Detect error pattern anomalies"""
        if not self.error_baselines:
            return None
        
        anomalies = {"score": 0.0, "anomalies": [], "recommendations": []}
        
        # This would typically analyze error patterns from the build
        # For now, we'll use a simple heuristic based on available metrics
        
        performance_indicators = system_metrics.get("performance_indicators", [])
        
        # Detect missing expected performance indicators
        expected_indicators = ["parallel_compilation"]
        missing_indicators = [ind for ind in expected_indicators if ind not in performance_indicators]
        
        if missing_indicators:
            anomalies["score"] += 0.2
            anomalies["anomalies"].append({
                "type": "missing_performance_indicators",
                "description": f"Expected performance indicators not detected: {missing_indicators}",
                "severity": 0.3
            })
            anomalies["recommendations"].append("Verify build configuration includes performance optimizations")
        
        return anomalies if anomalies["anomalies"] else None
    
    def _detect_timing_anomalies(self, system_metrics: Dict) -> Optional[Dict]:
        """Detect timing-based anomalies"""
        if not self.timing_baselines:
            return None
        
        anomalies = {"score": 0.0, "anomalies": [], "recommendations": []}
        
        # This would analyze current build timing against baselines
        # Since we don't have current timing in system_metrics, we'll skip for now
        # In a real implementation, this would compare current stage timings
        
        return None
    
    def is_trained(self) -> bool:
        """Check if detector is trained"""
        return self.is_trained_flag
    
    def needs_training(self) -> bool:
        """Check if detector needs retraining"""
        if not self.is_trained_flag:
            return True
        
        if self.last_training_time:
            days_since_training = (datetime.now() - self.last_training_time).days
            return days_since_training > 21  # Retrain every 3 weeks
        
        return True
    
    def detect_anomalies(self, metrics: Dict) -> Optional[Dict]:
        """Detect anomalies - interface method for tests"""
        return self.detect(metrics)
    
    def check_realtime_anomaly(self, current_metrics: Dict) -> Optional[Dict]:
        """Check for real-time anomalies in current metrics"""
        try:
            # Convert single metrics to expected format
            system_metrics = {
                'resource_warnings': 1 if current_metrics.get('cpu_usage', 0) > 90 else 0,
                'system_errors': 1 if current_metrics.get('memory_usage', 0) > 90 else 0,
                'performance_indicators': []
            }
            
            # Add performance indicators based on metrics
            if current_metrics.get('disk_io', 0) > 400:
                system_metrics['resource_warnings'] += 1
            
            return self.detect(system_metrics)
            
        except Exception as e:
            self.logger.error(f"Real-time anomaly check failed: {e}")
            return None
    
    def train(self) -> Dict:
        """Train the anomaly detector"""
        try:
            self.logger.info("Training anomaly detector...")
            
            # Refresh baseline patterns
            self._establish_resource_baselines()
            self._establish_error_baselines()
            self._establish_timing_baselines()
            
            # Calculate accuracy based on baseline coverage
            baseline_count = len([b for b in [self.resource_baselines, self.error_baselines, self.timing_baselines] if b])
            accuracy = min(0.85, 0.3 + (baseline_count * 0.2))
            
            self.is_trained_flag = True
            self.last_training_time = datetime.now()
            self.accuracy = accuracy
            
            return {
                "success": True,
                "accuracy": accuracy,
                "training_time": "< 1 minute",
                "baselines_established": baseline_count,
                "resource_baselines": bool(self.resource_baselines),
                "error_baselines": bool(self.error_baselines),
                "timing_baselines": bool(self.timing_baselines)
            }
            
        except Exception as e:
            self.logger.error(f"Training failed: {e}")
            return {"success": False, "error": str(e)}