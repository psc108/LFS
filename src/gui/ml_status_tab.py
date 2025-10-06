"""
ML Status Tab - Monitor ML system activity and insights
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import json
from datetime import datetime

class MLStatusTab(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.ml_engine = None
        self.init_ui()
        self.init_ml_engine()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("🤖 Machine Learning System Status")
        header.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(header)
        
        # Status overview
        status_group = QGroupBox("System Status")
        status_layout = QGridLayout()
        
        self.status_label = QLabel("Initializing...")
        self.models_label = QLabel("Models: 0")
        self.accuracy_label = QLabel("Accuracy: N/A")
        self.memory_label = QLabel("Memory: N/A")
        
        status_layout.addWidget(QLabel("Status:"), 0, 0)
        status_layout.addWidget(self.status_label, 0, 1)
        status_layout.addWidget(QLabel("Models:"), 1, 0)
        status_layout.addWidget(self.models_label, 1, 1)
        status_layout.addWidget(QLabel("Accuracy:"), 2, 0)
        status_layout.addWidget(self.accuracy_label, 2, 1)
        status_layout.addWidget(QLabel("Memory:"), 3, 0)
        status_layout.addWidget(self.memory_label, 3, 1)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Tabs for different ML views
        tab_widget = QTabWidget()
        
        # System status tab
        self.system_status_tab = QWidget()
        system_status_layout = QVBoxLayout()
        
        system_refresh_btn = QPushButton("🔄 Refresh System Status")
        system_refresh_btn.clicked.connect(self.update_system_status)
        system_status_layout.addWidget(system_refresh_btn)
        
        self.system_status_text = QTextEdit()
        self.system_status_text.setReadOnly(True)
        system_status_layout.addWidget(self.system_status_text)
        
        self.system_status_tab.setLayout(system_status_layout)
        tab_widget.addTab(self.system_status_tab, "System Status")
        
        # Insights tab
        self.insights_tab = QWidget()
        insights_layout = QVBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh Insights")
        refresh_btn.clicked.connect(self.refresh_insights)
        insights_layout.addWidget(refresh_btn)
        
        self.insights_text = QTextEdit()
        self.insights_text.setReadOnly(True)
        insights_layout.addWidget(self.insights_text)
        
        self.insights_tab.setLayout(insights_layout)
        tab_widget.addTab(self.insights_tab, "System Insights")
        
        # Predictions tab
        self.predictions_tab = QWidget()
        predictions_layout = QVBoxLayout()
        
        predict_btn = QPushButton("🎯 Run Prediction Test")
        predict_btn.clicked.connect(self.run_prediction_test)
        predictions_layout.addWidget(predict_btn)
        
        self.predictions_text = QTextEdit()
        self.predictions_text.setReadOnly(True)
        predictions_layout.addWidget(self.predictions_text)
        
        self.predictions_tab.setLayout(predictions_layout)
        tab_widget.addTab(self.predictions_tab, "Predictions")
        
        # Model status tab
        self.models_tab = QWidget()
        models_layout = QVBoxLayout()
        
        # Training controls
        training_controls = QHBoxLayout()
        
        train_btn = QPushButton("🏋️ Train Models")
        train_btn.clicked.connect(self.train_models)
        training_controls.addWidget(train_btn)
        
        self.auto_train_checkbox = QCheckBox("Auto Training")
        self.auto_train_checkbox.setChecked(True)
        self.auto_train_checkbox.stateChanged.connect(self.toggle_auto_training)
        training_controls.addWidget(self.auto_train_checkbox)
        
        interval_label = QLabel("Interval (hrs):")
        training_controls.addWidget(interval_label)
        
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1, 168)
        self.interval_spinbox.setValue(24)
        self.interval_spinbox.valueChanged.connect(self.update_training_interval)
        training_controls.addWidget(self.interval_spinbox)
        
        models_layout.addLayout(training_controls)
        
        self.models_text = QTextEdit()
        self.models_text.setReadOnly(True)
        models_layout.addWidget(self.models_text)
        
        self.models_tab.setLayout(models_layout)
        tab_widget.addTab(self.models_tab, "Model Status")
        
        layout.addWidget(tab_widget)
        
        # Auto-refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)  # Update every 5 seconds
        
        self.setLayout(layout)
        
    def init_ml_engine(self):
        try:
            from ml.ml_engine import MLEngine
            self.ml_engine = MLEngine(self.db_manager)
            self.update_status()
        except Exception as e:
            self.status_label.setText(f"❌ Error: {e}")
            
    def update_status(self):
        if not self.ml_engine:
            return
            
        try:
            health = self.ml_engine.get_health_status()
            
            # Update status labels
            status = health.get('overall_health', 'Unknown')
            if status == 'Good':
                self.status_label.setText("✅ Operational")
            else:
                self.status_label.setText(f"⚠️ {status}")
                
            models_count = health.get('components', {}).get('models_loaded', 0)
            self.models_label.setText(f"Models: {models_count}")
            
            # Get accuracy from real models
            accuracy = self.ml_engine.get_prediction_accuracy()
            real_accuracies = [v for k, v in accuracy.items() if k.endswith('_accuracy') and v is not None]
            if real_accuracies:
                avg_accuracy = sum(real_accuracies) / len(real_accuracies)
                self.accuracy_label.setText(f"Accuracy: {avg_accuracy:.1%}")
            else:
                self.accuracy_label.setText("Accuracy: No training data")
            
            # Memory usage
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.memory_label.setText(f"Memory: {memory_mb:.1f} MB")
            
        except Exception as e:
            self.status_label.setText(f"❌ Error: {e}")
            
    def refresh_insights(self):
        if not self.ml_engine:
            self.insights_text.setText("ML Engine not available")
            return
            
        try:
            insights = self.ml_engine.get_system_wide_insights()
            
            output = "🤖 System-Wide ML Insights\n"
            output += "=" * 50 + "\n\n"
            
            if 'error' in insights:
                output += f"❌ Error: {insights['error']}\n"
            else:
                for facility, data in insights.items():
                    output += f"📊 {facility.upper()}\n"
                    if isinstance(data, dict):
                        health = data.get('health_score', 'N/A')
                        output += f"   Health: {health}%\n"
                        
                        recommendations = data.get('recommendations', [])
                        if recommendations:
                            output += f"   Recommendations: {len(recommendations)}\n"
                            for rec in recommendations[:3]:  # Show first 3
                                output += f"   • {rec}\n"
                    else:
                        output += f"   Status: {data}\n"
                    output += "\n"
                    
            self.insights_text.setText(output)
            
        except Exception as e:
            self.insights_text.setText(f"Error getting insights: {e}")
            
    def run_prediction_test(self):
        if not self.ml_engine:
            self.predictions_text.setText("ML Engine not available")
            return
            
        try:
            output = "🎯 ML Prediction Test Results\n"
            output += "=" * 50 + "\n\n"
            
            # Test failure prediction
            build_data = {
                'stage_count': 10,
                'avg_stage_duration': 300,
                'system_load': 0.7,
                'memory_usage': 0.8,
                'previous_failures': 1
            }
            
            prediction = self.ml_engine.predict_failure_risk(build_data)
            if prediction:
                output += "🚨 Failure Prediction:\n"
                output += f"   Risk Score: {prediction.get('risk_score', 0):.2f}\n"
                output += f"   Confidence: {prediction.get('confidence', 0):.2f}\n"
                recommendations = prediction.get('recommendations', [])
                if recommendations:
                    output += "   Recommendations:\n"
                    for rec in recommendations:
                        output += f"   • {rec}\n"
            else:
                output += "🚨 Failure Prediction: No risk detected\n"
                
            output += "\n"
            
            # Test performance optimization
            perf_data = {
                'build_duration': 7200,
                'cpu_cores': 4,
                'parallel_jobs': 2
            }
            
            optimization = self.ml_engine.optimize_build_config(perf_data)
            if optimization:
                output += "⚡ Performance Optimization:\n"
                output += f"   Improvement: {optimization.get('improvement_percent', 0):.1f}%\n"
                output += f"   Confidence: {optimization.get('confidence', 0):.2f}\n"
                changes = optimization.get('changes', [])
                if changes:
                    output += "   Suggested Changes:\n"
                    for change in changes[:3]:
                        output += f"   • {change.get('description', 'N/A')}\n"
            else:
                output += "⚡ Performance Optimization: No improvements suggested\n"
                
            output += "\n"
            
            # Test anomaly detection
            metrics = {
                'cpu_usage': 95,
                'memory_usage': 90,
                'disk_io': 600
            }
            
            anomalies = self.ml_engine.detect_anomalies(metrics)
            if anomalies:
                output += "🔍 Anomaly Detection:\n"
                output += f"   Anomaly Score: {anomalies.get('anomaly_score', 0):.2f}\n"
                output += f"   Severity: {anomalies.get('severity', 'normal')}\n"
                detected = anomalies.get('anomalies_detected', [])
                if detected:
                    output += "   Detected Issues:\n"
                    for anomaly in detected:
                        output += f"   • {anomaly.get('description', 'N/A')}\n"
            else:
                output += "🔍 Anomaly Detection: No anomalies detected\n"
                
            self.predictions_text.setText(output)
            
        except Exception as e:
            self.predictions_text.setText(f"Error running predictions: {e}")
            
    def train_models(self):
        if not self.ml_engine:
            self.models_text.setText("ML Engine not available")
            return
            
        try:
            output = "🏋️ Model Training Results\n"
            output += "=" * 50 + "\n\n"
            
            # Train models
            result = self.ml_engine.train_models()
            
            trained = result.get('trained_models', [])
            errors = result.get('errors', [])
            
            if trained:
                output += "✅ Successfully Trained Models:\n"
                for model in trained:
                    output += f"   • {model.get('model', 'Unknown')}\n"
                    if model.get('accuracy') is not None:
                        output += f"     Accuracy: {model.get('accuracy'):.2%}\n"
                    else:
                        output += f"     Accuracy: No training data\n"
                    output += f"     Samples: {model.get('samples_used', 0)}\n"
                    output += f"     Time: {model.get('training_time', 'N/A')}\n\n"
            
            if errors:
                output += "❌ Training Errors:\n"
                for error in errors:
                    output += f"   • {error}\n"
                output += "\n"
                
            # Get model status
            status = self.ml_engine.get_model_status()
            output += "📊 Model Status:\n"
            
            models = status.get('models', {})
            for model_name, model_info in models.items():
                output += f"   {model_name}:\n"
                output += f"     Loaded: {'✅' if model_info.get('loaded') else '❌'}\n"
                output += f"     Trained: {'✅' if model_info.get('trained') else '❌'}\n"
                if 'accuracy' in model_info:
                    if model_info['accuracy'] is not None:
                        output += f"     Accuracy: {model_info['accuracy']:.2%}\n"
                    else:
                        output += f"     Accuracy: No training data\n"
                output += "\n"
                
            self.models_text.setText(output)
            
        except Exception as e:
            self.models_text.setText(f"Error training models: {e}")
            
    def toggle_auto_training(self, state):
        if not self.ml_engine:
            return
        try:
            enabled = state == Qt.Checked
            self.ml_engine.configure_auto_training(auto_training_enabled=enabled)
        except Exception as e:
            print(f"Error toggling auto training: {e}")
            
    def update_training_interval(self, hours):
        if not self.ml_engine:
            return
        try:
            self.ml_engine.configure_auto_training(training_interval_hours=hours)
        except Exception as e:
            print(f"Error updating training interval: {e}")
    
    def update_system_status(self):
        """Update system status tab"""
        if not self.ml_engine:
            self.system_status_text.setText("ML Engine not available")
            return
            
        try:
            health = self.ml_engine.get_health_status()
            accuracy = self.ml_engine.get_prediction_accuracy()
            
            output = "🤖 ML System Status\n"
            output += "=" * 50 + "\n\n"
            
            output += f"Overall Health: {health.get('overall_health', 'Unknown')}\n"
            output += f"Database Connection: {health.get('database_connection', 'Unknown')}\n"
            output += f"Models Loaded: {health.get('components', {}).get('models_loaded', 0)}\n"
            output += f"Enabled Models: {', '.join(health.get('enabled_models', []))}\n\n"
            
            output += "Prediction Accuracy:\n"
            for key, value in accuracy.items():
                if key.endswith('_accuracy'):
                    model_name = key.replace('_accuracy', '').replace('_', ' ').title()
                    if value is not None:
                        output += f"  {model_name}: {value:.1%}\n"
                    else:
                        output += f"  {model_name}: No training data\n"
                elif key.endswith('_predictions'):
                    model_name = key.replace('_predictions', '').replace('_', ' ').title()
                    output += f"  {model_name} Predictions Made: {value}\n"
            
            if accuracy.get('data_source'):
                output += f"  Data Source: {accuracy.get('data_source')}\n"
            
            self.system_status_text.setText(output)
            
        except Exception as e:
            self.system_status_text.setText(f"Error updating system status: {e}")
    
    def update_insights(self):
        """Update insights tab"""
        self.refresh_insights()
    
    def update_predictions(self):
        """Update predictions tab"""
        self.run_prediction_test()
    
    def update_models(self):
        """Update models tab"""
        self.train_models()