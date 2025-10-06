"""
Training Data Pipeline for ML Models

Prepares and processes build data for machine learning model training.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
try:
    import numpy as np
except ImportError:
    # Graceful fallback if NumPy not available
    class MockNumPy:
        @staticmethod
        def median(data):
            sorted_data = sorted(data)
            n = len(sorted_data)
            if n % 2 == 0:
                return (sorted_data[n//2-1] + sorted_data[n//2]) / 2
            return sorted_data[n//2]
        
        @staticmethod
        def var(data):
            if not data:
                return 0.0
            mean = sum(data) / len(data)
            return sum((x - mean) ** 2 for x in data) / len(data)
    
    np = MockNumPy()


class TrainingDataPipeline:
    """Prepares training data from build database for ML models"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
    
    def prepare_failure_prediction_data(self, lookback_days: int = 30) -> Tuple[List[Dict], List[int]]:
        """Prepare data for failure prediction model"""
        try:
            # Get builds with features and outcomes
            builds = self.db.execute_query("""
                SELECT b.build_id, b.status, b.duration_seconds, b.config_name,
                       COUNT(bs.stage_name) as total_stages,
                       SUM(CASE WHEN bs.status = 'completed' THEN 1 ELSE 0 END) as completed_stages,
                       AVG(bs.duration_seconds) as avg_stage_duration,
                       MAX(bs.stage_order) as max_stage_order
                FROM builds b
                LEFT JOIN build_stages bs ON b.build_id = bs.build_id
                WHERE b.start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY b.build_id
                HAVING total_stages > 0
            """, (lookback_days,), fetch=True)
            
            if not builds or len(builds) < 5:
                return [], []
            
            features = []
            labels = []
            
            for build in builds:
                # Extract features
                feature_dict = {
                    'duration_seconds': build.get('duration_seconds', 0) or 0,
                    'total_stages': build.get('total_stages', 0),
                    'completed_stages': build.get('completed_stages', 0),
                    'completion_ratio': (build.get('completed_stages', 0) / max(build.get('total_stages', 1), 1)),
                    'avg_stage_duration': build.get('avg_stage_duration', 0) or 0,
                    'max_stage_order': build.get('max_stage_order', 0) or 0
                }
                
                # Add stage-specific failure history
                stage_failures = self._get_stage_failure_features(build['build_id'])
                feature_dict.update(stage_failures)
                
                features.append(feature_dict)
                
                # Label: 1 for failure, 0 for success
                labels.append(1 if build['status'] == 'failed' else 0)
            
            return features, labels
            
        except Exception as e:
            self.logger.error(f"Failed to prepare failure prediction data: {e}")
            return [], []
    
    def prepare_performance_optimization_data(self, lookback_days: int = 30) -> Tuple[List[Dict], List[float]]:
        """Prepare data for performance optimization model"""
        try:
            # Get successful builds with timing data
            builds = self.db.execute_query("""
                SELECT b.build_id, b.duration_seconds, b.config_name,
                       COUNT(bs.stage_name) as total_stages,
                       AVG(bs.duration_seconds) as avg_stage_duration,
                       MIN(bs.duration_seconds) as min_stage_duration,
                       MAX(bs.duration_seconds) as max_stage_duration
                FROM builds b
                LEFT JOIN build_stages bs ON b.build_id = bs.build_id
                WHERE b.start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                  AND b.status = 'success'
                  AND b.duration_seconds IS NOT NULL
                GROUP BY b.build_id
                HAVING total_stages > 0
            """, (lookback_days,), fetch=True)
            
            if not builds or len(builds) < 3:
                return [], []
            
            features = []
            performance_scores = []
            
            # Calculate performance baseline
            durations = [b['duration_seconds'] for b in builds if b['duration_seconds']]
            if not durations:
                return [], []
            
            median_duration = np.median(durations)
            
            for build in builds:
                # Extract configuration features
                feature_dict = {
                    'total_stages': build.get('total_stages', 0),
                    'avg_stage_duration': build.get('avg_stage_duration', 0) or 0,
                    'min_stage_duration': build.get('min_stage_duration', 0) or 0,
                    'max_stage_duration': build.get('max_stage_duration', 0) or 0,
                    'stage_duration_variance': self._calculate_stage_variance(build['build_id'])
                }
                
                features.append(feature_dict)
                
                # Performance score: lower duration = higher score
                duration = build['duration_seconds']
                performance_score = max(0, 1 - (duration / (median_duration * 2)))
                performance_scores.append(performance_score)
            
            return features, performance_scores
            
        except Exception as e:
            self.logger.error(f"Failed to prepare performance optimization data: {e}")
            return [], []
    
    def prepare_anomaly_detection_data(self, lookback_days: int = 30) -> List[Dict]:
        """Prepare data for anomaly detection model (unsupervised)"""
        try:
            # Get successful builds as baseline
            builds = self.db.execute_query("""
                SELECT b.build_id, b.duration_seconds,
                       COUNT(bs.stage_name) as total_stages,
                       AVG(bs.duration_seconds) as avg_stage_duration,
                       STDDEV(bs.duration_seconds) as stage_duration_stddev
                FROM builds b
                LEFT JOIN build_stages bs ON b.build_id = bs.build_id
                WHERE b.start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                  AND b.status = 'success'
                GROUP BY b.build_id
                HAVING total_stages > 0
            """, (lookback_days,), fetch=True)
            
            if not builds or len(builds) < 10:
                return []
            
            baseline_features = []
            
            for build in builds:
                feature_dict = {
                    'build_duration': build.get('duration_seconds', 0) or 0,
                    'total_stages': build.get('total_stages', 0),
                    'avg_stage_duration': build.get('avg_stage_duration', 0) or 0,
                    'stage_duration_stddev': build.get('stage_duration_stddev', 0) or 0,
                    'stage_failure_rate': self._get_historical_failure_rate(build['build_id'])
                }
                
                baseline_features.append(feature_dict)
            
            return baseline_features
            
        except Exception as e:
            self.logger.error(f"Failed to prepare anomaly detection data: {e}")
            return []
    
    def _get_stage_failure_features(self, build_id: str) -> Dict:
        """Get stage-specific failure features for a build"""
        try:
            # Get stage failure counts for common stages
            stage_data = self.db.execute_query("""
                SELECT stage_name, status
                FROM build_stages
                WHERE build_id = %s
            """, (build_id,), fetch=True)
            
            features = {}
            common_stages = ['prepare_host', 'download_sources', 'build_toolchain', 
                           'build_temp_system', 'enter_chroot', 'build_final_system']
            
            for stage in common_stages:
                stage_status = next((s['status'] for s in stage_data if s['stage_name'] == stage), None)
                features[f'{stage}_failed'] = 1 if stage_status == 'failed' else 0
            
            return features
            
        except Exception as e:
            return {}
    
    def _calculate_stage_variance(self, build_id: str) -> float:
        """Calculate variance in stage durations for a build"""
        try:
            durations = self.db.execute_query("""
                SELECT duration_seconds
                FROM build_stages
                WHERE build_id = %s AND duration_seconds IS NOT NULL
            """, (build_id,), fetch=True)
            
            if not durations or len(durations) < 2:
                return 0.0
            
            duration_values = [d['duration_seconds'] for d in durations]
            return float(np.var(duration_values))
            
        except Exception as e:
            return 0.0
    
    def _get_historical_failure_rate(self, build_id: str) -> float:
        """Get historical failure rate for builds similar to this one"""
        try:
            # Get failure rate for builds with similar configuration
            build_config = self.db.execute_query("""
                SELECT config_name FROM builds WHERE build_id = %s
            """, (build_id,), fetch=True)
            
            if not build_config:
                return 0.0
            
            config_name = build_config[0]['config_name']
            
            # Calculate failure rate for this configuration
            stats = self.db.execute_query("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failures
                FROM builds
                WHERE config_name = %s
                  AND start_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            """, (config_name,), fetch=True)
            
            if stats and stats[0]['total'] > 0:
                return float(stats[0]['failures']) / float(stats[0]['total'])
            
            return 0.0
            
        except Exception as e:
            return 0.0
    
    def validate_training_data(self, features: List[Dict], labels: List) -> bool:
        """Validate that training data is suitable for ML"""
        if not features or not labels:
            return False
        
        if len(features) != len(labels):
            return False
        
        if len(features) < 5:  # Minimum samples needed
            return False
        
        # Check for feature completeness
        if not all(isinstance(f, dict) and len(f) > 0 for f in features):
            return False
        
        return True