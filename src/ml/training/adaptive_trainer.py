"""
Adaptive ML Model Trainer
Continuously adapts and retrains models based on new data and performance
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import json

class AdaptiveTrainer:
    """Adaptive trainer for continuous model improvement"""
    
    def __init__(self, ml_engine, db_manager):
        self.ml_engine = ml_engine
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        
        self.training_active = False
        self.training_thread = None
        self.training_schedule = {
            'failure_predictor': {'interval_hours': 24, 'last_trained': None},
            'performance_optimizer': {'interval_hours': 48, 'last_trained': None},
            'anomaly_detector': {'interval_hours': 72, 'last_trained': None}
        }
        
        self.performance_metrics = {}
    
    def start_adaptive_training(self):
        """Start adaptive training process"""
        if self.training_active:
            return
            
        self.training_active = True
        self.training_thread = threading.Thread(target=self._training_loop, daemon=True)
        self.training_thread.start()
        self.logger.info("Adaptive training started")
    
    def stop_adaptive_training(self):
        """Stop adaptive training process"""
        self.training_active = False
        if self.training_thread:
            self.training_thread.join(timeout=10)
        self.logger.info("Adaptive training stopped")
    
    def trigger_immediate_training(self, model_name: str = None) -> Dict:
        """Trigger immediate training for specific model or all models"""
        try:
            results = {}
            
            if model_name:
                if model_name in self.training_schedule:
                    result = self._train_model(model_name)
                    results[model_name] = result
                else:
                    results['error'] = f"Unknown model: {model_name}"
            else:
                # Train all models
                for model in self.training_schedule.keys():
                    result = self._train_model(model)
                    results[model] = result
            
            return results
            
        except Exception as e:
            self.logger.error(f"Immediate training failed: {e}")
            return {'error': str(e)}
    
    def _training_loop(self):
        """Main adaptive training loop"""
        while self.training_active:
            try:
                current_time = datetime.now()
                
                # Check each model for training needs
                for model_name, schedule in self.training_schedule.items():
                    if self._should_train_model(model_name, current_time):
                        self.logger.info(f"Starting adaptive training for {model_name}")
                        result = self._train_model(model_name)
                        
                        if result.get('success'):
                            schedule['last_trained'] = current_time
                            self.logger.info(f"Adaptive training completed for {model_name}")
                        else:
                            self.logger.error(f"Adaptive training failed for {model_name}: {result.get('error')}")
                
                # Sleep before next check
                time.sleep(3600)  # Check every hour
                
            except Exception as e:
                self.logger.error(f"Training loop error: {e}")
                time.sleep(1800)  # Sleep 30 minutes on error
    
    def _should_train_model(self, model_name: str, current_time: datetime) -> bool:
        """Determine if model should be retrained"""
        try:
            schedule = self.training_schedule[model_name]
            
            # Check time-based schedule
            if schedule['last_trained'] is None:
                return True  # Never trained
            
            time_since_training = current_time - schedule['last_trained']
            if time_since_training.total_seconds() >= schedule['interval_hours'] * 3600:
                return True  # Time for scheduled retraining
            
            # Check performance-based triggers
            if self._performance_degraded(model_name):
                self.logger.info(f"Performance degradation detected for {model_name}")
                return True
            
            # Check data availability
            if self._sufficient_new_data(model_name):
                self.logger.info(f"Sufficient new data available for {model_name}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Training decision error for {model_name}: {e}")
            return False
    
    def _performance_degraded(self, model_name: str) -> bool:
        """Check if model performance has degraded"""
        try:
            # Get recent prediction accuracy
            recent_accuracy = self._get_recent_accuracy(model_name)
            
            if recent_accuracy is None:
                return False
            
            # Get baseline accuracy
            baseline_accuracy = self.performance_metrics.get(f'{model_name}_baseline', 0.7)
            
            # Trigger retraining if accuracy dropped significantly
            degradation_threshold = 0.1
            return recent_accuracy < (baseline_accuracy - degradation_threshold)
            
        except Exception as e:
            self.logger.error(f"Performance check error for {model_name}: {e}")
            return False
    
    def _get_recent_accuracy(self, model_name: str) -> Optional[float]:
        """Get recent prediction accuracy for model"""
        try:
            # Get recent predictions and outcomes
            predictions = self.db.execute_query("""
                SELECT bd1.content as prediction, bd2.content as outcome
                FROM build_documents bd1
                JOIN build_documents bd2 ON bd1.build_id = bd2.build_id
                WHERE bd1.document_type = 'ml_prediction'
                  AND bd2.document_type = 'build_outcome'
                  AND bd1.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                  AND bd1.content LIKE %s
                LIMIT 20
            """, (f'%{model_name}%',), fetch=True)
            
            if not predictions or len(predictions) < 5:
                return None
            
            # Calculate accuracy
            correct_predictions = 0
            total_predictions = len(predictions)
            
            for pred_data in predictions:
                try:
                    prediction = json.loads(pred_data['prediction'])
                    outcome = json.loads(pred_data['outcome'])
                    
                    # Simple accuracy calculation
                    predicted_success = prediction.get('failure_risk', 0.5) < 0.5
                    actual_success = outcome.get('status') == 'success'
                    
                    if predicted_success == actual_success:
                        correct_predictions += 1
                        
                except (json.JSONDecodeError, KeyError):
                    continue
            
            return correct_predictions / total_predictions if total_predictions > 0 else None
            
        except Exception as e:
            self.logger.error(f"Accuracy calculation error: {e}")
            return None
    
    def _sufficient_new_data(self, model_name: str) -> bool:
        """Check if sufficient new training data is available"""
        try:
            # Get count of new builds since last training
            last_trained = self.training_schedule[model_name]['last_trained']
            
            if last_trained is None:
                cutoff_time = datetime.now() - timedelta(days=7)
            else:
                cutoff_time = last_trained
            
            new_builds = self.db.execute_query("""
                SELECT COUNT(*) as count FROM builds
                WHERE start_time >= %s AND status IN ('success', 'failed')
            """, (cutoff_time,), fetch=True)
            
            count = new_builds[0]['count'] if new_builds else 0
            
            # Minimum new samples needed for retraining
            min_samples = {'failure_predictor': 10, 'performance_optimizer': 5, 'anomaly_detector': 20}
            threshold = min_samples.get(model_name, 10)
            
            return count >= threshold
            
        except Exception as e:
            self.logger.error(f"New data check error: {e}")
            return False
    
    def _train_model(self, model_name: str) -> Dict:
        """Train specific model with latest data"""
        try:
            self.logger.info(f"Starting training for {model_name}")
            
            # Get training data pipeline
            if not hasattr(self.ml_engine, 'data_pipeline'):
                return {'success': False, 'error': 'Data pipeline not available'}
            
            data_pipeline = self.ml_engine.data_pipeline
            
            # Prepare training data based on model type
            if model_name == 'failure_predictor':
                features, labels = data_pipeline.prepare_failure_prediction_data()
                if not data_pipeline.validate_training_data(features, labels):
                    return {'success': False, 'error': 'Insufficient training data'}
                
                # Train failure predictor
                if hasattr(self.ml_engine, 'failure_predictor'):
                    training_result = self._train_failure_predictor(features, labels)
                else:
                    return {'success': False, 'error': 'Failure predictor not available'}
            
            elif model_name == 'performance_optimizer':
                features, scores = data_pipeline.prepare_performance_optimization_data()
                if not data_pipeline.validate_training_data(features, scores):
                    return {'success': False, 'error': 'Insufficient training data'}
                
                # Train performance optimizer
                if hasattr(self.ml_engine, 'performance_optimizer'):
                    training_result = self._train_performance_optimizer(features, scores)
                else:
                    return {'success': False, 'error': 'Performance optimizer not available'}
            
            elif model_name == 'anomaly_detector':
                baseline_data = data_pipeline.prepare_anomaly_detection_data()
                if len(baseline_data) < 10:
                    return {'success': False, 'error': 'Insufficient baseline data'}
                
                # Train anomaly detector
                if hasattr(self.ml_engine, 'anomaly_detector'):
                    training_result = self._train_anomaly_detector(baseline_data)
                else:
                    return {'success': False, 'error': 'Anomaly detector not available'}
            
            else:
                return {'success': False, 'error': f'Unknown model: {model_name}'}
            
            # Store training results
            self._store_training_results(model_name, training_result)
            
            # Update performance baseline
            if training_result.get('success'):
                self._update_performance_baseline(model_name, training_result)
            
            return training_result
            
        except Exception as e:
            self.logger.error(f"Model training failed for {model_name}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _train_failure_predictor(self, features: List[Dict], labels: List[int]) -> Dict:
        """Train failure prediction model"""
        try:
            # Simple training simulation (would use actual ML library in production)
            training_accuracy = self._simulate_training_accuracy(features, labels)
            
            return {
                'success': True,
                'model': 'failure_predictor',
                'training_samples': len(features),
                'training_accuracy': training_accuracy,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _train_performance_optimizer(self, features: List[Dict], scores: List[float]) -> Dict:
        """Train performance optimization model"""
        try:
            training_accuracy = self._simulate_training_accuracy(features, scores)
            
            return {
                'success': True,
                'model': 'performance_optimizer',
                'training_samples': len(features),
                'training_accuracy': training_accuracy,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _train_anomaly_detector(self, baseline_data: List[Dict]) -> Dict:
        """Train anomaly detection model"""
        try:
            # Calculate baseline statistics
            if not baseline_data:
                return {'success': False, 'error': 'No baseline data'}
            
            return {
                'success': True,
                'model': 'anomaly_detector',
                'baseline_samples': len(baseline_data),
                'training_accuracy': 0.85,  # Simulated
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _simulate_training_accuracy(self, features: List, labels: List) -> float:
        """Simulate training accuracy (replace with actual ML training)"""
        if not features or not labels:
            return 0.0
        
        # Simulate accuracy based on data quality
        base_accuracy = 0.7
        data_quality_bonus = min(0.2, len(features) / 100.0)
        
        return min(0.95, base_accuracy + data_quality_bonus)
    
    def _store_training_results(self, model_name: str, results: Dict):
        """Store training results in database"""
        try:
            # Ensure system build exists for ML training documents
            system_build_id = 'ml_system_training'
            
            # Check if system build exists, create if not
            existing = self.db.execute_query(
                "SELECT build_id FROM builds WHERE build_id = %s", 
                (system_build_id,), fetch=True
            )
            
            if not existing:
                # Create system build record
                self.db.execute_query("""
                    INSERT INTO builds (build_id, config_name, status, total_stages, completed_stages, start_time)
                    VALUES (%s, 'ML System Training', 'running', 1, 0, NOW())
                """, (system_build_id,))
            
            # Store training results as document
            self.db.execute_query("""
                INSERT INTO build_documents (build_id, document_type, title, content, created_at)
                VALUES (%s, 'ml_train', %s, %s, NOW())
            """, (
                system_build_id,
                f'Adaptive Training - {model_name}',
                json.dumps(results, default=str)
            ))
            
        except Exception as e:
            self.logger.error(f"Failed to store training results: {e}")
    
    def _update_performance_baseline(self, model_name: str, results: Dict):
        """Update performance baseline for model"""
        try:
            accuracy = results.get('training_accuracy', 0.0)
            self.performance_metrics[f'{model_name}_baseline'] = accuracy
            self.logger.info(f"Updated baseline for {model_name}: {accuracy:.3f}")
            
        except Exception as e:
            self.logger.error(f"Failed to update baseline: {e}")
    
    def get_training_status(self) -> Dict:
        """Get current training status"""
        return {
            'training_active': self.training_active,
            'training_schedule': {
                name: {
                    'interval_hours': schedule['interval_hours'],
                    'last_trained': schedule['last_trained'].isoformat() if schedule['last_trained'] else None,
                    'next_training': self._calculate_next_training(name)
                }
                for name, schedule in self.training_schedule.items()
            },
            'performance_metrics': self.performance_metrics.copy(),
            'last_update': datetime.now().isoformat()
        }
    
    def _calculate_next_training(self, model_name: str) -> Optional[str]:
        """Calculate next scheduled training time"""
        try:
            schedule = self.training_schedule[model_name]
            if schedule['last_trained'] is None:
                return "Immediate"
            
            next_time = schedule['last_trained'] + timedelta(hours=schedule['interval_hours'])
            return next_time.isoformat()
            
        except Exception:
            return None