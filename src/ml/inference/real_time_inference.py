"""
Real-time ML Inference Engine
Production inference system for live build monitoring and prediction
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import json

class RealTimeInferenceEngine:
    """Real-time inference engine for live ML predictions"""
    
    def __init__(self, ml_engine, db_manager):
        self.ml_engine = ml_engine
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        
        self.inference_active = False
        self.inference_thread = None
        self.prediction_cache = {}
        self.active_builds = {}
        
    def start_inference_monitoring(self):
        """Start real-time inference monitoring"""
        if self.inference_active:
            return
            
        self.inference_active = True
        self.inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self.inference_thread.start()
        self.logger.info("Real-time inference monitoring started")
    
    def stop_inference_monitoring(self):
        """Stop real-time inference monitoring"""
        self.inference_active = False
        if self.inference_thread:
            self.inference_thread.join(timeout=5)
        self.logger.info("Real-time inference monitoring stopped")
    
    def predict_build_outcome(self, build_id: str, current_stage: str = None) -> Dict:
        """Predict build outcome in real-time"""
        try:
            # Check cache first
            cache_key = f"{build_id}_{current_stage}"
            if cache_key in self.prediction_cache:
                cached = self.prediction_cache[cache_key]
                if (datetime.now() - cached['timestamp']).seconds < 300:  # 5 min cache
                    return cached['prediction']
            
            # Extract real-time features
            features = self._extract_realtime_features(build_id, current_stage)
            
            # Get predictions from all models
            predictions = {}
            
            # Failure prediction
            if hasattr(self.ml_engine, 'failure_predictor'):
                failure_risk = self.ml_engine.failure_predictor.predict_failure_risk(features)
                predictions['failure_risk'] = failure_risk
            
            # Performance prediction
            if hasattr(self.ml_engine, 'performance_optimizer'):
                perf_recommendations = self.ml_engine.performance_optimizer.get_recommendations(features)
                predictions['performance_recommendations'] = perf_recommendations
            
            # Anomaly detection
            if hasattr(self.ml_engine, 'anomaly_detector'):
                anomaly_score = self.ml_engine.anomaly_detector.check_realtime_anomaly(features)
                predictions['anomaly_detected'] = anomaly_score
            
            # Advanced prediction if available
            if hasattr(self.ml_engine, 'advanced_predictor'):
                advanced_pred = self.ml_engine.advanced_predictor.predict_with_confidence(features)
                predictions['advanced_prediction'] = advanced_pred
            
            # Combine predictions
            combined_prediction = self._combine_predictions(predictions)
            
            # Cache result
            self.prediction_cache[cache_key] = {
                'timestamp': datetime.now(),
                'prediction': combined_prediction
            }
            
            # Store prediction in database
            self._store_prediction(build_id, current_stage, combined_prediction)
            
            return combined_prediction
            
        except Exception as e:
            self.logger.error(f"Real-time prediction failed for {build_id}: {e}")
            return {'error': str(e), 'failure_risk': 0.5}
    
    def _extract_realtime_features(self, build_id: str, current_stage: str = None) -> Dict:
        """Extract features for real-time prediction"""
        try:
            # Get current build data
            build_data = self.db.execute_query("""
                SELECT b.*, COUNT(bs.stage_name) as completed_stages,
                       AVG(bs.duration_seconds) as avg_stage_duration
                FROM builds b
                LEFT JOIN build_stages bs ON b.build_id = bs.build_id AND bs.status = 'completed'
                WHERE b.build_id = %s
                GROUP BY b.build_id
            """, (build_id,), fetch=True)
            
            if not build_data:
                return {}
            
            build = build_data[0]
            
            # Calculate elapsed time
            start_time = build.get('start_time')
            if start_time:
                elapsed_seconds = (datetime.now() - start_time).total_seconds()
            else:
                elapsed_seconds = 0
            
            features = {
                'build_id': build_id,
                'elapsed_time': elapsed_seconds,
                'completed_stages': build.get('completed_stages', 0),
                'avg_stage_duration': build.get('avg_stage_duration', 0) or 0,
                'current_stage': current_stage or 'unknown'
            }
            
            # Add stage-specific features
            if current_stage:
                stage_features = self._get_stage_specific_features(build_id, current_stage)
                features.update(stage_features)
            
            # Add system resource features
            resource_features = self._get_system_resource_features()
            features.update(resource_features)
            
            return features
            
        except Exception as e:
            self.logger.error(f"Feature extraction failed: {e}")
            return {}
    
    def _get_stage_specific_features(self, build_id: str, stage_name: str) -> Dict:
        """Get features specific to current stage"""
        try:
            # Get historical data for this stage
            stage_history = self.db.execute_query("""
                SELECT AVG(duration_seconds) as avg_duration,
                       COUNT(*) as total_runs,
                       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failures
                FROM build_stages
                WHERE stage_name = %s
                  AND start_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """, (stage_name,), fetch=True)
            
            if stage_history:
                hist = stage_history[0]
                failure_rate = (hist['failures'] / max(hist['total_runs'], 1)) if hist['total_runs'] else 0
                
                return {
                    f'{stage_name}_avg_duration': hist['avg_duration'] or 0,
                    f'{stage_name}_failure_rate': failure_rate,
                    f'{stage_name}_historical_runs': hist['total_runs'] or 0
                }
            
            return {}
            
        except Exception as e:
            return {}
    
    def _get_system_resource_features(self) -> Dict:
        """Get current system resource utilization"""
        try:
            import psutil
            
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'load_average': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
            }
            
        except Exception as e:
            return {'cpu_percent': 0, 'memory_percent': 0, 'disk_percent': 0}
    
    def _combine_predictions(self, predictions: Dict) -> Dict:
        """Combine multiple model predictions into unified result"""
        combined = {
            'timestamp': datetime.now().isoformat(),
            'predictions': predictions
        }
        
        # Calculate overall risk score
        risk_scores = []
        
        if 'failure_risk' in predictions:
            risk_scores.append(predictions['failure_risk'])
        
        if 'anomaly_detected' in predictions and predictions['anomaly_detected']:
            risk_scores.append(0.8)
        
        if 'advanced_prediction' in predictions:
            adv_pred = predictions['advanced_prediction']
            if isinstance(adv_pred, dict) and 'prediction' in adv_pred:
                risk_scores.append(adv_pred['prediction'])
        
        # Overall risk assessment
        if risk_scores:
            combined['overall_risk'] = sum(risk_scores) / len(risk_scores)
            combined['risk_level'] = self._categorize_risk(combined['overall_risk'])
        else:
            combined['overall_risk'] = 0.5
            combined['risk_level'] = 'medium'
        
        # Recommendations
        recommendations = []
        if 'performance_recommendations' in predictions:
            recommendations.extend(predictions['performance_recommendations'])
        
        if combined['overall_risk'] > 0.7:
            recommendations.append("High failure risk detected - consider intervention")
        
        combined['recommendations'] = recommendations
        
        return combined
    
    def _categorize_risk(self, risk_score: float) -> str:
        """Categorize risk score into levels"""
        if risk_score >= 0.8:
            return 'critical'
        elif risk_score >= 0.6:
            return 'high'
        elif risk_score >= 0.4:
            return 'medium'
        else:
            return 'low'
    
    def _store_prediction(self, build_id: str, stage: str, prediction: Dict):
        """Store prediction result in database"""
        try:
            self.db.execute_query("""
                INSERT INTO build_documents (build_id, document_type, title, content, created_at)
                VALUES (%s, 'ml_prediction', %s, %s, NOW())
            """, (
                build_id,
                f'Real-time Prediction - {stage or "General"}',
                json.dumps(prediction, default=str)
            ))
            
        except Exception as e:
            self.logger.error(f"Failed to store prediction: {e}")
    
    def _inference_loop(self):
        """Main inference monitoring loop"""
        while self.inference_active:
            try:
                # Get active builds
                active_builds = self.db.execute_query("""
                    SELECT build_id, status FROM builds
                    WHERE status = 'running'
                      AND start_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                """, fetch=True)
                
                # Run predictions for active builds
                for build in active_builds:
                    build_id = build['build_id']
                    
                    # Get current stage
                    current_stage = self._get_current_stage(build_id)
                    
                    # Run prediction
                    prediction = self.predict_build_outcome(build_id, current_stage)
                    
                    # Check for alerts
                    if prediction.get('overall_risk', 0) > 0.8:
                        self._trigger_alert(build_id, prediction)
                
                # Clean old cache entries
                self._cleanup_cache()
                
                # Sleep before next iteration
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Inference loop error: {e}")
                time.sleep(30)
    
    def _get_current_stage(self, build_id: str) -> Optional[str]:
        """Get current stage for active build"""
        try:
            current_stage = self.db.execute_query("""
                SELECT stage_name FROM build_stages
                WHERE build_id = %s AND status = 'running'
                ORDER BY stage_order DESC
                LIMIT 1
            """, (build_id,), fetch=True)
            
            return current_stage[0]['stage_name'] if current_stage else None
            
        except Exception as e:
            return None
    
    def _trigger_alert(self, build_id: str, prediction: Dict):
        """Trigger alert for high-risk build"""
        try:
            alert_data = {
                'build_id': build_id,
                'risk_level': prediction.get('risk_level', 'unknown'),
                'overall_risk': prediction.get('overall_risk', 0),
                'timestamp': datetime.now().isoformat(),
                'recommendations': prediction.get('recommendations', [])
            }
            
            # Store alert
            self.db.execute_query("""
                INSERT INTO build_documents (build_id, document_type, title, content, created_at)
                VALUES (%s, 'ml_alert', 'High Risk Alert', %s, NOW())
            """, (build_id, json.dumps(alert_data)))
            
            self.logger.warning(f"High risk alert for build {build_id}: {prediction.get('overall_risk', 0):.2f}")
            
        except Exception as e:
            self.logger.error(f"Failed to trigger alert: {e}")
    
    def _cleanup_cache(self):
        """Clean up old cache entries"""
        cutoff = datetime.now() - timedelta(hours=1)
        
        keys_to_remove = [
            key for key, value in self.prediction_cache.items()
            if value['timestamp'] < cutoff
        ]
        
        for key in keys_to_remove:
            del self.prediction_cache[key]
    
    def get_inference_stats(self) -> Dict:
        """Get inference engine statistics"""
        return {
            'inference_active': self.inference_active,
            'cache_size': len(self.prediction_cache),
            'active_builds': len(self.active_builds),
            'last_update': datetime.now().isoformat()
        }