from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import json
import os
from datetime import datetime
from typing import Dict, List

class TagTemplateDialog(QDialog):
    """Dialog for managing tag templates"""
    
    def __init__(self, templates_file, parent=None):
        super().__init__(parent)
        self.templates_file = templates_file
        self.templates = self.load_templates()
        self.setup_ui()
        self.load_template_list()
    
    def setup_ui(self):
        self.setWindowTitle("Tag Templates")
        self.setModal(True)
        self.resize(700, 500)
        
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("Manage Tag Templates")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header_label)
        
        # Template list
        list_layout = QHBoxLayout()
        
        # Left side - template list
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Templates:"))
        
        self.template_list = QListWidget()
        self.template_list.itemClicked.connect(self.on_template_selected)
        left_layout.addWidget(self.template_list)
        
        # Template actions
        template_actions = QHBoxLayout()
        
        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self.new_template)
        template_actions.addWidget(self.new_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_template)
        self.delete_btn.setEnabled(False)
        template_actions.addWidget(self.delete_btn)
        
        left_layout.addLayout(template_actions)
        list_layout.addLayout(left_layout)
        
        # Right side - template editor
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Template Editor:"))
        
        # Template name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_template_changed)
        name_layout.addWidget(self.name_edit)
        right_layout.addLayout(name_layout)
        
        # Template pattern
        pattern_layout = QVBoxLayout()
        pattern_layout.addWidget(QLabel("Tag Pattern:"))
        self.pattern_edit = QLineEdit()
        self.pattern_edit.textChanged.connect(self.on_template_changed)
        self.pattern_edit.setPlaceholderText("e.g., v{version}-{date}")
        pattern_layout.addWidget(self.pattern_edit)
        
        # Variables help
        help_text = QLabel("Available variables: {version}, {date}, {time}, {build_id}, {branch}, {commit_short}")
        help_text.setStyleSheet("color: #666; font-size: 10px;")
        pattern_layout.addWidget(help_text)
        right_layout.addLayout(pattern_layout)
        
        # Message template
        msg_layout = QVBoxLayout()
        msg_layout.addWidget(QLabel("Message Template:"))
        self.message_edit = QTextEdit()
        self.message_edit.textChanged.connect(self.on_template_changed)
        self.message_edit.setMaximumHeight(100)
        self.message_edit.setPlaceholderText("Tag message template...")
        msg_layout.addWidget(self.message_edit)
        right_layout.addLayout(msg_layout)
        
        # Preview
        preview_layout = QVBoxLayout()
        preview_layout.addWidget(QLabel("Preview:"))
        self.preview_label = QLabel("Select or create a template to see preview")
        self.preview_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc;")
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label)
        right_layout.addLayout(preview_layout)
        
        # Save button
        self.save_btn = QPushButton("Save Template")
        self.save_btn.clicked.connect(self.save_current_template)
        self.save_btn.setEnabled(False)
        right_layout.addWidget(self.save_btn)
        
        list_layout.addLayout(right_layout)
        layout.addLayout(list_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
        # Track changes
        self.current_template = None
        self.template_changed = False
    
    def load_templates(self) -> Dict:
        """Load templates from file"""
        if os.path.exists(self.templates_file):
            try:
                with open(self.templates_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default templates
        return {
            "Release": {
                "pattern": "v{version}",
                "message": "Release version {version}\\n\\nBuild: {build_id}\\nBranch: {branch}\\nDate: {date}"
            },
            "Build": {
                "pattern": "build-{build_id}-{date}",
                "message": "Build {build_id}\\n\\nCreated: {date} {time}\\nBranch: {branch}\\nCommit: {commit_short}"
            },
            "Milestone": {
                "pattern": "milestone-{version}",
                "message": "Milestone {version}\\n\\nAchieved on {date}\\nBranch: {branch}"
            }
        }
    
    def save_templates(self):
        """Save templates to file"""
        try:
            os.makedirs(os.path.dirname(self.templates_file), exist_ok=True)
            with open(self.templates_file, 'w') as f:
                json.dump(self.templates, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save templates: {str(e)}")
    
    def load_template_list(self):
        """Load template list"""
        self.template_list.clear()
        for name in sorted(self.templates.keys()):
            self.template_list.addItem(name)
    
    def on_template_selected(self, item):
        """Handle template selection"""
        if self.template_changed and self.current_template:
            reply = QMessageBox.question(self, 'Unsaved Changes', 
                                       'Save changes to current template?',
                                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.save_current_template()
            elif reply == QMessageBox.Cancel:
                return
        
        template_name = item.text()
        self.current_template = template_name
        template = self.templates[template_name]
        
        self.name_edit.setText(template_name)
        self.pattern_edit.setText(template['pattern'])
        self.message_edit.setPlainText(template['message'])
        
        self.delete_btn.setEnabled(True)
        self.template_changed = False
        self.save_btn.setEnabled(False)
        
        self.update_preview()
    
    def on_template_changed(self):
        """Handle template changes"""
        self.template_changed = True
        self.save_btn.setEnabled(True)
        self.update_preview()
    
    def update_preview(self):
        """Update preview with sample data"""
        pattern = self.pattern_edit.text()
        message = self.message_edit.toPlainText()
        
        if not pattern:
            self.preview_label.setText("Enter a tag pattern to see preview")
            return
        
        # Sample data for preview
        sample_data = {
            'version': '1.0.0',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'build_id': 'build-20240101-123456',
            'branch': 'main',
            'commit_short': 'abc1234'
        }
        
        try:
            preview_tag = pattern.format(**sample_data)
            preview_msg = message.format(**sample_data) if message else ""
            
            preview_text = f"Tag: {preview_tag}"
            if preview_msg:
                preview_text += f"\\n\\nMessage:\\n{preview_msg}"
            
            self.preview_label.setText(preview_text)
        except KeyError as e:
            self.preview_label.setText(f"Error: Unknown variable {e}")
        except Exception as e:
            self.preview_label.setText(f"Error: {str(e)}")
    
    def new_template(self):
        """Create new template"""
        if self.template_changed and self.current_template:
            reply = QMessageBox.question(self, 'Unsaved Changes', 
                                       'Save changes to current template?',
                                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.save_current_template()
            elif reply == QMessageBox.Cancel:
                return
        
        name, ok = QInputDialog.getText(self, 'New Template', 'Template name:')
        if ok and name:
            if name in self.templates:
                QMessageBox.warning(self, "Error", "Template name already exists")
                return
            
            self.current_template = name
            self.name_edit.setText(name)
            self.pattern_edit.setText("")
            self.message_edit.setPlainText("")
            
            self.template_changed = True
            self.save_btn.setEnabled(True)
            self.delete_btn.setEnabled(False)
            
            self.update_preview()
    
    def delete_template(self):
        """Delete selected template"""
        if not self.current_template:
            return
        
        reply = QMessageBox.question(self, 'Delete Template', 
                                   f'Delete template "{self.current_template}"?',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            del self.templates[self.current_template]
            self.save_templates()
            self.load_template_list()
            
            # Clear editor
            self.current_template = None
            self.name_edit.setText("")
            self.pattern_edit.setText("")
            self.message_edit.setPlainText("")
            self.delete_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.template_changed = False
            self.preview_label.setText("Select or create a template to see preview")
    
    def save_current_template(self):
        """Save current template"""
        name = self.name_edit.text().strip()
        pattern = self.pattern_edit.text().strip()
        message = self.message_edit.toPlainText()
        
        if not name:
            QMessageBox.warning(self, "Error", "Template name is required")
            return
        
        if not pattern:
            QMessageBox.warning(self, "Error", "Tag pattern is required")
            return
        
        # If name changed, remove old template
        if self.current_template and self.current_template != name:
            if self.current_template in self.templates:
                del self.templates[self.current_template]
        
        self.templates[name] = {
            'pattern': pattern,
            'message': message
        }
        
        self.current_template = name
        self.template_changed = False
        self.save_btn.setEnabled(False)
        self.delete_btn.setEnabled(True)
        
        self.save_templates()
        self.load_template_list()
        
        # Select the saved template
        for i in range(self.template_list.count()):
            if self.template_list.item(i).text() == name:
                self.template_list.setCurrentRow(i)
                break
    
    def accept(self):
        """Handle dialog accept"""
        if self.template_changed:
            reply = QMessageBox.question(self, 'Unsaved Changes', 
                                       'Save changes to current template?',
                                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.save_current_template()
            elif reply == QMessageBox.Cancel:
                return
        
        super().accept()

class CreateTagFromTemplateDialog(QDialog):
    """Dialog for creating tags from templates"""
    
    def __init__(self, templates, repo_manager, parent=None):
        super().__init__(parent)
        self.templates = templates
        self.repo_manager = repo_manager
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Create Tag from Template")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Template selection
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Template:"))
        self.template_combo = QComboBox()
        self.template_combo.addItems(sorted(self.templates.keys()))
        self.template_combo.currentTextChanged.connect(self.on_template_changed)
        template_layout.addWidget(self.template_combo)
        layout.addLayout(template_layout)
        
        # Variables
        variables_group = QGroupBox("Variables")
        variables_layout = QVBoxLayout()
        
        # Version
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("Version:"))
        self.version_edit = QLineEdit("1.0.0")
        self.version_edit.textChanged.connect(self.update_preview)
        version_layout.addWidget(self.version_edit)
        variables_layout.addLayout(version_layout)
        
        # Build ID (auto-filled)
        build_layout = QHBoxLayout()
        build_layout.addWidget(QLabel("Build ID:"))
        self.build_id_edit = QLineEdit()
        self.build_id_edit.textChanged.connect(self.update_preview)
        build_layout.addWidget(self.build_id_edit)
        variables_layout.addLayout(build_layout)
        
        variables_group.setLayout(variables_layout)
        layout.addWidget(variables_group)
        
        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        self.tag_preview = QLabel()
        self.tag_preview.setStyleSheet("background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc;")
        preview_layout.addWidget(QLabel("Tag Name:"))
        preview_layout.addWidget(self.tag_preview)
        
        self.message_preview = QTextEdit()
        self.message_preview.setReadOnly(True)
        self.message_preview.setMaximumHeight(100)
        preview_layout.addWidget(QLabel("Tag Message:"))
        preview_layout.addWidget(self.message_preview)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.create_tag)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
        # Initialize
        self.fill_auto_variables()
        self.on_template_changed()
    
    def fill_auto_variables(self):
        """Fill automatic variables"""
        try:
            # Get current build ID from parent
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'current_build_id'):
                parent_window = parent_window.parent()
            
            if parent_window and parent_window.current_build_id:
                self.build_id_edit.setText(parent_window.current_build_id)
            else:
                self.build_id_edit.setText(f"build-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        except:
            self.build_id_edit.setText(f"build-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    
    def on_template_changed(self):
        """Handle template selection change"""
        self.update_preview()
    
    def update_preview(self):
        """Update preview"""
        template_name = self.template_combo.currentText()
        if not template_name or template_name not in self.templates:
            return
        
        template = self.templates[template_name]
        
        # Get current repository info
        try:
            repo_status = self.repo_manager.get_repository_status()
            current_branch = repo_status.get('current_branch', 'main')
            last_commit = repo_status.get('last_commit', {})
            commit_short = last_commit.get('hash', 'unknown')[:7] if last_commit.get('hash') else 'unknown'
        except:
            current_branch = 'main'
            commit_short = 'unknown'
        
        # Prepare variables
        variables = {
            'version': self.version_edit.text(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'build_id': self.build_id_edit.text(),
            'branch': current_branch,
            'commit_short': commit_short
        }
        
        try:
            # Generate tag name and message
            tag_name = template['pattern'].format(**variables)
            tag_message = template['message'].format(**variables)
            
            self.tag_preview.setText(tag_name)
            self.message_preview.setPlainText(tag_message)
            
        except KeyError as e:
            self.tag_preview.setText(f"Error: Unknown variable {e}")
            self.message_preview.setPlainText("")
        except Exception as e:
            self.tag_preview.setText(f"Error: {str(e)}")
            self.message_preview.setPlainText("")
    
    def create_tag(self):
        """Create the tag"""
        tag_name = self.tag_preview.text()
        tag_message = self.message_preview.toPlainText()
        
        if not tag_name or tag_name.startswith("Error:"):
            QMessageBox.warning(self, "Error", "Cannot create tag with invalid name")
            return
        
        # Check if tag already exists
        existing_tags = [tag['name'] for tag in self.repo_manager.list_tags()]
        if tag_name in existing_tags:
            reply = QMessageBox.question(self, 'Tag Exists', 
                                       f'Tag "{tag_name}" already exists. Replace it?',
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
            
            # Delete existing tag
            self.repo_manager.delete_tag(tag_name)
        
        # Create the tag
        if self.repo_manager.create_tag(tag_name, tag_message):
            QMessageBox.information(self, "Success", f"Created tag: {tag_name}")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", f"Failed to create tag: {tag_name}")