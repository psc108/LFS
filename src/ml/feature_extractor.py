"""
Feature Extractor for LFS Build System

Extracts meaningful features from build data stored in MySQL database
for machine learning model training and prediction.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json


class FeatureExtractor:
    """Extracts features from build database for ML models"""
    
    def __init__(self, db_manager):
        """Initialize with database connection"""
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
    
    def extract_build_features(self, build_id: Optional[str] = None) -> Dict:
        """Extract comprehensive features for builds"""
        try:
            if build_id:
                # Extract features for specific build
                features = self._extract_single_build_features(build_id)
                return features if features else {}
            else:
                # Extract features for recent builds
                recent_features = self._extract_recent_build_features()
                return {"recent_builds": recent_features} if recent_features else {}
                
        except Exception as e:
            self.logger.error(f"Feature extraction failed: {e}")
            return {}
    
    def _extract_single_build_features(self, build_id: str) -> Optional[Dict]:
        """Extract comprehensive features for a specific build"""
        try:
            features = {}
            
            # Basic build information
            build_info = self._get_build_info(build_id)
            if not build_info:
                return None
            
            features["build_info"] = build_info
            
            # Stage timing features
            stage_features = self._extract_stage_features(build_id)
            if stage_features:
                features["stages"] = stage_features
            
            # System metrics features
            system_features = self._extract_system_features(build_id)
            if system_features:
                features["system_metrics"] = system_features
            
            # Historical context features
            historical_features = self._extract_historical_features(build_info.get("config_name"))
            if historical_features:
                features["historical_context"] = historical_features
            
            # Error pattern features
            error_features = self._extract_error_features(build_id)
            if error_features:
                features["error_patterns"] = error_features
            
            return features
            
        except Exception as e:
            self.logger.error(f"Feature extraction failed for build {build_id}: {e}")
            return None
    
    def _get_build_info(self, build_id: str) -> Optional[Dict]:
        """Get basic build information"""
        try:
            builds = self.db.execute_query(
                "SELECT build_id, config_name, status, start_time, end_time, duration_seconds FROM builds WHERE build_id = %s",
                (build_id,), fetch=True
            )
            
            if not builds:
                return None
            
            build = builds[0]
            return {
                "build_id": build["build_id"],
                "config_name": build.get("config_name"),
                "status": build["status"],
                "start_time": build.get("start_time"),
                "end_time": build.get("end_time"),
                "duration_seconds": build.get("duration_seconds", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get build info for {build_id}: {e}")
            return None
    
    def _extract_stage_features(self, build_id: str) -> Optional[Dict]:
        """Extract stage timing and sequence features"""
        try:
            stages = self.db.execute_query(
                """SELECT stage_name, status, stage_order, start_time, end_time, 
                   TIMESTAMPDIFF(SECOND, start_time, end_time) as duration_seconds,
                   error_message FROM build_stages 
                   WHERE build_id = %s ORDER BY stage_order""",
                (build_id,), fetch=True
            )
            
            if not stages:
                return None
            
            stage_features = {
                "total_stages": len(stages),
                "completed_stages": len([s for s in stages if s["status"] == "completed"]),
                "failed_stages": len([s for s in stages if s["status"] == "failed"]),
                "stage_durations": [],
                "stage_sequence": [],
                "failure_points": []
            }
            
            for stage in stages:
                stage_features["stage_sequence"].append({
                    "name": stage["stage_name"],
                    "order": stage["stage_order"],
                    "status": stage["status"],
                    "duration": stage.get("duration_seconds", 0)
                })
                
                if stage.get("duration_seconds"):
                    stage_features["stage_durations"].append(stage["duration_seconds"])
                
                if stage["status"] == "failed":
                    stage_features["failure_points"].append({
                        "stage": stage["stage_name"],
                        "order": stage["stage_order"],
                        "error": stage.get("error_message", "")
                    })
            
            # Calculate timing statistics
            if stage_features["stage_durations"]:
                durations = stage_features["stage_durations"]
                stage_features["avg_stage_duration"] = sum(durations) / len(durations)
                stage_features["max_stage_duration"] = max(durations)
                stage_features["min_stage_duration"] = min(durations)
            
            return stage_features
            
        except Exception as e:
            self.logger.error(f"Failed to extract stage features for {build_id}: {e}")
            return None
    
    def _extract_system_features(self, build_id: str) -> Optional[Dict]:
        """Extract system resource and performance features"""
        try:
            # Get system-related documents
            docs = self.db.execute_query(
                """SELECT content FROM build_documents 
                   WHERE build_id = %s AND document_type = 'log' 
                   AND (title LIKE '%system%' OR title LIKE '%resource%' OR content LIKE '%CPU%' OR content LIKE '%memory%')
                   ORDER BY created_at""",
                (build_id,), fetch=True
            )
            
            system_features = {
                "resource_warnings": 0,
                "performance_indicators": [],
                "system_errors": 0
            }
            
            for doc in docs:
                content = doc.get("content", "").lower()
                
                # Count resource warnings
                if any(keyword in content for keyword in ["high cpu", "memory", "disk space", "load average"]):
                    system_features["resource_warnings"] += 1
                
                # Count system errors
                if any(keyword in content for keyword in ["system error", "kernel", "hardware"]):
                    system_features["system_errors"] += 1
                
                # Extract performance indicators
                if "compilation" in content or "make -j" in content:
                    system_features["performance_indicators"].append("parallel_compilation")
            
            return system_features if any(system_features.values()) else None
            
        except Exception as e:
            self.logger.error(f"Failed to extract system features for {build_id}: {e}")
            return None
    
    def _extract_historical_features(self, config_name: str) -> Optional[Dict]:
        """Extract historical context features for similar builds"""
        try:
            if not config_name:
                return None
            
            # Get recent builds with same configuration
            recent_builds = self.db.execute_query(
                """SELECT status, duration_seconds FROM builds 
                   WHERE config_name = %s AND start_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                   ORDER BY start_time DESC LIMIT 20""",
                (config_name,), fetch=True
            )
            
            if not recent_builds:
                return None
            
            historical_features = {
                "recent_build_count": len(recent_builds),
                "success_rate": 0,
                "avg_duration": 0,
                "duration_trend": "stable"
            }
            
            # Calculate success rate
            successful = len([b for b in recent_builds if b["status"] == "success"])
            historical_features["success_rate"] = successful / len(recent_builds) if recent_builds else 0
            
            # Calculate average duration
            durations = [b["duration_seconds"] for b in recent_builds if b.get("duration_seconds")]
            if durations:
                historical_features["avg_duration"] = sum(durations) / len(durations)
                
                # Determine duration trend
                if len(durations) >= 3:
                    recent_avg = sum(durations[:3]) / 3
                    older_avg = sum(durations[3:6]) / min(3, len(durations[3:6])) if len(durations) > 3 else recent_avg
                    
                    if recent_avg > older_avg * 1.1:
                        historical_features["duration_trend"] = "increasing"
                    elif recent_avg < older_avg * 0.9:
                        historical_features["duration_trend"] = "decreasing"
            
            return historical_features
            
        except Exception as e:
            self.logger.error(f"Failed to extract historical features for {config_name}: {e}")
            return None
    
    def _extract_error_features(self, build_id: str) -> Optional[Dict]:
        """Extract error pattern features"""
        try:
            # Get error documents
            error_docs = self.db.execute_query(
                """SELECT content FROM build_documents 
                   WHERE build_id = %s AND (document_type = 'error' OR content LIKE '%error%' OR content LIKE '%failed%')
                   ORDER BY created_at""",
                (build_id,), fetch=True
            )
            
            if not error_docs:
                return None
            
            error_features = {
                "error_count": len(error_docs),
                "error_types": [],
                "common_errors": []
            }
            
            # Analyze error patterns
            for doc in error_docs:
                content = doc.get("content", "").lower()
                
                # Categorize error types
                if "compilation" in content or "gcc" in content:
                    error_features["error_types"].append("compilation")
                elif "permission" in content or "access denied" in content:
                    error_features["error_types"].append("permission")
                elif "network" in content or "download" in content:
                    error_features["error_types"].append("network")
                elif "disk" in content or "space" in content:
                    error_features["error_types"].append("disk_space")
                else:
                    error_features["error_types"].append("other")
                
                # Extract common error patterns
                if "make: *** [" in content:
                    error_features["common_errors"].append("make_error")
                if "configure: error:" in content:
                    error_features["common_errors"].append("configure_error")
                if "no such file" in content:
                    error_features["common_errors"].append("missing_file")
            
            # Remove duplicates
            error_features["error_types"] = list(set(error_features["error_types"]))
            error_features["common_errors"] = list(set(error_features["common_errors"]))
            
            return error_features
            
        except Exception as e:
            self.logger.error(f"Failed to extract error features for {build_id}: {e}")
            return None
    
    def extract_training_dataset(self, limit: int = 1000) -> List[Dict]:
        """Extract features for multiple builds to create training dataset"""
        try:
            # Get recent builds for training
            builds = self.db.execute_query(
                """SELECT build_id FROM builds 
                   WHERE start_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                   ORDER BY start_time DESC LIMIT %s""",
                (limit,), fetch=True
            )
            
            training_data = []
            
            for build in builds:
                build_id = build["build_id"]
                features = self.extract_build_features(build_id)
                
                if features:
                    training_data.append(features)
                
                # Log progress every 100 builds
                if len(training_data) % 100 == 0:
                    self.logger.info(f"Extracted features for {len(training_data)} builds")
            
            self.logger.info(f"Training dataset created with {len(training_data)} samples")
            return training_data
            
        except Exception as e:
            self.logger.error(f"Failed to extract training dataset: {e}")
            return []
    
    def _extract_recent_build_features(self) -> List[Dict]:
        """Extract features for recent builds"""
        try:
            # Get recent builds
            builds = self.db.execute_query(
                """SELECT build_id FROM builds 
                   WHERE start_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                   ORDER BY start_time DESC LIMIT 50""",
                fetch=True
            )
            
            features_list = []
            for build in builds:
                build_id = build["build_id"]
                features = self._extract_single_build_features(build_id)
                if features:
                    features_list.append(features)
            
            return features_list
            
        except Exception as e:
            self.logger.error(f"Failed to extract recent build features: {e}")
            return []
    
    def extract_system_features(self) -> Dict:
        """Extract current system-level features"""
        try:
            # Get system statistics from recent builds
            system_stats = self.db.execute_query(
                """SELECT COUNT(*) as total_builds,
                   SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_builds,
                   AVG(duration_seconds) as avg_duration
                   FROM builds 
                   WHERE start_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                   AND duration_seconds IS NOT NULL""",
                fetch=True
            )
            
            features = {
                "total_builds_week": 0,
                "success_rate_week": 0.0,
                "avg_build_duration": 0.0,
                "system_health": "unknown"
            }
            
            if system_stats and system_stats[0]["total_builds"]:
                stat = system_stats[0]
                features["total_builds_week"] = stat["total_builds"]
                features["success_rate_week"] = stat["successful_builds"] / stat["total_builds"]
                features["avg_build_duration"] = stat.get("avg_duration", 0) or 0
                
                # Determine system health
                if features["success_rate_week"] > 0.8:
                    features["system_health"] = "good"
                elif features["success_rate_week"] > 0.6:
                    features["system_health"] = "fair"
                else:
                    features["system_health"] = "poor"
            
            return features
            
        except Exception as e:
            self.logger.error(f"Failed to extract system features: {e}")
            return {"system_health": "error", "error": str(e)}