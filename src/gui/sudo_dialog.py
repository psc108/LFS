#!/usr/bin/env python3

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

class SudoPasswordDialog(QDialog):
    """Dialog for requesting sudo password"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.password = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Sudo Password Required")
        self.setModal(True)
        self.setFixedSize(400, 150)
        
        layout = QVBoxLayout()
        
        # Message
        msg_label = QLabel("The build process requires administrator privileges.\nPlease enter your sudo password:")
        layout.addWidget(msg_label)
        
        # Password input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter sudo password...")
        self.password_input.returnPressed.connect(self.accept)
        layout.addWidget(self.password_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Focus on password input
        self.password_input.setFocus()
    
    def accept(self):
        self.password = self.password_input.text()
        if not self.password:
            QMessageBox.warning(self, "Warning", "Please enter your sudo password.")
            return
        super().accept()
    
    def get_password(self):
        """Get the entered password"""
        return self.password

    @staticmethod
    def get_sudo_password(parent=None):
        """Static method to get sudo password"""
        dialog = SudoPasswordDialog(parent)
        if dialog.exec_() == QDialog.Accepted:
            return dialog.get_password()
        return None