#!/usr/bin/env python3

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import json

class TrainingScheduler:
    """Automated ML model training scheduler with configurable intervals and triggers"""
    
    def __init__(self, ml_engine, db_manager):
        self.ml_engine = ml_engine
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Scheduler state
        self.running = False
        self.scheduler_thread = None
        self.training_callbacks = []
        
        # Training configuration
        self.config = {
            'auto_training_enabled': True,
            'training_interval_hours': 24,  # Daily by default
            'min_builds_for_training': 10,  # Minimum builds before training
            'training_triggers': {
                'build_completion': True,
                'failure_threshold': 3,  # Train after 3 consecutive failures
                'data_threshold': 50     # Train when 50 new builds available
            }
        }
        
        # Training state tracking
        self.last_training_time = None
        self.builds_since_training = 0
        self.consecutive_failures = 0
        
    def start_scheduler(self):
        """Start the automated training scheduler"""
        if self.running:
            return
            
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("ML training scheduler started")
        
    def stop_scheduler(self):
        """Stop the automated training scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        self.logger.info("ML training scheduler stopped")
        
    def add_training_callback(self, callback: Callable):
        """Add callback to be notified when training occurs"""
        self.training_callbacks.append(callback)
        
    def configure_training(self, **kwargs):
        """Update training configuration"""
        self.config.update(kwargs)
        self.logger.info(f"Training configuration updated: {kwargs}")
        
    def trigger_manual_training(self, force=False):
        """Manually trigger ML model training"""
        try:
            if not force and not self._should_train():
                return {'success': False, 'message': "Training conditions not met"}
                
            self.logger.info("Starting manual ML training")
            success = self._perform_training()
            
            if success:
                self._notify_callbacks("manual_training_completed")
                return {'success': True, 'message': "Training completed successfully"}
            else:
                return {'success': False, 'message': "Training failed"}
                
        except Exception as e:
            self.logger.error(f"Manual training failed: {e}")
            return {'success': False, 'message': f"Training error: {str(e)}"}
            
    def on_build_completed(self, build_id: int, success: bool):
        """Handle build completion events for training triggers"""
        self.builds_since_training += 1
        
        if not success:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0
            
        # Check if we should trigger training
        if self._should_trigger_training():
            threading.Thread(target=self._perform_training, daemon=True).start()
            
    def get_training_status(self) -> Dict:
        """Get current training scheduler status"""
        return {
            'is_running': self.running,
            'scheduler_running': self.running,
            'auto_training_enabled': self.config['auto_training_enabled'],
            'last_training': self.last_training_time.isoformat() if self.last_training_time else None,
            'builds_since_training': self.builds_since_training,
            'consecutive_failures': self.consecutive_failures,
            'next_scheduled_training': self._get_next_training_time(),
            'training_interval_hours': self.config['training_interval_hours'],
            'config': self.config
        }
    
    def get_training_history(self) -> List[Dict]:
        """Get training history from database"""
        try:
            # Get training logs from build documents
            training_logs = self.db_manager.execute_query(
                """SELECT bd.content, bd.created_at, b.build_id
                   FROM build_documents bd
                   JOIN builds b ON bd.build_id = b.build_id
                   WHERE bd.title = 'ML Training Log'
                   AND bd.document_type = 'log'
                   ORDER BY bd.created_at DESC
                   LIMIT 50""",
                fetch=True
            )
            
            history = []
            for log in training_logs:
                try:
                    training_data = json.loads(log['content'])
                    history.append({
                        'timestamp': log['created_at'],
                        'build_id': log['build_id'],
                        'type': training_data.get('type', 'unknown'),
                        'results': training_data.get('results', {}),
                        'builds_processed': training_data.get('builds_processed', 0)
                    })
                except json.JSONDecodeError:
                    # Skip invalid JSON entries
                    continue
            
            return history
            
        except Exception as e:
            self.logger.error(f"Error getting training history: {e}")
            return []
        
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                if self._should_train():
                    self._perform_training()
                    
                # Sleep for 1 hour between checks
                time.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Scheduler loop error: {e}")
                time.sleep(300)  # Sleep 5 minutes on error
                
    def _should_train(self) -> bool:
        """Check if training should occur based on schedule and conditions"""
        if not self.config['auto_training_enabled']:
            return False
            
        # Check minimum builds requirement
        total_builds = self._get_total_builds()
        if total_builds < self.config['min_builds_for_training']:
            return False
            
        # Check time-based training
        if self._is_training_due():
            return True
            
        return False
        
    def _should_trigger_training(self) -> bool:
        """Check if training should be triggered by events"""
        if not self.config['auto_training_enabled']:
            return False
            
        triggers = self.config['training_triggers']
        
        # Check failure threshold
        if (triggers.get('failure_threshold', 0) > 0 and 
            self.consecutive_failures >= triggers['failure_threshold']):
            return True
            
        # Check data threshold
        if (triggers.get('data_threshold', 0) > 0 and 
            self.builds_since_training >= triggers['data_threshold']):
            return True
            
        return False
        
    def _is_training_due(self) -> bool:
        """Check if training is due based on time interval"""
        if not self.last_training_time:
            return True
            
        interval = timedelta(hours=self.config['training_interval_hours'])
        return datetime.now() - self.last_training_time >= interval
        
    def _get_next_training_time(self) -> Optional[str]:
        """Get next scheduled training time"""
        if not self.last_training_time:
            return "Immediate (no previous training)"
            
        next_time = self.last_training_time + timedelta(hours=self.config['training_interval_hours'])
        return next_time.isoformat()
        
    def _get_total_builds(self) -> int:
        """Get total number of builds in database"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM builds")
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            self.logger.error(f"Error getting build count: {e}")
            return 0
            
    def _perform_training(self) -> bool:
        """Perform the actual ML model training"""
        try:
            self.logger.info("Starting automated ML model training")
            
            # Train all models
            training_results = {}
            
            # Train failure predictor
            if hasattr(self.ml_engine, 'failure_predictor'):
                try:
                    self.ml_engine.failure_predictor.train_model()
                    training_results['failure_predictor'] = 'success'
                except Exception as e:
                    training_results['failure_predictor'] = f'failed: {e}'
                    
            # Train performance optimizer
            if hasattr(self.ml_engine, 'performance_optimizer'):
                try:
                    self.ml_engine.performance_optimizer.train_model()
                    training_results['performance_optimizer'] = 'success'
                except Exception as e:
                    training_results['performance_optimizer'] = f'failed: {e}'
                    
            # Train anomaly detector
            if hasattr(self.ml_engine, 'anomaly_detector'):
                try:
                    self.ml_engine.anomaly_detector.train_model()
                    training_results['anomaly_detector'] = 'success'
                except Exception as e:
                    training_results['anomaly_detector'] = f'failed: {e}'
                    
            # Update training state
            self.last_training_time = datetime.now()
            self.builds_since_training = 0
            self.consecutive_failures = 0
            
            # Log training completion
            self._log_training_event(training_results)
            
            # Notify callbacks
            self._notify_callbacks("auto_training_completed", training_results)
            
            self.logger.info(f"ML training completed: {training_results}")
            return True
            
        except Exception as e:
            self.logger.error(f"ML training failed: {e}")
            self._notify_callbacks("training_failed", str(e))
            return False
            
    def _log_training_event(self, results: Dict):
        """Log training event to database"""
        try:
            training_data = {
                'timestamp': datetime.now().isoformat(),
                'type': 'automated_training',
                'results': results,
                'builds_processed': self.builds_since_training,
                'config': self.config
            }
            
            # Create a training build record first
            build_id = f"ml_training_{int(datetime.now().timestamp())}"
            
            # Create build record
            self.db_manager.execute_query("""
                INSERT INTO builds (build_id, config_name, status, total_stages, completed_stages, start_time, end_time)
                VALUES (%s, 'ML Training', 'success', 1, 1, NOW(), NOW())
            """, (build_id,))
            
            # Add training document
            self.db_manager.execute_query("""
                INSERT INTO build_documents (build_id, document_type, title, content, created_at)
                VALUES (%s, 'log', 'ML Training Log', %s, NOW())
            """, (build_id, json.dumps(training_data, indent=2)))
                
        except Exception as e:
            self.logger.error(f"Error logging training event: {e}")
            
    def _notify_callbacks(self, event_type: str, data=None):
        """Notify registered callbacks of training events"""
        for callback in self.training_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                self.logger.error(f"Callback error: {e}")
    
    @property
    def training_interval(self) -> int:
        """Get training interval in hours"""
        return self.config['training_interval_hours']