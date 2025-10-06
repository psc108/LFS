"""
Core ML Engine for LFS Build System

Orchestrates machine learning operations including feature extraction,
model training, and real-time prediction for build intelligence.
"""

import os
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from .feature_extractor import FeatureExtractor
from .storage.model_manager import ModelManager
from .training_scheduler import TrainingScheduler
from .phase2.advanced_predictor import AdvancedPredictor
from .phase2.real_time_learner import RealTimeLearner
from .phase2.cross_system_integrator import CrossSystemIntegrator
from .phase2.production_integrator import ProductionCrossSystemIntegrator


class MLEngine:
    """Main ML orchestrator that integrates with existing LFS build system"""
    
    def __init__(self, db_manager, config_path: Optional[str] = None):
        """Initialize ML engine with database connection"""
        self.db = db_manager
        self.feature_extractor = FeatureExtractor(db_manager)
        self.model_manager = ModelManager()
        self.models = {}
        self.enabled = True
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize models
        self._initialize_models()
        
        # Initialize training scheduler
        self.training_scheduler = TrainingScheduler(self, db_manager)
        self.training_scheduler.start_scheduler()
        
        # Phase 2: Advanced ML capabilities
        self.advanced_predictor = AdvancedPredictor(db_manager)
        self.real_time_learner = RealTimeLearner(self, db_manager)
        self.cross_system_integrator = CrossSystemIntegrator(db_manager)
        self.production_integrator = ProductionCrossSystemIntegrator(db_manager)
        
        # Phase 2: Additional components
        from .inference.real_time_inference import RealTimeInferenceEngine
        from .inference.ensemble_predictor import EnsemblePredictor
        from .training.adaptive_trainer import AdaptiveTrainer
        
        self.real_time_inference = RealTimeInferenceEngine(self, db_manager)
        self.ensemble_predictor = EnsemblePredictor(self, db_manager)
        self.adaptive_trainer = AdaptiveTrainer(self, db_manager)
        
        # Initialize data pipeline first
        self.data_pipeline = None
        self.adaptive_training_started = False
        self._init_data_pipeline()
        
        # Start Phase 2 services
        self.real_time_learner.start_learning()
        self.real_time_inference.start_inference_monitoring()
        
        # Start background retry mechanism
        self._start_background_retry()
        
        # Phase 3: Build Optimization
        from .optimization.build_optimizer import BuildOptimizer
        self.build_optimizer = BuildOptimizer(db_manager)
        
        # Stage 4: Advanced Analysis Components
        from .analysis import LogAnalyzer, AnomalyDetector as SystemAnomalyDetector, MaintenanceAdvisor
        from .research.solution_finder import SolutionFinder
        from .monitoring.live_build_monitor import LiveBuildMonitor
        self.log_analyzer = LogAnalyzer(db_manager)
        self.system_anomaly_detector = SystemAnomalyDetector(db_manager)
        self.maintenance_advisor = MaintenanceAdvisor(db_manager, self.log_analyzer, self.system_anomaly_detector)
        self.solution_finder = SolutionFinder(db_manager)
        self.live_monitor = LiveBuildMonitor(db_manager, self)
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load ML configuration"""
        default_config = {
            "enabled": True,
            "models": {
                "failure_predictor": {"enabled": True, "retrain_interval": 24},
                "performance_optimizer": {"enabled": True, "retrain_interval": 48},
                "anomaly_detector": {"enabled": True, "retrain_interval": 72}
            },
            "feature_extraction": {
                "batch_size": 100,
                "lookback_days": 30
            },
            "prediction": {
                "confidence_threshold": 0.7,
                "cache_predictions": True
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                self.logger.warning(f"Failed to load ML config: {e}")
        
        return default_config
    
    def _initialize_models(self):
        """Initialize available ML models"""
        try:
            if self.config["models"]["failure_predictor"]["enabled"]:
                from .models.failure_predictor import FailurePredictor
                self.models["failure_predictor"] = FailurePredictor(self.db)
            
            if self.config["models"]["performance_optimizer"]["enabled"]:
                from .models.performance_optimizer import PerformanceOptimizer
                self.models["performance_optimizer"] = PerformanceOptimizer(self.db)
            
            if self.config["models"]["anomaly_detector"]["enabled"]:
                from .models.anomaly_detector import AnomalyDetector
                self.models["anomaly_detector"] = AnomalyDetector(self.db)
                
            self.logger.info(f"Initialized {len(self.models)} ML models")
            
        except ImportError as e:
            self.logger.warning(f"ML dependencies not available: {e}")
            self.enabled = False
        except Exception as e:
            self.logger.error(f"Failed to initialize ML models: {e}")
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """Check if ML engine is enabled and functional"""
        return self.enabled and len(self.models) > 0
    
    def extract_build_features(self, build_id: str) -> Optional[Dict]:
        """Extract features for a specific build"""
        if not self.is_enabled():
            return None
        
        try:
            return self.feature_extractor.extract_build_features(build_id)
        except Exception as e:
            self.logger.error(f"Feature extraction failed for build {build_id}: {e}")
            return None
    
    def predict_failure_risk(self, build_data: Dict) -> Optional[Dict]:
        """Predict failure risk for current build data"""
        if not self.is_enabled() or "failure_predictor" not in self.models:
            return None
        
        try:
            predictor = self.models["failure_predictor"]
            prediction = predictor.predict(build_data)
            
            if prediction and prediction.get("confidence", 0) >= self.config["prediction"]["confidence_threshold"]:
                return {
                    "risk_score": prediction["risk_score"],
                    "confidence": prediction["confidence"],
                    "predicted_failure_stage": prediction.get("failure_stage"),
                    "recommendations": prediction.get("recommendations", []),
                    "timestamp": datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failure prediction failed: {e}")
            return None
    
    def optimize_build_config(self, config_data: Dict) -> Optional[Dict]:
        """Suggest optimizations for build configuration"""
        if not self.is_enabled() or "performance_optimizer" not in self.models:
            return None
        
        try:
            optimizer = self.models["performance_optimizer"]
            optimizations = optimizer.optimize(config_data)
            
            return {
                "optimized_config": optimizations.get("config"),
                "expected_improvement": optimizations.get("improvement_percent"),
                "confidence": optimizations.get("confidence"),
                "changes": optimizations.get("changes", []),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Build optimization failed: {e}")
            return None
    
    def detect_anomalies(self, system_metrics: Dict) -> Optional[Dict]:
        """Detect system anomalies during build"""
        if not self.is_enabled() or "anomaly_detector" not in self.models:
            return None
        
        try:
            detector = self.models["anomaly_detector"]
            anomalies = detector.detect(system_metrics)
            
            if anomalies and anomalies.get("anomaly_score", 0) > 0.5:
                return {
                    "anomaly_score": anomalies["anomaly_score"],
                    "anomaly_type": anomalies.get("type"),
                    "affected_metrics": anomalies.get("metrics", []),
                    "severity": anomalies.get("severity", "medium"),
                    "recommendations": anomalies.get("recommendations", []),
                    "timestamp": datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Anomaly detection failed: {e}")
            return None
    
    def get_ml_insights(self, build_id: str) -> Dict:
        """Get comprehensive ML insights for a build"""
        insights = {
            "ml_enabled": self.is_enabled(),
            "available_models": list(self.models.keys()),
            "insights": {}
        }
        
        if not self.is_enabled():
            return insights
        
        # Attempt to initialize data pipeline if needed
        if not self.data_pipeline:
            self._init_data_pipeline()
        
        # Extract features
        features = self.extract_build_features(build_id)
        if features:
            insights["features_extracted"] = True
            
            # Get failure prediction
            failure_risk = self.predict_failure_risk(features)
            if failure_risk:
                insights["insights"]["failure_prediction"] = failure_risk
            
            # Get performance optimization
            if "build_config" in features:
                optimization = self.optimize_build_config(features["build_config"])
                if optimization:
                    insights["insights"]["performance_optimization"] = optimization
            
            # Get anomaly detection
            if "system_metrics" in features:
                anomalies = self.detect_anomalies(features["system_metrics"])
                if anomalies:
                    insights["insights"]["anomaly_detection"] = anomalies
        
        return insights
    
    def get_system_wide_insights(self) -> Dict:
        """Get ML insights across all system facilities"""
        try:
            from .system_advisor import SystemAdvisor
            
            advisor = SystemAdvisor(self.db)
            return advisor.get_comprehensive_system_insights()
            
        except Exception as e:
            self.logger.error(f"System-wide insights failed: {e}")
            return {"error": str(e), "ml_enabled": self.is_enabled()}
    
    def train_models(self, force_retrain: bool = False) -> Dict:
        """Train or retrain ML models using real database data only"""
        results = {"trained_models": [], "errors": [], "data_source": "real_database_only"}
        
        if not self.is_enabled():
            results["errors"].append("ML engine not enabled")
            return results
        
        # Ensure data pipeline is available for training
        if not self.data_pipeline:
            self._init_data_pipeline()
        
        for model_name, model in self.models.items():
            try:
                if hasattr(model, 'needs_training') and (model.needs_training() or force_retrain):
                    self.logger.info(f"Training model: {model_name} with real database data only")
                    training_result = model.train()
                    
                    if training_result.get("success"):
                        model_result = {
                            "model": model_name,
                            "accuracy": training_result.get("accuracy"),
                            "training_time": training_result.get("training_time"),
                            "samples_used": training_result.get("samples_used"),
                            "training_method": training_result.get("training_method", "unknown"),
                            "data_source": "real_database_only"
                        }
                        
                        if training_result.get("note"):
                            model_result["note"] = training_result["note"]
                        
                        results["trained_models"].append(model_result)
                    else:
                        results["errors"].append(f"{model_name}: {training_result.get('error')}")
                        
            except Exception as e:
                results["errors"].append(f"{model_name}: {str(e)}")
                self.logger.error(f"Training failed for {model_name}: {e}")
        
        return results
    
    def get_model_status(self) -> Dict:
        """Get status of all ML models"""
        status = {
            "ml_enabled": self.is_enabled(),
            "models": {}
        }
        
        for model_name, model in self.models.items():
            try:
                model_status = {
                    "loaded": True,
                    "trained": hasattr(model, 'is_trained') and model.is_trained(),
                    "last_training": getattr(model, 'last_training_time', None),
                    "accuracy": getattr(model, 'accuracy', None),
                    "predictions_made": getattr(model, 'prediction_count', 0)
                }
                
                if hasattr(model, 'needs_training'):
                    model_status["needs_training"] = model.needs_training()
                
                status["models"][model_name] = model_status
                
            except Exception as e:
                status["models"][model_name] = {"loaded": False, "error": str(e)}
        
        return status
    
    def get_health_status(self):
        """Get overall ML system health status"""
        try:
            status = {
                'overall_health': 'Good' if self.is_enabled() else 'Disabled',
                'components': {
                    'feature_extractor': 'Active' if hasattr(self, 'feature_extractor') else 'Inactive',
                    'model_manager': 'Active' if hasattr(self, 'model_manager') else 'Inactive',
                    'models_loaded': len(self.models),
                    'data_pipeline': 'Active' if self.data_pipeline else 'Initializing...',
                    'adaptive_training': 'Active' if self.adaptive_training_started else 'Pending'
                },
                'database_connection': 'Connected' if self.db else 'Disconnected',
                'enabled_models': list(self.models.keys()),
                'background_retry': 'Active' if hasattr(self, 'retry_active') and self.retry_active else 'Inactive',
                'data_source': 'real_database_only',
                'no_demo_data': True
            }
            return status
        except Exception as e:
            return {'overall_health': 'Error', 'error': str(e)}
    
    def get_prediction_accuracy(self):
        """Get prediction accuracy metrics from real model training"""
        try:
            accuracy_data = {
                'models_evaluated': len(self.models),
                'data_source': 'real_database_only'
            }
            
            # Get actual accuracy from trained models
            for model_name, model in self.models.items():
                if hasattr(model, 'accuracy') and model.accuracy is not None:
                    accuracy_data[f'{model_name}_accuracy'] = model.accuracy
                    accuracy_data[f'{model_name}_predictions'] = getattr(model, 'prediction_count', 0)
                else:
                    accuracy_data[f'{model_name}_accuracy'] = None
                    accuracy_data[f'{model_name}_note'] = 'No supervised training data available'
            
            return accuracy_data
        except Exception as e:
            return {'error': str(e)}
    
    @property
    def failure_predictor(self):
        """Get failure predictor model"""
        return self.models.get('failure_predictor')
    
    @property
    def performance_optimizer(self):
        """Get performance optimizer model"""
        return self.models.get('performance_optimizer')
    
    @property
    def anomaly_detector(self):
        """Get anomaly detector model"""
        return self.models.get('anomaly_detector')
    
    def trigger_manual_training(self, force=False):
        """Trigger manual ML model training"""
        try:
            if hasattr(self, 'training_scheduler') and self.training_scheduler:
                return self.training_scheduler.trigger_manual_training(force)
            else:
                return {'success': False, 'error': 'Training scheduler not available'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
    def configure_auto_training(self, **kwargs):
        """Configure automated training parameters"""
        self.training_scheduler.configure_training(**kwargs)
        
    def get_training_status(self):
        """Get current training scheduler status"""
        return self.training_scheduler.get_training_status()
        
    def on_build_completed(self, build_id: int, success: bool):
        """Notify ML system of build completion for training triggers"""
        self.training_scheduler.on_build_completed(build_id, success)
        
        # Attempt to initialize data pipeline on build completion
        if not self.data_pipeline:
            self._init_data_pipeline()
        
        # Phase 2: Add feedback for real-time learning
        if hasattr(self, 'real_time_learner'):
            outcome = 'success' if success else 'failed'
            # Get last prediction for this build (simplified)
            last_prediction = {'prediction': 0.5}  # Would be stored from actual prediction
            self.add_build_feedback(str(build_id), last_prediction, outcome)
        
    def predict_advanced(self, build_data: Dict) -> Optional[Dict]:
        """Phase 2: Advanced prediction with confidence intervals and cross-system integration"""
        if not self.is_enabled():
            return None
        
        try:
            # Extract cross-system features
            build_id = build_data.get('build_id', 'unknown')
            integrated_features = self.cross_system_integrator.get_integrated_features(str(build_id))
            
            # Combine with existing features
            combined_features = {**build_data, **integrated_features}
            
            # Get advanced prediction
            prediction = self.advanced_predictor.predict_with_confidence(combined_features)
            
            # Get cross-system impact predictions
            impact_predictions = self.cross_system_integrator.predict_cross_system_impact(combined_features)
            
            return {
                'advanced_prediction': prediction,
                'cross_system_impacts': impact_predictions,
                'timestamp': datetime.now().isoformat(),
                'phase': 'Phase 2 Advanced ML'
            }
            
        except Exception as e:
            self.logger.error(f"Advanced prediction failed: {e}")
            return None
    
    def predict_production(self, build_data: Dict) -> Optional[Dict]:
        """Production prediction with real system integration"""
        if not self.is_enabled():
            return None
        
        try:
            build_id = build_data.get('build_id', 'unknown')
            
            # Get production features from real systems
            production_features = self.production_integrator.get_production_features(str(build_id))
            
            # Combine with build data
            combined_features = {**build_data, **production_features}
            
            # Get prediction with real data
            prediction = self.advanced_predictor.predict_with_confidence(combined_features)
            
            return {
                'production_prediction': prediction,
                'real_system_features': production_features,
                'feature_count': len(combined_features),
                'timestamp': datetime.now().isoformat(),
                'mode': 'Production ML'
            }
            
        except Exception as e:
            self.logger.error(f"Production prediction failed: {e}")
            return None
    
    def add_build_feedback(self, build_id: str, prediction: Dict, actual_outcome: str):
        """Phase 2: Add feedback for real-time learning"""
        try:
            # Ensure data pipeline is available for feedback processing
            if not self.data_pipeline:
                self._init_data_pipeline()
            
            self.real_time_learner.add_feedback(build_id, prediction, actual_outcome)
        except Exception as e:
            self.logger.error(f"Failed to add build feedback: {e}")
    
    def get_phase2_status(self) -> Dict:
        """Get Phase 2 ML system status"""
        try:
            return {
                'phase2_enabled': True,
                'advanced_predictor': hasattr(self, 'advanced_predictor'),
                'real_time_learner': self.real_time_learner.get_learning_stats() if hasattr(self, 'real_time_learner') else {},
                'cross_system_integration': hasattr(self, 'cross_system_integrator'),
                'real_time_inference': hasattr(self, 'real_time_inference'),
                'ensemble_predictor': hasattr(self, 'ensemble_predictor'),
                'adaptive_trainer': hasattr(self, 'adaptive_trainer'),
                'capabilities': [
                    'Advanced Prediction with Confidence Intervals',
                    'Real-time Learning and Model Updates',
                    'Cross-system Integration (Git, CI/CD, Security)',
                    'Ensemble Prediction Methods',
                    'Real-time Inference Engine',
                    'Adaptive Model Training',
                    'Production System Integration'
                ]
            }
        except Exception as e:
            return {'error': str(e), 'phase2_enabled': False}
    
    def get_real_time_prediction(self, build_id: str, current_stage: str = None) -> Dict:
        """Get real-time ML prediction for active build"""
        try:
            return self.real_time_inference.predict_build_outcome(build_id, current_stage)
        except Exception as e:
            self.logger.error(f"Real-time prediction failed: {e}")
            return {'error': str(e)}
    
    def get_ensemble_prediction(self, features: Dict) -> Dict:
        """Get ensemble prediction from multiple models"""
        try:
            return self.ensemble_predictor.ensemble_predict(features)
        except Exception as e:
            self.logger.error(f"Ensemble prediction failed: {e}")
            return {'error': str(e)}
    
    def trigger_adaptive_training(self, model_name: str = None) -> Dict:
        """Trigger adaptive training for models"""
        try:
            # If data pipeline not ready, try to initialize it first
            if not self.data_pipeline:
                self._init_data_pipeline()
            
            if self.data_pipeline:
                return self.adaptive_trainer.trigger_immediate_training(model_name)
            else:
                return {'error': 'Data pipeline not available', 'retry_active': True}
        except Exception as e:
            self.logger.error(f"Adaptive training failed: {e}")
            return {'error': str(e)}
    
    def get_comprehensive_ml_status(self) -> Dict:
        """Get comprehensive ML system status including Phase 2"""
        try:
            status = self.get_model_status()
            
            # Add Phase 2 status
            status['phase2'] = {
                'real_time_inference': self.real_time_inference.get_inference_stats() if hasattr(self, 'real_time_inference') else {},
                'ensemble_predictor': self.ensemble_predictor.get_ensemble_stats() if hasattr(self, 'ensemble_predictor') else {},
                'adaptive_trainer': self.adaptive_trainer.get_training_status() if hasattr(self, 'adaptive_trainer') else {},
                'real_time_learner': self.real_time_learner.get_learning_stats() if hasattr(self, 'real_time_learner') else {}
            }
            
            # Add initialization status
            status['initialization'] = {
                'data_pipeline_ready': self.data_pipeline is not None,
                'adaptive_training_started': self.adaptive_training_started,
                'background_retry_active': hasattr(self, 'retry_active') and self.retry_active
            }
            
            # Add Stage 4 status with solution database analytics
            status['stage4'] = {
                'log_analyzer': hasattr(self, 'log_analyzer'),
                'system_anomaly_detector': hasattr(self, 'system_anomaly_detector'),
                'maintenance_advisor': hasattr(self, 'maintenance_advisor'),
                'solution_finder': hasattr(self, 'solution_finder'),
                'live_monitor': hasattr(self, 'live_monitor'),
                'solution_database': self.get_solution_analytics() if hasattr(self, 'solution_finder') else {'status': 'not_initialized'},
                'live_monitoring': self.get_live_monitoring_status() if hasattr(self, 'live_monitor') else {'status': 'not_initialized'},
                'capabilities': [
                    'Log Analysis for Root Cause Detection',
                    'System Health Anomaly Detection',
                    'Predictive Maintenance Recommendations',
                    'Internet-based Solution Research with Caching',
                    'Solution Effectiveness Tracking',
                    'Automated Solution Database Updates',
                    'Real-time Build Log Monitoring',
                    'On-the-fly Error Detection and Correction'
                ]
            }
            
            return status
            
        except Exception as e:
            return {'error': str(e), 'ml_enabled': False}
    
    def start_build_monitoring(self, build_id: str, stage_name: str = None):
        """Start comprehensive ML monitoring for active build"""
        try:
            # Attempt to initialize data pipeline if not ready
            if not self.data_pipeline:
                self._init_data_pipeline()
            
            # Start live log monitoring with error detection
            if hasattr(self, 'live_monitor'):
                self.live_monitor.start_monitoring(build_id, stage_name)
                self.logger.info(f"Started live build monitoring for {build_id}")
            
            # Detect system anomalies for this build
            anomalies = self.detect_system_anomalies(build_id)
            if anomalies.get('anomaly_count', 0) > 0:
                self.logger.warning(f"System anomalies detected for build {build_id}: {anomalies['anomaly_count']} issues")
            
            if hasattr(self, 'real_time_inference'):
                # Monitor build in real-time
                prediction = self.real_time_inference.predict_build_outcome(build_id)
                self.logger.info(f"Started ML monitoring for build {build_id}: {prediction.get('overall_risk', 'unknown')}")
        except Exception as e:
            self.logger.error(f"Failed to start build monitoring: {e}")
    
    def stop_build_monitoring(self, build_id: str):
        """Stop ML monitoring for build"""
        try:
            if hasattr(self, 'live_monitor'):
                self.live_monitor.stop_monitoring(build_id)
                self.logger.info(f"Stopped live monitoring for build {build_id}")
        except Exception as e:
            self.logger.error(f"Failed to stop build monitoring: {e}")
    
    def get_live_monitoring_status(self) -> Dict:
        """Get live monitoring status"""
        try:
            if hasattr(self, 'live_monitor'):
                return self.live_monitor.get_monitoring_status()
            else:
                return {'error': 'Live monitor not available'}
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_system_performance(self) -> Dict:
        """Analyze overall system performance using ML"""
        try:
            # Get system-wide insights
            insights = self.get_system_wide_insights()
            
            # Add ensemble analysis
            if hasattr(self, 'ensemble_predictor'):
                ensemble_stats = self.ensemble_predictor.get_ensemble_stats()
                insights['ensemble_analysis'] = ensemble_stats
            
            # Add adaptive training insights
            if hasattr(self, 'adaptive_trainer'):
                training_status = self.adaptive_trainer.get_training_status()
                insights['adaptive_training'] = training_status
            
            return insights
            
        except Exception as e:
            return {'error': str(e)}
    
    def _init_data_pipeline(self):
        """Initialize data pipeline with error handling"""
        try:
            from .training.data_pipeline import DataPipeline
            self.data_pipeline = DataPipeline(self.db)
            self.logger.info("Data pipeline initialized successfully")
            
            # Start adaptive training if not already started
            if not self.adaptive_training_started:
                self.adaptive_trainer.start_adaptive_training()
                self.adaptive_training_started = True
                self.logger.info("Adaptive training started successfully")
                
        except Exception as e:
            self.logger.warning(f"Data pipeline initialization failed: {e}")
            self.data_pipeline = None
    
    def _start_background_retry(self):
        """Start background thread to retry data pipeline initialization"""
        self.retry_active = True
        self.retry_thread = threading.Thread(target=self._background_retry_loop, daemon=True)
        self.retry_thread.start()
        self.logger.info("Background retry mechanism started")
    
    def _background_retry_loop(self):
        """Background loop to continuously retry initialization"""
        retry_interval = 30  # Start with 30 seconds
        max_interval = 300   # Max 5 minutes
        
        while self.retry_active:
            try:
                time.sleep(retry_interval)
                
                # Only retry if data pipeline is not available
                if not self.data_pipeline or not self.adaptive_training_started:
                    self.logger.debug("Attempting data pipeline initialization...")
                    self._init_data_pipeline()
                    
                    # If successful, we can stop retrying
                    if self.data_pipeline and self.adaptive_training_started:
                        self.logger.info("Data pipeline and adaptive training successfully initialized")
                        break
                    else:
                        # Exponential backoff with max limit
                        retry_interval = min(retry_interval * 1.5, max_interval)
                        self.logger.debug(f"Retry failed, next attempt in {retry_interval} seconds")
                else:
                    # Everything is working, stop retrying
                    break
                    
            except Exception as e:
                self.logger.error(f"Background retry error: {e}")
                retry_interval = min(retry_interval * 2, max_interval)
    
    def get_build_optimization(self, config_name: str = None) -> Dict:
        """Phase 3: Get ML-driven build optimization recommendations"""
        try:
            if hasattr(self, 'build_optimizer') and self.build_optimizer:
                result = self.build_optimizer.optimize_build_configuration(config_name)
                return result if result else {'error': 'No optimization result returned'}
            else:
                return {'error': 'Build optimizer not available'}
        except Exception as e:
            self.logger.error(f"Build optimization failed: {e}")
            return {'error': str(e)}
    
    def get_parallel_job_recommendation(self) -> Dict:
        """Phase 3: Get optimal parallel job count recommendation"""
        try:
            if hasattr(self, 'build_optimizer') and self.build_optimizer:
                result = self.build_optimizer.recommend_parallel_jobs()
                return result if result else {'error': 'No recommendation result returned'}
            else:
                return {'error': 'Build optimizer not available'}
        except Exception as e:
            self.logger.error(f"Parallel job recommendation failed: {e}")
            return {'error': str(e)}
    
    def analyze_build_performance_history(self, days_back: int = 30) -> Dict:
        """Phase 3: Analyze historical build performance for optimization"""
        try:
            if hasattr(self, 'build_optimizer') and self.build_optimizer:
                result = self.build_optimizer.analyze_historical_performance(days_back)
                return result if result else {'error': 'No analysis result returned'}
            else:
                return {'error': 'Build optimizer not available'}
        except Exception as e:
            self.logger.error(f"Performance history analysis failed: {e}")
            return {'error': str(e)}
    
    def analyze_build_logs(self, build_id: str) -> Dict:
        """Stage 4: Analyze build logs for root cause detection"""
        try:
            if hasattr(self, 'log_analyzer'):
                # Ensure we have a valid build ID from the database
                build_exists = self.db.execute_query(
                    "SELECT build_id FROM builds WHERE build_id = %s",
                    (build_id,), fetch=True
                )
                
                if not build_exists:
                    return {'error': f'Build {build_id} not found in database'}
                
                analysis_result = self.log_analyzer.analyze_build_logs(build_id)
                
                # Store analysis results in database
                if 'error' not in analysis_result:
                    self.db.add_document(
                        build_id,
                        'analysis',
                        f'Log Analysis Results for {build_id}',
                        json.dumps(analysis_result, indent=2),
                        {'analysis_type': 'log_analysis', 'stage4_ml': True}
                    )
                
                return analysis_result
            else:
                return {'error': 'Log analyzer not available'}
        except Exception as e:
            self.logger.error(f"Log analysis failed: {e}")
            return {'error': str(e)}
    
    def detect_system_anomalies(self, build_id: str = None) -> Dict:
        """Stage 4: Detect system health anomalies"""
        try:
            if hasattr(self, 'system_anomaly_detector'):
                anomaly_result = self.system_anomaly_detector.detect_anomalies()
                
                # Store anomaly detection results only if we have a valid build_id
                if 'error' not in anomaly_result and anomaly_result.get('anomaly_count', 0) > 0 and build_id:
                    # Verify build exists before saving document
                    build_exists = self.db.execute_query(
                        "SELECT build_id FROM builds WHERE build_id = %s",
                        (build_id,), fetch=True
                    )
                    
                    if build_exists:
                        self.db.add_document(
                            build_id,
                            'anomaly_report',
                            f'System Anomaly Detection - {anomaly_result["timestamp"]}',
                            json.dumps(anomaly_result, indent=2),
                            {'analysis_type': 'anomaly_detection', 'stage4_ml': True, 'severity': 'high' if anomaly_result.get('anomaly_count', 0) > 5 else 'medium'}
                        )
                    else:
                        # Log anomaly without saving to build_documents
                        self.logger.warning(f"System anomalies detected before build {build_id}: {anomaly_result.get('anomaly_count', 0)} issues")
                
                return anomaly_result
            else:
                return {'error': 'System anomaly detector not available'}
        except Exception as e:
            self.logger.error(f"System anomaly detection failed: {e}")
            return {'error': str(e)}
    
    def get_system_health_summary(self) -> Dict:
        """Stage 4: Get comprehensive system health summary"""
        try:
            if hasattr(self, 'system_anomaly_detector'):
                return self.system_anomaly_detector.get_health_summary()
            else:
                return {'error': 'System anomaly detector not available'}
        except Exception as e:
            self.logger.error(f"System health summary failed: {e}")
            return {'error': str(e)}
    
    def generate_maintenance_recommendations(self) -> Dict:
        """Stage 4: Generate predictive maintenance recommendations"""
        try:
            if hasattr(self, 'maintenance_advisor'):
                recommendations = self.maintenance_advisor.generate_maintenance_recommendations()
                
                # Store maintenance recommendations
                if 'error' not in recommendations and recommendations.get('total_recommendations', 0) > 0:
                    self.db.add_document(
                        'system_maintenance',
                        'maintenance_report',
                        f'Maintenance Recommendations - {recommendations["timestamp"]}',
                        json.dumps(recommendations, indent=2),
                        {'analysis_type': 'maintenance_recommendations', 'stage4_ml': True, 'priority_counts': recommendations.get('priority_counts', {})}
                    )
                
                return recommendations
            else:
                return {'error': 'Maintenance advisor not available'}
        except Exception as e:
            self.logger.error(f"Maintenance recommendations failed: {e}")
            return {'error': str(e)}
    
    def get_maintenance_checklist(self, priority: str = 'all') -> Dict:
        """Stage 4: Get maintenance checklist by priority"""
        try:
            if hasattr(self, 'maintenance_advisor'):
                return self.maintenance_advisor.get_maintenance_checklist(priority)
            else:
                return {'error': 'Maintenance advisor not available'}
        except Exception as e:
            self.logger.error(f"Maintenance checklist failed: {e}")
            return {'error': str(e)}
    
    def find_build_solutions(self, build_id: str) -> Dict:
        """Find internet-based solutions for build failures with comprehensive tracking"""
        try:
            if hasattr(self, 'solution_finder'):
                report = self.solution_finder.generate_solution_report(int(build_id))
                
                # Log solution research activity
                self.logger.info(f"Generated solution report for build {build_id}: "
                               f"{report.get('solutions_found', 0)} solutions found, "
                               f"{report.get('cached_solutions', 0)} from cache, "
                               f"{report.get('new_solutions', 0)} new searches")
                
                return report
            else:
                return {'error': 'Solution finder not available'}
        except Exception as e:
            self.logger.error(f"Solution finding failed: {e}")
            return {'error': str(e)}
    
    def search_error_solutions(self, error_message: str, build_stage: str, package_name: str = None) -> List[Dict]:
        """Search for solutions to specific build errors with caching"""
        try:
            if hasattr(self, 'solution_finder'):
                solutions = self.solution_finder.find_solutions(error_message, build_stage, package_name)
                
                # Log solution search activity
                self.logger.info(f"Found {len(solutions)} solutions for error in stage {build_stage}")
                
                return solutions
            else:
                return []
        except Exception as e:
            self.logger.error(f"Error solution search failed: {e}")
            return []
    
    def mark_solution_effective(self, error_message: str, effectiveness_rating: float):
        """Mark a solution as effective for machine learning improvement"""
        try:
            if hasattr(self, 'solution_finder'):
                self.solution_finder.mark_solution_effective(error_message, effectiveness_rating)
                self.logger.info(f"Marked solution effectiveness: {effectiveness_rating}")
        except Exception as e:
            self.logger.error(f"Failed to mark solution effectiveness: {e}")
    
    def get_solution_analytics(self) -> Dict:
        """Get analytics on solution database for ML insights"""
        try:
            if hasattr(self, 'solution_finder'):
                return self.solution_finder.get_solution_analytics()
            else:
                return {'error': 'Solution finder not available'}
        except Exception as e:
            self.logger.error(f"Failed to get solution analytics: {e}")
            return {'error': str(e)}
    
    def shutdown(self):
        """Shutdown ML engine and cleanup resources"""
        try:
            # Stop background retry
            self.retry_active = False
            
            if hasattr(self, 'training_scheduler'):
                self.training_scheduler.stop_scheduler()
            if hasattr(self, 'real_time_learner'):
                self.real_time_learner.stop_learning()
            if hasattr(self, 'real_time_inference'):
                self.real_time_inference.stop_inference_monitoring()
            if hasattr(self, 'adaptive_trainer'):
                self.adaptive_trainer.stop_adaptive_training()
            self.logger.info("ML Engine shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during ML engine shutdown: {e}")