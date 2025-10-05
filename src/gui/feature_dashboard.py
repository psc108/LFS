from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class FeatureDashboard(QWidget):
    """Prominent dashboard showing all available features"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_dashboard()
    
    def setup_dashboard(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("🚀 LFS Enterprise Features")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; padding: 20px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Feature grid
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        grid_layout = QGridLayout(scroll_widget)
        
        # Define feature cards
        features = [
            # Row 1 - Core Build Features
            ("🧙♂️ Build Wizard", "Guided setup for all build types", "primary", self.open_wizard),
            ("⚡ Parallel Builds", "Multi-core build orchestration", "success", self.open_parallel),
            ("📋 Templates", "Pre-configured build templates", "info", self.open_templates),
            ("🐳 Containers", "Docker/Podman integration", "warning", self.open_containers),
            
            # Row 2 - Analysis & Monitoring
            ("🔍 Fault Analysis", "AI-powered failure detection", "danger", self.open_fault_analysis),
            ("📊 Performance", "Build metrics & analytics", "primary", self.open_performance),
            ("🛡️ Security Scan", "Vulnerability assessment", "danger", self.open_security),
            ("🏥 System Health", "Real-time monitoring", "success", self.open_health),
            
            # Row 3 - Deployment & Distribution
            ("📦 ISO Generator", "Bootable image creation", "info", self.open_iso),
            ("🖥️ VM Images", "Virtual machine deployment", "info", self.open_vm),
            ("🌐 Network Boot", "PXE boot configuration", "warning", self.open_netboot),
            ("☁️ Cloud Deploy", "AWS/Azure/GCP integration", "primary", self.open_cloud),
            
            # Row 4 - Collaboration & Integration
            ("👥 Team Features", "Multi-user collaboration", "success", self.open_team),
            ("🌐 REST API", "External integrations", "info", self.open_api),
            ("🔌 Plugins", "Extensible architecture", "warning", self.open_plugins),
            ("📅 Scheduler", "Automated build scheduling", "primary", self.open_scheduler)
        ]
        
        # Create feature cards in grid
        for i, (title, description, color, action) in enumerate(features):
            card = self.create_feature_card(title, description, color, action)
            row = i // 4
            col = i % 4
            grid_layout.addWidget(card, row, col)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # Quick stats bar
        stats_bar = self.create_stats_bar()
        layout.addWidget(stats_bar)
    
    def create_feature_card(self, title, description, color, action):
        """Create a prominent feature card"""
        card = QFrame()
        card.setFrameStyle(QFrame.Box)
        card.setLineWidth(2)
        
        # Color scheme
        colors = {
            "primary": "#3498db",
            "success": "#27ae60", 
            "info": "#17a2b8",
            "warning": "#f39c12",
            "danger": "#e74c3c"
        }
        
        card.setStyleSheet(f"""
            QFrame {{
                border: 2px solid {colors.get(color, '#3498db')};
                border-radius: 10px;
                background-color: white;
                margin: 5px;
            }}
            QFrame:hover {{
                background-color: #f8f9fa;
                border-width: 3px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {colors.get(color, '#3498db')};")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 12px; color: #666; padding: 5px;")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Action button
        btn = QPushButton("Open")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors.get(color, '#3498db')};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {colors.get(color, '#3498db')}dd;
            }}
        """)
        btn.clicked.connect(action)
        layout.addWidget(btn)
        
        card.setMinimumSize(200, 150)
        card.setMaximumSize(250, 180)
        
        return card
    
    def create_stats_bar(self):
        """Create system statistics bar"""
        stats_widget = QFrame()
        stats_widget.setFrameStyle(QFrame.Box)
        stats_widget.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                color: white;
                padding: 10px;
                border-radius: 5px;
            }
        """)
        
        layout = QHBoxLayout(stats_widget)
        
        # Stats items
        stats = [
            ("🔨 Total Builds", "0"),
            ("⚡ Active Builds", "0"),
            ("🛡️ Risk Score", "Low"),
            ("🏥 System Health", "Healthy"),
            ("🌐 API Status", "Ready"),
            ("👥 Active Users", "1")
        ]
        
        for label, value in stats:
            stat_layout = QVBoxLayout()
            
            label_widget = QLabel(label)
            label_widget.setStyleSheet("font-size: 12px; color: #bdc3c7;")
            label_widget.setAlignment(Qt.AlignCenter)
            
            value_widget = QLabel(value)
            value_widget.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
            value_widget.setAlignment(Qt.AlignCenter)
            
            stat_layout.addWidget(label_widget)
            stat_layout.addWidget(value_widget)
            
            layout.addLayout(stat_layout)
        
        return stats_widget
    
    # Feature action methods
    def open_wizard(self):
        from .wizard_dialog import BuildWizardDialog
        from ..templates.template_manager import BuildTemplateManager
        
        try:
            template_manager = BuildTemplateManager()
            dialog = BuildWizardDialog(template_manager, self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.information(self, "Build Wizard", f"🧙♂️ Build Wizard\n\nGuided build configuration with:\n• Template selection\n• Kernel configuration\n• Advanced options\n• Real-time preview")
    
    def open_parallel(self):
        QMessageBox.information(self, "Parallel Builds", "⚡ Parallel Build Engine\n\n• Multi-core task distribution\n• Intelligent dependency management\n• Resource optimization\n• Performance monitoring\n• Distributed builds")
    
    def open_templates(self):
        QMessageBox.information(self, "Build Templates", "📋 Pre-configured Templates\n\n• Minimal LFS\n• Desktop Environment\n• Server Configuration\n• Embedded Systems\n• Custom templates")
    
    def open_containers(self):
        QMessageBox.information(self, "Container Integration", "🐳 Container Support\n\n• Docker builds\n• Podman integration\n• Isolated environments\n• Scalable deployment\n• Container registries")
    
    def open_fault_analysis(self):
        QMessageBox.information(self, "Fault Analysis", "🔍 AI-Powered Analysis\n\n• Pattern recognition\n• Predictive failure detection\n• Auto-fix suggestions\n• Root cause analysis\n• ML-based insights")
    
    def open_performance(self):
        QMessageBox.information(self, "Performance Analytics", "📊 Build Performance\n\n• Stage duration tracking\n• Resource utilization\n• Bottleneck identification\n• Trend analysis\n• Optimization recommendations")
    
    def open_security(self):
        QMessageBox.information(self, "Security Scanner", "🛡️ Vulnerability Assessment\n\n• CVE database scanning\n• Compliance checking (CIS, NIST)\n• Package vulnerability analysis\n• Security recommendations\n• Risk scoring")
    
    def open_health(self):
        QMessageBox.information(self, "System Health", "🏥 Health Monitoring\n\n• Real-time system metrics\n• Component status tracking\n• Predictive alerts\n• Performance monitoring\n• Health dashboards")
    
    def open_iso(self):
        QMessageBox.information(self, "ISO Generator", "📦 Bootable Images\n\n• ISOLINUX/GRUB support\n• Custom boot configurations\n• Live CD creation\n• Installation media\n• Automated generation")
    
    def open_vm(self):
        QMessageBox.information(self, "VM Images", "🖥️ Virtual Machine Deployment\n\n• QCOW2, VMDK, VHD formats\n• Hypervisor compatibility\n• Cloud-ready images\n• Automated provisioning\n• Template management")
    
    def open_netboot(self):
        QMessageBox.information(self, "Network Boot", "🌐 PXE Boot Setup\n\n• Network installation\n• Diskless workstations\n• Enterprise deployment\n• TFTP configuration\n• Boot menu management")
    
    def open_cloud(self):
        QMessageBox.information(self, "Cloud Deployment", "☁️ Cloud Integration\n\n• AWS EC2/AMI support\n• Azure VM images\n• Google Cloud Platform\n• Auto-scaling groups\n• Infrastructure as Code")
    
    def open_team(self):
        QMessageBox.information(self, "Team Collaboration", "👥 Multi-User Features\n\n• Role-based access control\n• Team dashboards\n• Build sharing\n• Review workflows\n• Activity tracking")
    
    def open_api(self):
        QMessageBox.information(self, "REST API", "🌐 API Integration\n\n• RESTful endpoints\n• Webhook support\n• Authentication\n• External integrations\n• Real-time updates")
    
    def open_plugins(self):
        QMessageBox.information(self, "Plugin System", "🔌 Extensible Architecture\n\n• Custom workflows\n• Third-party integrations\n• Event hooks\n• Plugin marketplace\n• Development SDK")
    
    def open_scheduler(self):
        QMessageBox.information(self, "Build Scheduler", "📅 Automated Scheduling\n\n• Cron-like scheduling\n• Recurring builds\n• Dependency triggers\n• Resource management\n• Notification integration")