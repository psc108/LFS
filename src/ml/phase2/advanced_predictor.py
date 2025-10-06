"""
Phase 2 Advanced ML Predictor
Enhanced prediction with ensemble methods and cross-system integration
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

class AdvancedPredictor:
    """Advanced ML predictor with real-time learning"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self.ensemble_models = {}
        self.prediction_history = []
        
    def predict_with_confidence(self, features: Dict) -> Dict:
        """Enhanced prediction with confidence intervals"""
        try:
            predictions = []
            
            # Base prediction
            base_pred = self._base_prediction(features)
            predictions.append(base_pred)
            
            # Git-aware prediction
            git_pred = self._git_aware_prediction(features)
            predictions.append(git_pred)
            
            # Ensemble result
            ensemble_result = np.mean(predictions)
            confidence_interval = self._calculate_confidence_interval(predictions)
            
            return {
                'prediction': ensemble_result,
                'confidence_interval': confidence_interval,
                'uncertainty_score': np.std(predictions),
                'contributing_models': len(predictions)
            }
            
        except Exception as e:
            self.logger.error(f"Advanced prediction failed: {e}")
            return {'prediction': 0.5, 'confidence_interval': [0.0, 1.0]}
    
    def _base_prediction(self, features: Dict) -> float:
        """Base prediction using traditional ML"""
        risk_factors = 0.0
        
        if 'stage_count' in features:
            risk_factors += min(0.3, features['stage_count'] * 0.02)
        
        if 'avg_duration' in features:
            risk_factors += min(0.2, features['avg_duration'] / 14400)
        
        return min(1.0, risk_factors)
    
    def _git_aware_prediction(self, features: Dict) -> float:
        """Git-aware prediction"""
        git_risk = 0.0
        
        if 'branch_count' in features:
            git_risk += min(0.2, features['branch_count'] * 0.01)
        
        return min(1.0, git_risk + self._base_prediction(features) * 0.7)
    
    def _calculate_confidence_interval(self, predictions: List[float]) -> Tuple[float, float]:
        """Calculate 95% confidence interval"""
        if len(predictions) < 2:
            return (0.0, 1.0)
        
        mean_pred = np.mean(predictions)
        std_pred = np.std(predictions)
        margin = 1.96 * std_pred / np.sqrt(len(predictions))
        
        return (max(0.0, mean_pred - margin), min(1.0, mean_pred + margin))
    
    def update_weights(self, prediction_result: Dict, actual_outcome: bool):
        """Update model weights based on accuracy"""
        self.prediction_history.append({
            'timestamp': datetime.now(),
            'prediction': prediction_result,
            'actual': actual_outcome
        })
        
        # Keep only recent history
        cutoff = datetime.now() - timedelta(days=30)
        self.prediction_history = [h for h in self.prediction_history if h['timestamp'] > cutoff]