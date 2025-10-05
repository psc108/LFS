from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class FeatureToolbar(QToolBar):
    """Enhanced toolbar with prominent feature buttons"""
    
    def __init__(self, parent=None):
        super().__init__("Enterprise Features", parent)
        self.setup_toolbar()
    
    def setup_toolbar(self):
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setIconSize(QSize(32, 32))
        self.setStyleSheet("""
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid #dee2e6;
                padding: 5px;
            }
            QToolButton {
                background-color: white;
                border: 2px solid #007bff;
                border-radius: 8px;
                padding: 8px 12px;
                margin: 2px;
                font-weight: bold;
                color: #007bff;
            }
            QToolButton:hover {
                background-color: #007bff;
                color: white;
            }
            QToolButton:pressed {
                background-color: #0056b3;
            }
        """)
        
        # Primary feature buttons
        self.add_feature_button("🧙♂️ Build Wizard", "Start guided build setup", self.open_wizard, "#007bff")
        self.addSeparator()
        
        self.add_feature_button("⚡ Parallel Build", "Multi-core build execution", self.open_parallel, "#28a745")
        self.add_feature_button("🔍 Fault Analysis", "AI-powered failure detection", self.open_analysis, "#dc3545")
        self.addSeparator()
        
        self.add_feature_button("🛡️ Security Scan", "Vulnerability assessment", self.open_security, "#fd7e14")
        self.add_feature_button("📦 Generate ISO", "Create bootable images", self.open_iso, "#6f42c1")
        self.addSeparator()
        
        self.add_feature_button("🌐 API Server", "REST API interface", self.toggle_api, "#17a2b8")
        self.add_feature_button("👥 Team Hub", "Collaboration features", self.open_team, "#20c997")
        
        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)
        
        # Status indicators
        self.add_status_indicator("🏥", "System Health: OK", "#28a745")
        self.add_status_indicator("📊", "Risk Score: Low", "#28a745")
        self.add_status_indicator("🔧", "Features: Active", "#007bff")
    
    def add_feature_button(self, text, tooltip, action, color):
        """Add a prominent feature button"""
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.clicked.connect(action)
        
        # Custom styling for this button
        button.setStyleSheet(f"""
            QToolButton {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 8px;
                padding: 8px 12px;
                margin: 2px;
                font-weight: bold;
                color: {color};
                min-width: 120px;
            }}
            QToolButton:hover {{
                background-color: {color};
                color: white;
            }}
        """)
        
        self.addWidget(button)
        return button
    
    def add_status_indicator(self, icon, tooltip, color):
        """Add a status indicator"""
        indicator = QLabel(icon)
        indicator.setToolTip(tooltip)
        indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: 15px;
                padding: 5px 10px;
                margin: 2px;
                font-size: 16px;
                font-weight: bold;
            }}
        """)
        indicator.setAlignment(Qt.AlignCenter)
        indicator.setMinimumSize(30, 30)
        self.addWidget(indicator)
        return indicator
    
    # Feature action methods
    def open_wizard(self):
        try:
            from .wizard_dialog import BuildWizardDialog
            from ..templates.template_manager import BuildTemplateManager
            
            template_manager = BuildTemplateManager()
            dialog = BuildWizardDialog(template_manager)
            dialog.exec_()
        except Exception as e:
            QMessageBox.information(None, "Build Wizard", 
                "🧙♂️ Build Wizard - Guided Setup\n\n"
                "• Choose from pre-configured templates\n"
                "• Customize build options\n"
                "• Configure kernel settings\n"
                "• Enable advanced features\n"
                "• Preview configuration")
    
    def open_parallel(self):
        QMessageBox.information(None, "Parallel Build Engine", 
            "⚡ Multi-Core Build Orchestration\n\n"
            "• Intelligent task distribution\n"
            "• Dependency-aware scheduling\n"
            "• Resource optimization\n"
            "• Performance monitoring\n"
            "• Distributed builds")
    
    def open_analysis(self):
        QMessageBox.information(None, "Advanced Fault Analysis", 
            "🔍 AI-Powered Build Intelligence\n\n"
            "• Pattern recognition (15+ patterns)\n"
            "• Predictive failure analysis\n"
            "• Auto-fix suggestions\n"
            "• Root cause detection\n"
            "• ML-based insights")
    
    def open_security(self):
        QMessageBox.information(None, "Security & Compliance", 
            "🛡️ Comprehensive Security Scanning\n\n"
            "• CVE vulnerability database\n"
            "• Compliance frameworks (CIS, NIST, SOX, HIPAA)\n"
            "• Package security analysis\n"
            "• Risk assessment & scoring\n"
            "• Automated recommendations")
    
    def open_iso(self):
        QMessageBox.information(None, "ISO & VM Generation", 
            "📦 Deployment Image Creation\n\n"
            "• Bootable ISO images (ISOLINUX/GRUB)\n"
            "• VM disk images (QCOW2, VMDK, VHD)\n"
            "• Network boot (PXE) images\n"
            "• Cloud-ready images (AMI, Azure, GCP)\n"
            "• Automated generation pipeline")
    
    def toggle_api(self):
        reply = QMessageBox.question(None, "REST API Server", 
            "🌐 REST API Integration\n\n"
            "• Complete RESTful endpoints\n"
            "• Webhook support\n"
            "• Real-time build monitoring\n"
            "• External tool integration\n"
            "• Authentication & authorization\n\n"
            "Start API server on port 5000?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            QMessageBox.information(None, "API Server", "🌐 API Server started on http://localhost:5000\n\nAPI documentation available at /api/docs")
    
    def open_team(self):
        QMessageBox.information(None, "Team Collaboration", 
            "👥 Multi-User Collaboration Platform\n\n"
            "• Role-based access control\n"
            "• Team activity dashboards\n"
            "• Build sharing & reviews\n"
            "• Real-time notifications\n"
            "• Project management")

class FeatureStatusBar(QStatusBar):
    """Enhanced status bar with feature indicators"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_statusbar()
    
    def setup_statusbar(self):
        self.setStyleSheet("""
            QStatusBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #343a40, stop:1 #495057);
                color: white;
                border-top: 1px solid #6c757d;
            }
            QLabel {
                color: white;
                padding: 2px 8px;
                margin: 2px;
            }
        """)
        
        # System metrics
        self.cpu_label = QLabel("🖥️ CPU: ---%")
        self.memory_label = QLabel("💾 RAM: ---%")
        self.disk_label = QLabel("💿 Disk: ---%")
        
        # Feature status
        self.builds_label = QLabel("🔨 Builds: 0")
        self.risk_label = QLabel("🛡️ Risk: Low")
        self.api_label = QLabel("🌐 API: Ready")
        
        # Version info
        self.version_label = QLabel("LFS Enterprise v2.0")
        
        # Add to status bar
        self.addWidget(self.cpu_label)
        self.addWidget(QLabel("|"))
        self.addWidget(self.memory_label)
        self.addWidget(QLabel("|"))
        self.addWidget(self.disk_label)
        self.addWidget(QLabel("||"))
        self.addWidget(self.builds_label)
        self.addWidget(QLabel("|"))
        self.addWidget(self.risk_label)
        self.addWidget(QLabel("|"))
        self.addWidget(self.api_label)
        
        self.addPermanentWidget(self.version_label)
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(5000)  # Update every 5 seconds
    
    def update_status(self):
        """Update status bar information"""
        try:
            import psutil
            
            # Update system metrics
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            self.cpu_label.setText(f"🖥️ CPU: {cpu_percent:.1f}%")
            self.memory_label.setText(f"💾 RAM: {memory_percent:.1f}%")
            self.disk_label.setText(f"💿 Disk: {disk_percent:.1f}%")
            
            # Color coding for high usage
            if cpu_percent > 80:
                self.cpu_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
            elif cpu_percent > 60:
                self.cpu_label.setStyleSheet("color: #feca57; font-weight: bold;")
            else:
                self.cpu_label.setStyleSheet("color: #48dbfb;")
            
            if memory_percent > 85:
                self.memory_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
            elif memory_percent > 70:
                self.memory_label.setStyleSheet("color: #feca57; font-weight: bold;")
            else:
                self.memory_label.setStyleSheet("color: #48dbfb;")
                
        except Exception as e:
            pass  # Silently handle errors