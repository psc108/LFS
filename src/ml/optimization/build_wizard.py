#!/usr/bin/env python3

import json
import logging
from typing import Dict, List, Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class MLBuildWizard(QDialog):
    """ML-integrated build configuration wizard"""
    
    def __init__(self, parent=None, db_manager=None, ml_engine=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.ml_engine = ml_engine
        self.optimizer = None
        
        if ml_engine and hasattr(ml_engine, 'build_optimizer'):
            self.optimizer = ml_engine.build_optimizer
        
        self.setWindowTitle("ML-Optimized Build Wizard")
        self.setModal(True)
        self.resize(800, 600)
        
        self.setup_ui()
        self.load_ml_recommendations()
    
    def setup_ui(self):
        """Setup the wizard UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("ML-Optimized Build Configuration Wizard")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(header)
        
        # Tabs for different configuration aspects
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # System Optimization Tab
        self.setup_system_tab()
        
        # Performance Prediction Tab
        self.setup_prediction_tab()
        
        # Advanced Settings Tab
        self.setup_advanced_tab()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("🔍 Analyze System")
        self.analyze_btn.clicked.connect(self.analyze_system)
        button_layout.addWidget(self.analyze_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.create_btn = QPushButton("Create Optimized Build")
        self.create_btn.clicked.connect(self.create_optimized_build)
        self.create_btn.setStyleSheet("font-weight: bold;")
        button_layout.addWidget(self.create_btn)
        
        layout.addLayout(button_layout)
    
    def setup_system_tab(self):
        """Setup system optimization tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # ML Recommendations Section
        ml_group = QGroupBox("🤖 ML Recommendations")
        ml_layout = QVBoxLayout(ml_group)
        
        self.ml_status = QLabel("Loading ML recommendations...")
        ml_layout.addWidget(self.ml_status)
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setMaximumHeight(150)
        self.recommendations_text.setReadOnly(True)
        ml_layout.addWidget(self.recommendations_text)
        
        layout.addWidget(ml_group)
        
        # System Configuration Section
        sys_group = QGroupBox("⚙️ System Configuration")
        sys_layout = QFormLayout(sys_group)
        
        self.parallel_jobs = QSpinBox()
        self.parallel_jobs.setRange(1, 16)
        self.parallel_jobs.setValue(2)
        sys_layout.addRow("Parallel Jobs:", self.parallel_jobs)
        
        self.memory_limit = QLineEdit("4G")
        sys_layout.addRow("Memory Limit:", self.memory_limit)
        
        self.io_scheduler = QComboBox()
        self.io_scheduler.addItems(["mq-deadline", "kyber", "bfq", "none"])
        sys_layout.addRow("I/O Scheduler:", self.io_scheduler)
        
        layout.addWidget(sys_group)
        
        # Performance History Section
        history_group = QGroupBox("📊 Performance History")
        history_layout = QVBoxLayout(history_group)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Config", "Duration", "Success Rate", "Trend"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setMaximumHeight(150)
        history_layout.addWidget(self.history_table)
        
        layout.addWidget(history_group)
        
        self.tabs.addTab(widget, "System Optimization")
    
    def setup_prediction_tab(self):
        """Setup performance prediction tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Prediction Results
        pred_group = QGroupBox("🔮 Performance Prediction")
        pred_layout = QVBoxLayout(pred_group)
        
        self.prediction_text = QTextEdit()
        self.prediction_text.setReadOnly(True)
        pred_layout.addWidget(self.prediction_text)
        
        layout.addWidget(pred_group)
        
        # Optimization Impact
        impact_group = QGroupBox("📈 Optimization Impact")
        impact_layout = QFormLayout(impact_group)
        
        self.baseline_duration = QLabel("--")
        impact_layout.addRow("Baseline Duration:", self.baseline_duration)
        
        self.predicted_duration = QLabel("--")
        impact_layout.addRow("Predicted Duration:", self.predicted_duration)
        
        self.improvement_percent = QLabel("--")
        impact_layout.addRow("Expected Improvement:", self.improvement_percent)
        
        self.confidence_level = QLabel("--")
        impact_layout.addRow("Confidence Level:", self.confidence_level)
        
        layout.addWidget(impact_group)
        
        # Stage Analysis
        stage_group = QGroupBox("🎯 Stage-Specific Optimizations")
        stage_layout = QVBoxLayout(stage_group)
        
        self.stage_table = QTableWidget()
        self.stage_table.setColumnCount(3)
        self.stage_table.setHorizontalHeaderLabels(["Stage", "Priority", "Recommendations"])
        self.stage_table.horizontalHeader().setStretchLastSection(True)
        stage_layout.addWidget(self.stage_table)
        
        layout.addWidget(stage_group)
        
        self.tabs.addTab(widget, "Performance Prediction")
    
    def setup_advanced_tab(self):
        """Setup advanced settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Build Configuration
        config_group = QGroupBox("🔧 Build Configuration")
        config_layout = QFormLayout(config_group)
        
        self.config_name = QLineEdit()
        self.config_name.setPlaceholderText("Enter configuration name")
        config_layout.addRow("Configuration Name:", self.config_name)
        
        self.build_type = QComboBox()
        self.build_type.addItems(["Standard LFS", "Minimal LFS", "Desktop LFS", "Server LFS"])
        config_layout.addRow("Build Type:", self.build_type)
        
        self.optimization_level = QComboBox()
        self.optimization_level.addItems(["Conservative", "Balanced", "Aggressive"])
        self.optimization_level.setCurrentText("Balanced")
        config_layout.addRow("Optimization Level:", self.optimization_level)
        
        layout.addWidget(config_group)
        
        # Advanced Options
        advanced_group = QGroupBox("⚡ Advanced Options")
        advanced_layout = QVBoxLayout(advanced_group)
        
        self.enable_ccache = QCheckBox("Enable ccache for faster rebuilds")
        advanced_layout.addWidget(self.enable_ccache)
        
        self.enable_tmpfs = QCheckBox("Use tmpfs for temporary files")
        advanced_layout.addWidget(self.enable_tmpfs)
        
        self.enable_lto = QCheckBox("Enable Link Time Optimization (LTO)")
        advanced_layout.addWidget(self.enable_lto)
        
        layout.addWidget(advanced_group)
        
        # Export Options
        export_group = QGroupBox("💾 Export Options")
        export_layout = QVBoxLayout(export_group)
        
        export_btn_layout = QHBoxLayout()
        
        self.export_json_btn = QPushButton("Export as JSON")
        self.export_json_btn.clicked.connect(self.export_json)
        export_btn_layout.addWidget(self.export_json_btn)
        
        self.export_yaml_btn = QPushButton("Export as YAML")
        self.export_yaml_btn.clicked.connect(self.export_yaml)
        export_btn_layout.addWidget(self.export_yaml_btn)
        
        export_layout.addLayout(export_btn_layout)
        
        layout.addWidget(export_group)
        
        self.tabs.addTab(widget, "Advanced Settings")
    
    def load_ml_recommendations(self):
        """Load ML recommendations"""
        if not self.optimizer:
            self.ml_status.setText("❌ ML optimizer not available")
            return
        
        try:
            # Get system recommendations
            job_rec = self.optimizer.recommend_parallel_jobs()
            
            if "error" not in job_rec:
                # Update UI with recommendations
                self.parallel_jobs.setValue(job_rec.get("recommended_jobs", 2))
                
                # Display real system analysis
                rec_text = f"Real System Analysis:\n"
                rec_text += f"• CPUs: {job_rec.get('system_cpus', 'Detecting...')}\n"
                rec_text += f"• Memory: {job_rec.get('system_memory_gb', 'Detecting...')} GB\n"
                rec_text += f"• Recommended Jobs: {job_rec.get('recommended_jobs', 'Calculating...')}\n"
                rec_text += f"• Analysis Method: {job_rec.get('analysis_method', 'Real-time system analysis')}\n"
                rec_text += f"• Data Points: {job_rec.get('data_points', 0)} builds analyzed\n"
                rec_text += f"• Reasoning: {job_rec.get('reasoning', 'Analyzing system capabilities...')}"
                
                self.recommendations_text.setText(rec_text)
                self.ml_status.setText("✅ Real ML analysis completed")
            else:
                self.ml_status.setText(f"⚠️ ML error: {job_rec['error']}")
                
        except Exception as e:
            self.ml_status.setText(f"❌ Error loading ML recommendations: {e}")
    
    def analyze_system(self):
        """Analyze system and update predictions"""
        if not self.optimizer:
            QMessageBox.warning(self, "Warning", "ML optimizer not available")
            return
        
        try:
            # Get optimized configuration
            config = self.optimizer.optimize_build_configuration()
            
            if "error" in config:
                QMessageBox.warning(self, "Error", f"Analysis failed: {config['error']}")
                return
            
            # Update system optimization
            sys_opt = config.get("system_optimization", {})
            self.parallel_jobs.setValue(sys_opt.get("parallel_jobs", 2))
            
            memory_alloc = sys_opt.get("memory_allocation", {})
            if "build_memory_limit" in memory_alloc:
                self.memory_limit.setText(memory_alloc["build_memory_limit"])
            
            io_opt = sys_opt.get("io_optimization", {})
            if "io_scheduler" in io_opt:
                scheduler = io_opt["io_scheduler"]
                index = self.io_scheduler.findText(scheduler)
                if index >= 0:
                    self.io_scheduler.setCurrentIndex(index)
            
            # Update performance prediction
            perf_pred = config.get("performance_prediction", {})
            if "baseline_duration" in perf_pred:
                self.baseline_duration.setText(f"{perf_pred['baseline_duration']:.0f} seconds")
            if "predicted_duration" in perf_pred:
                self.predicted_duration.setText(f"{perf_pred['predicted_duration']:.0f} seconds")
            if "improvement_percent" in perf_pred:
                self.improvement_percent.setText(f"{perf_pred['improvement_percent']}%")
            if "confidence" in perf_pred:
                self.confidence_level.setText(perf_pred["confidence"].title())
            
            # Update stage optimizations
            stage_opt = config.get("stage_optimization", {})
            self.update_stage_table(stage_opt)
            
            # Update recommendations with real analysis data
            recommendations = config.get("recommendations", [])
            if recommendations:
                rec_text = "Real ML Analysis Results:\n"
                for i, rec in enumerate(recommendations, 1):
                    rec_text += f"{i}. {rec}\n"
                
                # Add analysis metadata
                perf_pred = config.get("performance_prediction", {})
                if "data_points" in perf_pred:
                    rec_text += f"\nAnalysis based on {perf_pred['data_points']} actual builds"
                
                self.prediction_text.setText(rec_text)
            
            QMessageBox.information(self, "Success", "System analysis completed!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Analysis failed: {e}")
    
    def update_stage_table(self, stage_optimizations: Dict):
        """Update stage optimization table"""
        self.stage_table.setRowCount(len(stage_optimizations))
        
        for row, (stage_name, opt_data) in enumerate(stage_optimizations.items()):
            self.stage_table.setItem(row, 0, QTableWidgetItem(stage_name))
            self.stage_table.setItem(row, 1, QTableWidgetItem(opt_data.get("priority", "medium")))
            
            recommendations = opt_data.get("recommendations", [])
            rec_text = "; ".join(recommendations)
            self.stage_table.setItem(row, 2, QTableWidgetItem(rec_text))
    
    def create_optimized_build(self):
        """Create optimized build configuration"""
        try:
            config_name = self.config_name.text().strip()
            if not config_name:
                config_name = f"ml_optimized_{QDateTime.currentDateTime().toString('yyyyMMdd_hhmmss')}"
            
            # Gather configuration
            config = {
                "name": config_name,
                "type": self.build_type.currentText(),
                "optimization_level": self.optimization_level.currentText(),
                "system": {
                    "parallel_jobs": self.parallel_jobs.value(),
                    "memory_limit": self.memory_limit.text(),
                    "io_scheduler": self.io_scheduler.currentText()
                },
                "advanced": {
                    "ccache": self.enable_ccache.isChecked(),
                    "tmpfs": self.enable_tmpfs.isChecked(),
                    "lto": self.enable_lto.isChecked()
                },
                "ml_generated": True,
                "created_at": QDateTime.currentDateTime().toString(Qt.ISODate)
            }
            
            # Save configuration (this would integrate with the build system)
            self.save_configuration(config)
            
            QMessageBox.information(self, "Success", f"Optimized build configuration '{config_name}' created!")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create configuration: {e}")
    
    def save_configuration(self, config: Dict):
        """Start actual ML-optimized build"""
        try:
            # Get build engine from parent
            build_engine = None
            if self.parent() and hasattr(self.parent(), 'build_engine'):
                build_engine = self.parent().build_engine
            
            if not build_engine:
                logging.error("Build engine not available")
                return None
            
            # Generate LFS build configuration with ML optimizations
            build_id = f"ml_build_{QDateTime.currentDateTime().toString('yyyyMMdd_hhmmss')}"
            parallel_jobs = config['system']['parallel_jobs']
            
            config_content = f"""# ML-Optimized LFS Build Configuration
# Generated by ML Build Wizard
# Build ID: {build_id}
# Optimization Level: {config['optimization_level']}

name: {config['name']}
version: '12.4'
parallel_jobs: {parallel_jobs}
build_type: ml_optimized_lfs
ml_generated: true
stages:
  - name: prepare_host
    order: 1
    command: |
      echo "=== ML-Optimized LFS Host Preparation ==="
      export LFS=/mnt/lfs
      export MAKEFLAGS="-j{parallel_jobs}"
      bash scripts/prepare_host.sh
    dependencies: []
  - name: download_sources
    order: 2
    command: |
      echo "=== ML-Optimized Source Downloads ==="
      export LFS=/mnt/lfs
      bash scripts/download_sources.sh
    dependencies: [prepare_host]
  - name: build_toolchain
    order: 3
    command: |
      echo "=== ML-Optimized Toolchain Build ==="
      export LFS=/mnt/lfs
      export MAKEFLAGS="-j{parallel_jobs}"
      bash scripts/build_toolchain.sh
    dependencies: [download_sources]
  - name: build_final_system
    order: 4
    command: |
      echo "=== ML-Optimized Final System ==="
      export LFS=/mnt/lfs
      export MAKEFLAGS="-j{parallel_jobs}"
      bash scripts/build_final_system.sh
    dependencies: [build_toolchain]
"""
            
            # Save config to repository
            repo_manager = getattr(self.parent(), 'repo_manager', None)
            if repo_manager:
                config_path = repo_manager.add_build_config(build_id, config_content)
            else:
                # Fallback: save to temp file
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write(config_content)
                    config_path = f.name
            
            # Always ask for sudo password for LFS builds
            password, ok = QInputDialog.getText(
                self, 
                'Sudo Password Required', 
                f'LFS builds require sudo access for directory setup and permissions.\n\nEnter your sudo password:',
                QLineEdit.Password
            )
            
            if ok and password:
                build_engine.set_sudo_password(password)
                logging.info(f"🔐 Sudo password provided for ML-optimized LFS build")
            else:
                reply = QMessageBox.question(
                    self, 'Continue Without Sudo?', 
                    'No sudo password provided. Build will likely fail due to permission issues.\n\nContinue anyway?',
                    QMessageBox.Yes | QMessageBox.No, 
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return None
                logging.warning(f"⚠️ Continuing ML build without sudo password - build may fail")
            
            # Start the build
            actual_build_id = build_engine.start_build(config_path, config['name'])
            
            # Activate monitoring in parent window
            if self.parent():
                parent = self.parent()
                parent.current_build_id = actual_build_id
                parent.build_id_label.setText(f"Build ID: {actual_build_id}")
                parent.build_status_label.setText("Status: Running (ML-Optimized)")
                parent.progress_bar.setValue(0)
                parent.cancel_build_btn.setEnabled(True)
                parent.force_cancel_btn.setEnabled(True)
                
                # Initialize detailed logs like regular wizard
                if hasattr(parent, 'logs_text'):
                    sudo_status = "✅ Provided" if build_engine.sudo_password else "❌ NOT PROVIDED"
                    parent.logs_text.setPlainText(f"🚀 ML-Optimized LFS Build {actual_build_id} started\n"
                                                 f"Configuration: {config['name']}\n"
                                                 f"Type: {config['type']}\n"
                                                 f"Optimization Level: {config['optimization_level']}\n"
                                                 f"Parallel Jobs: {config['system']['parallel_jobs']}\n"
                                                 f"Memory Limit: {config['system']['memory_limit']}\n"
                                                 f"Configuration File: {config_path}\n"
                                                 f"Sudo Password: {sudo_status}\n"
                                                 f"\n🤖 This is an ML-optimized build with intelligent resource allocation!\n"
                                                 f"\n📋 Live logs will appear below as build progresses...\n")
                
                # Start live monitoring
                if hasattr(parent, 'start_live_log_monitoring'):
                    parent.start_live_log_monitoring(actual_build_id)
                
                # Initial log refresh
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(1000, parent.refresh_build_logs)
                
                # Refresh builds table
                if hasattr(parent, 'refresh_builds'):
                    parent.refresh_builds()
            
            logging.info(f"ML-optimized build started: {actual_build_id}")
            return actual_build_id
            
        except Exception as e:
            logging.error(f"Failed to start ML build: {e}")
            return None
    
    def export_json(self):
        """Export configuration as JSON"""
        try:
            config = self.get_current_config()
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export JSON Configuration", 
                f"{config['name']}.json", "JSON Files (*.json)"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                QMessageBox.information(self, "Success", f"Configuration exported to {filename}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {e}")
    
    def export_yaml(self):
        """Export configuration as YAML"""
        try:
            import yaml
            config = self.get_current_config()
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export YAML Configuration", 
                f"{config['name']}.yaml", "YAML Files (*.yaml)"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                QMessageBox.information(self, "Success", f"Configuration exported to {filename}")
                
        except ImportError:
            QMessageBox.warning(self, "Warning", "PyYAML not installed. Cannot export YAML.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {e}")
    
    def get_current_config(self) -> Dict:
        """Get current configuration from UI with real ML analysis data"""
        config_name = self.config_name.text().strip()
        if not config_name:
            config_name = f"ml_optimized_{QDateTime.currentDateTime().toString('yyyyMMdd_hhmmss')}"
        
        # Get real system info for configuration
        import psutil
        system_info = {
            "cpu_count": psutil.cpu_count(logical=True),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 1)
        }
        
        return {
            "name": config_name,
            "type": self.build_type.currentText(),
            "optimization_level": self.optimization_level.currentText(),
            "system": {
                "parallel_jobs": self.parallel_jobs.value(),
                "memory_limit": self.memory_limit.text(),
                "io_scheduler": self.io_scheduler.currentText(),
                "detected_cpus": system_info["cpu_count"],
                "detected_memory_gb": system_info["memory_gb"],
                "available_disk_gb": system_info["disk_free_gb"]
            },
            "advanced": {
                "ccache": self.enable_ccache.isChecked(),
                "tmpfs": self.enable_tmpfs.isChecked(),
                "lto": self.enable_lto.isChecked()
            },
            "ml_generated": True,
            "ml_analysis_timestamp": QDateTime.currentDateTime().toString(Qt.ISODate),
            "real_system_analysis": True,
            "created_at": QDateTime.currentDateTime().toString(Qt.ISODate)
        }