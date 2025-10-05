from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import yaml
from typing import Dict, List

class BuildWizardDialog(QDialog):
    def __init__(self, template_manager, parent=None):
        super().__init__(parent)
        self.template_manager = template_manager
        self.config_data = {}
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("LFS Build Wizard")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # Create wizard
        self.wizard = QStackedWidget()
        
        # Pages
        self.welcome_page = self.create_welcome_page()
        self.template_page = self.create_template_page()
        self.config_page = self.create_config_page()
        self.summary_page = self.create_summary_page()
        
        self.wizard.addWidget(self.welcome_page)
        self.wizard.addWidget(self.template_page)
        self.wizard.addWidget(self.config_page)
        self.wizard.addWidget(self.summary_page)
        
        layout.addWidget(self.wizard)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.back_btn = QPushButton("< Back")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setEnabled(False)
        
        self.next_btn = QPushButton("Next >")
        self.next_btn.clicked.connect(self.go_next)
        
        self.finish_btn = QPushButton("Finish")
        self.finish_btn.clicked.connect(self.finish_wizard)
        self.finish_btn.setVisible(False)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        nav_layout.addWidget(self.back_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.cancel_btn)
        nav_layout.addWidget(self.next_btn)
        nav_layout.addWidget(self.finish_btn)
        
        layout.addLayout(nav_layout)
        self.setLayout(layout)
        
        self.current_page = 0
    
    def create_welcome_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Welcome to LFS Build Wizard")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        layout.addSpacing(20)
        
        # Description
        desc = QLabel("""
This wizard will guide you through creating a customized Linux From Scratch build configuration.

You'll be able to:
• Choose from pre-configured templates
• Customize build options
• Set optimization preferences
• Configure target architecture
• Review your configuration before starting

Click Next to begin.
        """)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 14px; line-height: 1.5;")
        layout.addWidget(desc)
        
        layout.addStretch()
        
        # Features overview
        features_group = QGroupBox("What's Included")
        features_layout = QVBoxLayout()
        
        features = [
            "✓ Complete LFS 12.4 build automation",
            "✓ Multiple build templates (Minimal, Desktop, Server)",
            "✓ Automated dependency management",
            "✓ Real-time build monitoring",
            "✓ Git integration with automatic branching",
            "✓ Advanced fault analysis and recovery"
        ]
        
        for feature in features:
            label = QLabel(feature)
            label.setStyleSheet("color: #27ae60; font-weight: bold;")
            features_layout.addWidget(label)
        
        features_group.setLayout(features_layout)
        layout.addWidget(features_group)
        
        page.setLayout(layout)
        return page
    
    def create_template_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Choose Build Template")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)
        
        # Template selection
        self.template_list = QListWidget()
        self.template_list.itemClicked.connect(self.on_template_selected)
        
        templates = self.template_manager.list_templates()
        for template in templates:
            item = QListWidgetItem()
            item.setText(f"{template['name']}")
            item.setData(Qt.UserRole, template)
            
            # Add description as tooltip
            item.setToolTip(template.get('description', ''))
            
            self.template_list.addItem(item)
        
        layout.addWidget(self.template_list)
        
        # Template details
        self.template_details = QTextEdit()
        self.template_details.setMaximumHeight(150)
        self.template_details.setReadOnly(True)
        layout.addWidget(QLabel("Template Details:"))
        layout.addWidget(self.template_details)
        
        page.setLayout(layout)
        return page
    
    def create_config_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Customize Configuration")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)
        
        # Configuration options
        config_scroll = QScrollArea()
        config_widget = QWidget()
        config_layout = QVBoxLayout()
        
        # Build name
        name_group = QGroupBox("Build Information")
        name_layout = QFormLayout()
        
        self.build_name_edit = QLineEdit()
        self.build_name_edit.setText("My LFS Build")
        name_layout.addRow("Build Name:", self.build_name_edit)
        
        self.build_desc_edit = QTextEdit()
        self.build_desc_edit.setMaximumHeight(60)
        name_layout.addRow("Description:", self.build_desc_edit)
        
        name_group.setLayout(name_layout)
        config_layout.addWidget(name_group)
        
        # Architecture
        arch_group = QGroupBox("Target Architecture")
        arch_layout = QVBoxLayout()
        
        self.arch_combo = QComboBox()
        self.arch_combo.addItems(["x86_64", "i686", "arm64", "armhf"])
        arch_layout.addWidget(self.arch_combo)
        
        arch_group.setLayout(arch_layout)
        config_layout.addWidget(arch_group)
        
        # Optimization
        opt_group = QGroupBox("Optimization")
        opt_layout = QVBoxLayout()
        
        self.opt_size_radio = QRadioButton("Optimize for size")
        self.opt_speed_radio = QRadioButton("Optimize for performance")
        self.opt_balanced_radio = QRadioButton("Balanced optimization")
        self.opt_balanced_radio.setChecked(True)
        
        opt_layout.addWidget(self.opt_size_radio)
        opt_layout.addWidget(self.opt_speed_radio)
        opt_layout.addWidget(self.opt_balanced_radio)
        
        opt_group.setLayout(opt_layout)
        config_layout.addWidget(opt_group)
        
        # Kernel Configuration
        kernel_group = QGroupBox("Kernel Configuration")
        kernel_layout = QVBoxLayout()
        
        self.kernel_config_check = QCheckBox("Configure kernel options")
        self.kernel_config_check.toggled.connect(self.toggle_kernel_config)
        
        self.kernel_config_btn = QPushButton("Open Kernel Configuration")
        self.kernel_config_btn.clicked.connect(self.open_kernel_config)
        self.kernel_config_btn.setEnabled(False)
        
        self.kernel_preset_combo = QComboBox()
        self.kernel_preset_combo.addItems(["Default", "Minimal", "Desktop", "Server", "Performance"])
        self.kernel_preset_combo.setEnabled(False)
        
        kernel_layout.addWidget(self.kernel_config_check)
        kernel_layout.addWidget(QLabel("Kernel Preset:"))
        kernel_layout.addWidget(self.kernel_preset_combo)
        kernel_layout.addWidget(self.kernel_config_btn)
        
        kernel_group.setLayout(kernel_layout)
        config_layout.addWidget(kernel_group)
        
        # Advanced options
        adv_group = QGroupBox("Advanced Options")
        adv_layout = QVBoxLayout()
        
        self.parallel_builds_check = QCheckBox("Enable parallel builds")
        self.parallel_builds_check.setChecked(True)
        
        self.debug_symbols_check = QCheckBox("Include debug symbols")
        
        self.fault_analysis_check = QCheckBox("Enable advanced fault analysis")
        self.fault_analysis_check.setChecked(True)
        
        self.custom_cflags_check = QCheckBox("Use custom CFLAGS")
        self.custom_cflags_edit = QLineEdit()
        self.custom_cflags_edit.setPlaceholderText("-O2 -march=native")
        self.custom_cflags_edit.setEnabled(False)
        
        self.custom_cflags_check.toggled.connect(self.custom_cflags_edit.setEnabled)
        
        adv_layout.addWidget(self.parallel_builds_check)
        adv_layout.addWidget(self.debug_symbols_check)
        adv_layout.addWidget(self.fault_analysis_check)
        adv_layout.addWidget(self.custom_cflags_check)
        adv_layout.addWidget(self.custom_cflags_edit)
        
        adv_group.setLayout(adv_layout)
        config_layout.addWidget(adv_group)
        
        config_widget.setLayout(config_layout)
        config_scroll.setWidget(config_widget)
        config_scroll.setWidgetResizable(True)
        
        layout.addWidget(config_scroll)
        
        page.setLayout(layout)
        return page
    
    def create_summary_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Configuration Summary")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)
        
        # Summary display
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)
        
        # Final options
        final_group = QGroupBox("Final Options")
        final_layout = QVBoxLayout()
        
        self.save_config_check = QCheckBox("Save configuration to repository")
        self.save_config_check.setChecked(True)
        
        self.start_build_check = QCheckBox("Start build immediately")
        self.start_build_check.setChecked(True)
        
        final_layout.addWidget(self.save_config_check)
        final_layout.addWidget(self.start_build_check)
        
        final_group.setLayout(final_layout)
        layout.addWidget(final_group)
        
        page.setLayout(layout)
        return page
    
    def on_template_selected(self, item):
        template = item.data(Qt.UserRole)
        
        details = f"""
Template: {template['name']}
Category: {template.get('category', 'Unknown')}
Description: {template.get('description', 'No description available')}

Configuration:
- Architecture: {template['config'].get('target_arch', 'x86_64')}
- Optimization: {template['config'].get('optimization', 'balanced')}
- Stages: {len(template['config'].get('stages', []))}
        """
        
        self.template_details.setPlainText(details.strip())
        self.selected_template = template
    
    def go_next(self):
        if self.current_page < 3:
            if self.current_page == 1:  # Template page
                if not hasattr(self, 'selected_template'):
                    QMessageBox.warning(self, "Selection Required", "Please select a template to continue.")
                    return
            
            self.current_page += 1
            self.wizard.setCurrentIndex(self.current_page)
            
            if self.current_page == 3:  # Summary page
                self.update_summary()
                self.next_btn.setVisible(False)
                self.finish_btn.setVisible(True)
            
            self.back_btn.setEnabled(True)
    
    def go_back(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.wizard.setCurrentIndex(self.current_page)
            
            if self.current_page == 0:
                self.back_btn.setEnabled(False)
            
            if self.current_page < 3:
                self.next_btn.setVisible(True)
                self.finish_btn.setVisible(False)
    
    def toggle_kernel_config(self, enabled):
        self.kernel_config_btn.setEnabled(enabled)
        self.kernel_preset_combo.setEnabled(enabled)
    
    def open_kernel_config(self):
        try:
            from .kernel_config_dialog import KernelConfigDialog
            from ..config.settings_manager import SettingsManager
            settings = SettingsManager()
            dialog = KernelConfigDialog(settings, self)
            if dialog.exec_() == QDialog.Accepted:
                self.kernel_config_data = dialog.get_config()
        except (ImportError, Exception) as e:
            QMessageBox.information(self, "Info", "Kernel configuration will be available in the main interface")
            print(f"Kernel config error: {e}")
    
    def update_summary(self):
        # Collect configuration
        optimization = "size" if self.opt_size_radio.isChecked() else \
                      "performance" if self.opt_speed_radio.isChecked() else "balanced"
        
        config = {
            'name': self.build_name_edit.text(),
            'description': self.build_desc_edit.toPlainText(),
            'template': self.selected_template['name'],
            'target_arch': self.arch_combo.currentText(),
            'optimization': optimization,
            'parallel_builds': self.parallel_builds_check.isChecked(),
            'debug_symbols': self.debug_symbols_check.isChecked(),
            'fault_analysis': self.fault_analysis_check.isChecked(),
            'kernel_config': self.kernel_config_check.isChecked(),
            'kernel_preset': self.kernel_preset_combo.currentText() if self.kernel_config_check.isChecked() else None,
            'custom_cflags': self.custom_cflags_edit.text() if self.custom_cflags_check.isChecked() else None
        }
        
        self.config_data = config
        
        # Generate summary text
        summary = f"""
Build Configuration Summary:

Name: {config['name']}
Template: {config['template']}
Architecture: {config['target_arch']}
Optimization: {config['optimization']}

Options:
• Parallel builds: {'Enabled' if config['parallel_builds'] else 'Disabled'}
• Debug symbols: {'Included' if config['debug_symbols'] else 'Not included'}
• Fault analysis: {'Enabled' if config['fault_analysis'] else 'Disabled'}
• Kernel config: {'Custom' if config['kernel_config'] else 'Default'}
• Kernel preset: {config['kernel_preset'] or 'Default'}
• Custom CFLAGS: {config['custom_cflags'] or 'None'}

Description:
{config['description'] or 'No description provided'}

The configuration will be saved to the repository and can be used to start builds.
        """
        
        self.summary_text.setPlainText(summary.strip())
    
    def finish_wizard(self):
        try:
            # Generate YAML configuration
            customizations = {
                'name': self.config_data['name'],
                'target_arch': self.config_data['target_arch'],
                'optimization': self.config_data['optimization']
            }
            
            config_yaml = self.template_manager.generate_config_from_template(
                self.selected_template['id'], 
                customizations
            )
            
            self.generated_config = config_yaml
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate configuration: {str(e)}")
    
    def get_config(self):
        return getattr(self, 'generated_config', ''), self.config_data