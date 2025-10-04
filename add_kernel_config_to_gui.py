#!/usr/bin/env python3

# Read the current main_window.py
with open('src/gui/main_window.py', 'r') as f:
    content = f.read()

# Add import for kernel config dialog
import_line = "from .build_details_dialog import BuildDetailsDialog"
new_import = "from .build_details_dialog import BuildDetailsDialog\nfrom .kernel_config_dialog import KernelConfigDialog"

content = content.replace(import_line, new_import)

# Add kernel config action to build menu
menu_addition = '''        self.settings_action = self.build_menu.addAction("Settings")
        self.settings_action.triggered.connect(self.open_settings)'''

new_menu = '''        self.kernel_config_action = self.build_menu.addAction("Kernel Configuration")
        self.kernel_config_action.triggered.connect(self.open_kernel_config)
        
        self.settings_action = self.build_menu.addAction("Settings")
        self.settings_action.triggered.connect(self.open_settings)'''

content = content.replace(menu_addition, new_menu)

# Add kernel config method
kernel_method = '''
    def open_kernel_config(self):
        """Open kernel configuration dialog"""
        dialog = KernelConfigDialog(self.settings, self)
        dialog.exec_()
'''

# Insert before the open_settings method
content = content.replace(
    '    def open_settings(self):',
    kernel_method + '\n    def open_settings(self):'
)

# Write the updated content
with open('src/gui/main_window.py', 'w') as f:
    f.write(content)

print("✅ Added kernel configuration to main GUI")