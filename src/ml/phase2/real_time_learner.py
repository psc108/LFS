"""
Phase 2 Real-time Learning System
Continuous model improvement during system operation
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List
import logging

class RealTimeLearner:
    """Real-time learning system for continuous model improvement"""
    
    def __init__(self, ml_engine, db_manager):
        self.ml_engine = ml_engine
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        
        self.learning_active = False
        self.learning_thread = None
        self.feedback_queue = []
        
    def start_learning(self):
        """Start real-time learning process"""
        if self.learning_active:
            return
            
        self.learning_active = True
        self.learning_thread = threading.Thread(target=self._learning_loop, daemon=True)
        self.learning_thread.start()
        self.logger.info("Real-time learning started")
    
    def stop_learning(self):
        """Stop real-time learning process"""
        self.learning_active = False
        if self.learning_thread:
            self.learning_thread.join(timeout=5)
        self.logger.info("Real-time learning stopped")
    
    def add_feedback(self, build_id: str, prediction: Dict, actual_outcome: str):
        """Add feedback for model improvement"""
        feedback = {
            'timestamp': datetime.now(),
            'build_id': build_id,
            'prediction': prediction,
            'actual_outcome': actual_outcome,
            'processed': False
        }
        self.feedback_queue.append(feedback)
    
    def _learning_loop(self):
        """Main learning loop"""
        while self.learning_active:
            try:
                self._process_feedback_batch()
                time.sleep(300)  # Process every 5 minutes
            except Exception as e:
                self.logger.error(f"Learning loop error: {e}")
                time.sleep(60)
    
    def _process_feedback_batch(self):
        """Process batch of feedback for model updates"""
        unprocessed = [f for f in self.feedback_queue if not f['processed']]
        
        if len(unprocessed) >= 5:  # Process in batches of 5+
            for feedback in unprocessed[:10]:  # Process up to 10 at once
                self._update_model_from_feedback(feedback)
                feedback['processed'] = True
            
            # Clean old feedback
            cutoff = datetime.now() - timedelta(days=7)
            self.feedback_queue = [f for f in self.feedback_queue if f['timestamp'] > cutoff]
    
    def _update_model_from_feedback(self, feedback: Dict):
        """Update model based on single feedback"""
        try:
            # Extract features and outcome
            prediction = feedback['prediction']
            actual_success = feedback['actual_outcome'] == 'success'
            
            # Update advanced predictor if available
            if hasattr(self.ml_engine, 'advanced_predictor'):
                self.ml_engine.advanced_predictor.update_weights(prediction, actual_success)
            
            # Log learning event
            self._log_learning_event(feedback)
            
        except Exception as e:
            self.logger.error(f"Model update failed: {e}")
    
    def _log_learning_event(self, feedback: Dict):
        """Log learning event to database"""
        try:
            learning_data = {
                'timestamp': feedback['timestamp'].isoformat(),
                'build_id': feedback['build_id'],
                'prediction_accuracy': self._calculate_accuracy(feedback),
                'model_updated': True
            }
            
            # Store in database
            self.db.execute_query("""
                INSERT INTO build_documents (build_id, document_type, title, content, created_at)
                VALUES (%s, 'ml_learning', 'Real-time Learning Event', %s, NOW())
            """, (feedback['build_id'], str(learning_data)))
            
        except Exception as e:
            self.logger.error(f"Failed to log learning event: {e}")
    
    def _calculate_accuracy(self, feedback: Dict) -> float:
        """Calculate prediction accuracy"""
        predicted_risk = feedback['prediction'].get('prediction', 0.5)
        actual_success = feedback['actual_outcome'] == 'success'
        actual_risk = 0.0 if actual_success else 1.0
        
        return 1.0 - abs(predicted_risk - actual_risk)
    
    def get_learning_stats(self) -> Dict:
        """Get real-time learning statistics"""
        processed = [f for f in self.feedback_queue if f['processed']]
        unprocessed = [f for f in self.feedback_queue if not f['processed']]
        
        if processed:
            accuracies = [self._calculate_accuracy(f) for f in processed]
            avg_accuracy = sum(accuracies) / len(accuracies)
        else:
            avg_accuracy = 0.0
        
        return {
            'learning_active': self.learning_active,
            'total_feedback': len(self.feedback_queue),
            'processed_feedback': len(processed),
            'pending_feedback': len(unprocessed),
            'average_accuracy': avg_accuracy,
            'last_update': processed[-1]['timestamp'].isoformat() if processed else None
        }