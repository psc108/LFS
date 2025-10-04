#!/usr/bin/env python3

# Read the current kernel_config_dialog.py
with open('src/gui/kernel_config_dialog.py', 'r') as f:
    content = f.read()

# Add help data dictionary after imports
help_data = '''
class KernelHelpData:
    """Context-sensitive help for kernel configuration options"""
    
    HELP_TEXT = {
        "local_version": {
            "title": "Local Version String",
            "description": "Appends a custom string to the kernel version. Common values: '-lfs', '-custom', '-server'",
            "example": "Example: '-lfs' results in kernel version like '6.1.11-lfs'",
            "recommendation": "Use '-lfs' for Linux From Scratch builds"
        },
        "compression": {
            "title": "Kernel Compression Method", 
            "description": "Compression algorithm for the kernel image. Affects boot time and kernel size.",
            "example": "XZ: Best compression, slower boot. Gzip: Faster boot, larger size. LZ4: Fastest boot, largest size.",
            "recommendation": "XZ recommended for most systems (good balance of size and speed)"
        },
        "cpu_family": {
            "title": "Processor Family Optimization",
            "description": "Optimizes kernel for specific CPU architecture. Improves performance but reduces compatibility.",
            "example": "Generic x86-64: Works on all 64-bit systems. Intel Core i7: Optimized for Intel processors.",
            "recommendation": "Use Generic x86-64 for maximum compatibility, specific CPU for performance"
        },
        "max_cpus": {
            "title": "Maximum Number of CPUs",
            "description": "Maximum CPUs the kernel can use. Higher values use more memory but support more cores.",
            "example": "64: Good for most systems. 256: High-end servers. 8: Embedded systems.",
            "recommendation": "64 is sufficient for most desktop and server systems"
        },
        "smp_support": {
            "title": "Symmetric Multi-Processing",
            "description": "Enables support for multiple CPU cores. Required for multi-core systems.",
            "example": "Enable for any system with more than one CPU core.",
            "recommendation": "Always enable unless building for single-core embedded systems"
        },
        "highmem": {
            "title": "High Memory Support",
            "description": "Enables support for more than 4GB of RAM on 32-bit systems. Not needed on 64-bit.",
            "example": "Required for 32-bit systems with >4GB RAM.",
            "recommendation": "Enable for compatibility, no impact on 64-bit systems"
        },
        "ata_support": {
            "title": "ATA/IDE Drive Support",
            "description": "Support for traditional IDE/PATA hard drives and CD/DVD drives.",
            "example": "Needed for older IDE drives and most optical drives.",
            "recommendation": "Enable for compatibility with older hardware"
        },
        "sata_support": {
            "title": "Serial ATA Support", 
            "description": "Support for modern SATA hard drives and SSDs.",
            "example": "Required for most modern desktop and laptop storage.",
            "recommendation": "Always enable for modern systems"
        },
        "nvme_support": {
            "title": "NVMe SSD Support",
            "description": "Support for high-speed NVMe solid-state drives.",
            "example": "Required for M.2 NVMe SSDs and PCIe SSDs.",
            "recommendation": "Enable if you have or plan to use NVMe storage"
        },
        "usb_support": {
            "title": "USB Support",
            "description": "Basic USB subsystem support. Required for any USB devices.",
            "example": "Needed for USB keyboards, mice, storage devices, etc.",
            "recommendation": "Always enable for desktop systems"
        },
        "drm_support": {
            "title": "Direct Rendering Manager",
            "description": "Graphics subsystem for modern video cards. Required for hardware acceleration.",
            "example": "Needed for 3D graphics, video playback, and modern desktop environments.",
            "recommendation": "Enable for any system with a graphics card"
        },
        "networking": {
            "title": "Network Support",
            "description": "Basic networking subsystem. Required for any network connectivity.",
            "example": "Needed for internet, LAN, WiFi, etc.",
            "recommendation": "Always enable unless building for isolated embedded systems"
        },
        "inet": {
            "title": "TCP/IP Networking",
            "description": "Internet Protocol support. Required for internet connectivity.",
            "example": "Needed for web browsing, email, SSH, etc.",
            "recommendation": "Always enable for networked systems"
        },
        "ipv6": {
            "title": "IPv6 Protocol Support",
            "description": "Next-generation Internet Protocol. Increasingly required by modern networks.",
            "example": "Many ISPs and networks now require IPv6.",
            "recommendation": "Enable for future compatibility"
        },
        "ext4": {
            "title": "Ext4 Filesystem",
            "description": "Modern Linux filesystem with journaling and large file support.",
            "example": "Default filesystem for most Linux distributions.",
            "recommendation": "Always enable - required for most Linux systems"
        },
        "proc_fs": {
            "title": "/proc Filesystem",
            "description": "Virtual filesystem providing system information and process details.",
            "example": "Used by 'ps', 'top', and many system utilities.",
            "recommendation": "Always enable - required by most Linux software"
        },
        "sysfs": {
            "title": "/sys Filesystem", 
            "description": "Virtual filesystem for device and driver information.",
            "example": "Used by udev and hardware detection tools.",
            "recommendation": "Always enable - required by modern Linux systems"
        },
        "tmpfs": {
            "title": "Tmpfs Virtual Memory Filesystem",
            "description": "RAM-based filesystem for temporary files.",
            "example": "Used for /tmp and /run directories for better performance.",
            "recommendation": "Enable for better system performance"
        },
        "devtmpfs": {
            "title": "Devtmpfs Device Filesystem",
            "description": "Automatic device node creation in /dev.",
            "example": "Creates device files automatically when hardware is detected.",
            "recommendation": "Always enable - required by modern Linux systems"
        },
        "security": {
            "title": "Security Framework",
            "description": "Linux Security Module framework for access control systems.",
            "example": "Required for SELinux, AppArmor, and other security systems.",
            "recommendation": "Enable for security-conscious systems"
        },
        "debug_kernel": {
            "title": "Kernel Debugging",
            "description": "Enables kernel debugging features. Increases kernel size and may impact performance.",
            "example": "Useful for kernel development and troubleshooting crashes.",
            "recommendation": "Disable for production systems, enable for development"
        }
    }

'''

# Insert help data class before the KernelConfigDialog class
content = content.replace(
    'class KernelConfigDialog(QDialog):',
    help_data + '\nclass KernelConfigDialog(QDialog):'
)

# Add help panel to the UI setup
help_panel_code = '''
        # Help panel
        help_layout = QHBoxLayout()
        
        # Help text area
        self.help_text = QTextEdit()
        self.help_text.setReadOnly(True)
        self.help_text.setMaximumHeight(120)
        self.help_text.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6; font-size: 11px;")
        self.help_text.setPlainText("Hover over any option to see detailed help information.")
        
        help_layout.addWidget(QLabel("Help:"))
        help_layout.addWidget(self.help_text)
        
        layout.addLayout(help_layout)
        
'''

# Insert help panel before buttons
content = content.replace(
    '        # Buttons\n        button_layout = QHBoxLayout()',
    help_panel_code + '        # Buttons\n        button_layout = QHBoxLayout()'
)

# Add tooltip and help methods
help_methods = '''
    def setup_help_tooltips(self):
        """Setup tooltips and help for all widgets"""
        help_data = KernelHelpData.HELP_TEXT
        
        # Setup tooltips for widgets
        widgets_help = {
            self.local_version: "local_version",
            self.compression: "compression", 
            self.cpu_family: "cpu_family",
            self.max_cpus: "max_cpus",
            self.smp_support: "smp_support",
            self.highmem: "highmem",
            self.ata_support: "ata_support",
            self.sata_support: "sata_support", 
            self.nvme_support: "nvme_support",
            self.usb_support: "usb_support",
            self.drm_support: "drm_support",
            self.networking: "networking",
            self.inet: "inet",
            self.ipv6: "ipv6",
            self.ext4: "ext4",
            self.proc_fs: "proc_fs",
            self.sysfs: "sysfs",
            self.tmpfs: "tmpfs",
            self.devtmpfs: "devtmpfs",
            self.security: "security",
            self.debug_kernel: "debug_kernel"
        }
        
        for widget, help_key in widgets_help.items():
            if help_key in help_data:
                help_info = help_data[help_key]
                tooltip = f"{help_info['title']}\\n\\n{help_info['description']}"
                widget.setToolTip(tooltip)
                
                # Connect hover events for detailed help
                widget.enterEvent = lambda event, key=help_key: self.show_detailed_help(key)
                widget.leaveEvent = lambda event: self.clear_help()
    
    def show_detailed_help(self, help_key):
        """Show detailed help for a specific option"""
        help_data = KernelHelpData.HELP_TEXT
        if help_key in help_data:
            help_info = help_data[help_key]
            
            help_text = f"📋 {help_info['title']}\\n\\n"
            help_text += f"📝 {help_info['description']}\\n\\n"
            
            if 'example' in help_info:
                help_text += f"💡 {help_info['example']}\\n\\n"
            
            if 'recommendation' in help_info:
                help_text += f"✅ Recommendation: {help_info['recommendation']}"
            
            self.help_text.setPlainText(help_text)
    
    def clear_help(self):
        """Clear help text"""
        self.help_text.setPlainText("Hover over any option to see detailed help information.")
    
'''

# Insert help methods before load_kernel_config method
content = content.replace(
    '    def load_kernel_config(self):',
    help_methods + '\n    def load_kernel_config(self):'
)

# Add call to setup help tooltips in __init__
content = content.replace(
    '        self.setup_ui()\n        self.load_config_values()',
    '        self.setup_ui()\n        self.setup_help_tooltips()\n        self.load_config_values()'
)

# Write the updated content
with open('src/gui/kernel_config_dialog.py', 'w') as f:
    f.write(content)

print("✅ Added context-sensitive help to kernel configuration dialog")