"""
Ensemble ML Predictor
Combines multiple ML models for improved prediction accuracy
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

class EnsemblePredictor:
    """Ensemble predictor combining multiple ML models"""
    
    def __init__(self, ml_engine, db_manager):
        self.ml_engine = ml_engine
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        
        self.model_weights = {
            'failure_predictor': 0.4,
            'performance_optimizer': 0.3,
            'anomaly_detector': 0.2,
            'advanced_predictor': 0.1
        }
        
        self.prediction_history = []
    
    def ensemble_predict(self, features: Dict) -> Dict:
        """Generate ensemble prediction from multiple models"""
        try:
            model_predictions = {}
            model_confidences = {}
            
            # Failure prediction
            if hasattr(self.ml_engine, 'failure_predictor'):
                try:
                    failure_risk = self.ml_engine.failure_predictor.predict_failure_risk(features)
                    model_predictions['failure_predictor'] = failure_risk
                    model_confidences['failure_predictor'] = self._calculate_model_confidence('failure_predictor')
                except Exception as e:
                    self.logger.warning(f"Failure predictor error: {e}")
            
            # Performance optimization
            if hasattr(self.ml_engine, 'performance_optimizer'):
                try:
                    perf_score = self._performance_to_risk_score(features)
                    model_predictions['performance_optimizer'] = perf_score
                    model_confidences['performance_optimizer'] = self._calculate_model_confidence('performance_optimizer')
                except Exception as e:
                    self.logger.warning(f"Performance optimizer error: {e}")
            
            # Anomaly detection
            if hasattr(self.ml_engine, 'anomaly_detector'):
                try:
                    anomaly_detected = self.ml_engine.anomaly_detector.check_realtime_anomaly(features)
                    anomaly_risk = 0.8 if anomaly_detected else 0.2
                    model_predictions['anomaly_detector'] = anomaly_risk
                    model_confidences['anomaly_detector'] = self._calculate_model_confidence('anomaly_detector')
                except Exception as e:
                    self.logger.warning(f"Anomaly detector error: {e}")
            
            # Advanced predictor
            if hasattr(self.ml_engine, 'advanced_predictor'):
                try:
                    advanced_pred = self.ml_engine.advanced_predictor.predict_with_confidence(features)
                    if isinstance(advanced_pred, dict) and 'prediction' in advanced_pred:
                        model_predictions['advanced_predictor'] = advanced_pred['prediction']
                        model_confidences['advanced_predictor'] = self._extract_confidence(advanced_pred)
                except Exception as e:
                    self.logger.warning(f"Advanced predictor error: {e}")
            
            # Calculate weighted ensemble prediction
            ensemble_result = self._calculate_weighted_ensemble(model_predictions, model_confidences)
            
            # Add metadata
            ensemble_result.update({
                'timestamp': datetime.now().isoformat(),
                'model_count': len(model_predictions),
                'individual_predictions': model_predictions,
                'model_confidences': model_confidences
            })
            
            # Store prediction
            self._store_ensemble_prediction(features.get('build_id', 'unknown'), ensemble_result)
            
            return ensemble_result
            
        except Exception as e:
            self.logger.error(f"Ensemble prediction failed: {e}")
            return {
                'ensemble_prediction': 0.5,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _performance_to_risk_score(self, features: Dict) -> float:
        """Convert performance metrics to risk score"""
        try:
            recommendations = self.ml_engine.performance_optimizer.get_recommendations(features)
            
            # More recommendations = higher risk
            if isinstance(recommendations, list):
                risk_score = min(1.0, len(recommendations) * 0.15)
            else:
                risk_score = 0.3
            
            return risk_score
            
        except Exception:
            return 0.5
    
    def _calculate_model_confidence(self, model_name: str) -> float:
        """Calculate confidence for specific model based on historical accuracy"""
        try:
            # Get recent prediction accuracy for this model
            recent_predictions = [p for p in self.prediction_history[-50:] 
                                if model_name in p.get('model_accuracies', {})]
            
            if not recent_predictions:
                return 0.5  # Default confidence
            
            accuracies = [p['model_accuracies'][model_name] for p in recent_predictions]
            return sum(accuracies) / len(accuracies)
            
        except Exception:
            return 0.5
    
    def _extract_confidence(self, advanced_pred: Dict) -> float:
        """Extract confidence from advanced predictor result"""
        try:
            if 'confidence_interval' in advanced_pred:
                ci = advanced_pred['confidence_interval']
                if isinstance(ci, (list, tuple)) and len(ci) == 2:
                    # Narrower confidence interval = higher confidence
                    interval_width = abs(ci[1] - ci[0])
                    return max(0.0, 1.0 - interval_width)
            
            if 'uncertainty_score' in advanced_pred:
                # Lower uncertainty = higher confidence
                return max(0.0, 1.0 - advanced_pred['uncertainty_score'])
            
            return 0.7  # Default for advanced predictor
            
        except Exception:
            return 0.5
    
    def _calculate_weighted_ensemble(self, predictions: Dict, confidences: Dict) -> Dict:
        """Calculate weighted ensemble prediction"""
        try:
            if not predictions:
                return {'ensemble_prediction': 0.5, 'confidence': 0.0}
            
            # Adjust weights based on confidence
            adjusted_weights = {}
            total_weight = 0.0
            
            for model_name, prediction in predictions.items():
                base_weight = self.model_weights.get(model_name, 0.1)
                confidence = confidences.get(model_name, 0.5)
                
                # Boost weight for high-confidence models
                adjusted_weight = base_weight * (0.5 + confidence)
                adjusted_weights[model_name] = adjusted_weight
                total_weight += adjusted_weight
            
            # Normalize weights
            if total_weight > 0:
                for model_name in adjusted_weights:
                    adjusted_weights[model_name] /= total_weight
            
            # Calculate weighted prediction
            ensemble_prediction = 0.0
            for model_name, prediction in predictions.items():
                weight = adjusted_weights.get(model_name, 0.0)
                ensemble_prediction += prediction * weight
            
            # Calculate ensemble confidence
            ensemble_confidence = sum(confidences.values()) / len(confidences) if confidences else 0.0
            
            # Boost confidence if models agree
            prediction_variance = self._calculate_prediction_variance(list(predictions.values()))
            agreement_bonus = max(0.0, 0.3 - prediction_variance)
            ensemble_confidence = min(1.0, ensemble_confidence + agreement_bonus)
            
            return {
                'ensemble_prediction': ensemble_prediction,
                'confidence': ensemble_confidence,
                'prediction_variance': prediction_variance,
                'adjusted_weights': adjusted_weights
            }
            
        except Exception as e:
            self.logger.error(f"Weighted ensemble calculation failed: {e}")
            return {'ensemble_prediction': 0.5, 'confidence': 0.0}
    
    def _calculate_prediction_variance(self, predictions: List[float]) -> float:
        """Calculate variance in model predictions"""
        if len(predictions) < 2:
            return 0.0
        
        mean_pred = sum(predictions) / len(predictions)
        variance = sum((p - mean_pred) ** 2 for p in predictions) / len(predictions)
        return variance
    
    def _store_ensemble_prediction(self, build_id: str, prediction: Dict):
        """Store ensemble prediction in database"""
        try:
            self.db.execute_query("""
                INSERT INTO build_documents (build_id, document_type, title, content, created_at)
                VALUES (%s, 'ml_ensemble', 'Ensemble Prediction', %s, NOW())
            """, (build_id, json.dumps(prediction, default=str)))
            
        except Exception as e:
            self.logger.error(f"Failed to store ensemble prediction: {e}")
    
    def update_model_weights(self, model_accuracies: Dict):
        """Update model weights based on recent performance"""
        try:
            # Store accuracy history
            self.prediction_history.append({
                'timestamp': datetime.now(),
                'model_accuracies': model_accuracies
            })
            
            # Keep only recent history
            self.prediction_history = self.prediction_history[-100:]
            
            # Update weights based on performance
            for model_name, accuracy in model_accuracies.items():
                if model_name in self.model_weights:
                    # Gradually adjust weights toward better-performing models
                    current_weight = self.model_weights[model_name]
                    adjustment = (accuracy - 0.5) * 0.1  # Small adjustments
                    new_weight = max(0.05, min(0.8, current_weight + adjustment))
                    self.model_weights[model_name] = new_weight
            
            # Normalize weights to sum to 1.0
            total_weight = sum(self.model_weights.values())
            if total_weight > 0:
                for model_name in self.model_weights:
                    self.model_weights[model_name] /= total_weight
            
            self.logger.info(f"Updated model weights: {self.model_weights}")
            
        except Exception as e:
            self.logger.error(f"Failed to update model weights: {e}")
    
    def get_ensemble_stats(self) -> Dict:
        """Get ensemble predictor statistics"""
        return {
            'model_weights': self.model_weights.copy(),
            'prediction_history_size': len(self.prediction_history),
            'available_models': list(self.model_weights.keys()),
            'last_update': datetime.now().isoformat()
        }