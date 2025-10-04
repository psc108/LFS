from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QCheckBox, QComboBox, QSpinBox, 
                            QDialogButtonBox, QTabWidget, QWidget, QScrollArea,
                            QGroupBox, QGridLayout, QTextEdit, QPushButton,
                            QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt
import json
import os


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


class KernelConfigDialog(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings = settings_manager
        self.setWindowTitle("Linux Kernel Configuration")
        self.setModal(True)
        self.resize(800, 600)
        
        # Load current kernel config
        self.kernel_config = self.load_kernel_config()
        
        self.setup_ui()
        self.setup_help_tooltips()
        self.load_config_values()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Configure Linux Kernel Build Parameters")
        header.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Tabs for different config categories
        tab_widget = QTabWidget()
        
        # General tab
        general_tab = self.create_general_tab()
        tab_widget.addTab(general_tab, "General")
        
        # Hardware tab
        hardware_tab = self.create_hardware_tab()
        tab_widget.addTab(hardware_tab, "Hardware")
        
        # Networking tab
        network_tab = self.create_network_tab()
        tab_widget.addTab(network_tab, "Networking")
        
        # Filesystems tab
        fs_tab = self.create_filesystem_tab()
        tab_widget.addTab(fs_tab, "Filesystems")
        
        # Advanced tab
        advanced_tab = self.create_advanced_tab()
        tab_widget.addTab(advanced_tab, "Advanced")
        
        layout.addWidget(tab_widget)
        

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
        
        # Buttons
        button_layout = QHBoxLayout()
        
        load_btn = QPushButton("Load .config")
        load_btn.clicked.connect(self.load_config_file)
        button_layout.addWidget(load_btn)
        
        save_btn = QPushButton("Save .config")
        save_btn.clicked.connect(self.save_config_file)
        button_layout.addWidget(save_btn)
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_config)
        buttons.rejected.connect(self.reject)
        button_layout.addWidget(buttons)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Kernel version info
        version_group = QGroupBox("Kernel Information")
        version_layout = QGridLayout(version_group)
        
        version_layout.addWidget(QLabel("Local Version:"), 0, 0)
        self.local_version = QLineEdit()
        self.local_version.setPlaceholderText("e.g., -lfs")
        version_layout.addWidget(self.local_version, 0, 1)
        
        version_layout.addWidget(QLabel("Kernel Compression:"), 1, 0)
        self.compression = QComboBox()
        self.compression.addItems(["Gzip", "Bzip2", "LZMA", "XZ", "LZO", "LZ4"])
        version_layout.addWidget(self.compression, 1, 1)
        
        layout.addWidget(version_group)
        
        # CPU options
        cpu_group = QGroupBox("Processor Options")
        cpu_layout = QGridLayout(cpu_group)
        
        cpu_layout.addWidget(QLabel("Processor Family:"), 0, 0)
        self.cpu_family = QComboBox()
        self.cpu_family.addItems([
            "Generic x86-64", "Intel Core 2", "Intel Atom", "Intel Core i7",
            "AMD Opteron/Athlon64", "AMD Bulldozer", "AMD Zen"
        ])
        cpu_layout.addWidget(self.cpu_family, 0, 1)
        
        cpu_layout.addWidget(QLabel("Maximum CPUs:"), 1, 0)
        self.max_cpus = QSpinBox()
        self.max_cpus.setRange(1, 8192)
        self.max_cpus.setValue(64)
        cpu_layout.addWidget(self.max_cpus, 1, 1)
        
        self.smp_support = QCheckBox("Symmetric Multi-Processing (SMP)")
        self.smp_support.setChecked(True)
        cpu_layout.addWidget(self.smp_support, 2, 0, 1, 2)
        
        layout.addWidget(cpu_group)
        
        # Memory options
        mem_group = QGroupBox("Memory Management")
        mem_layout = QGridLayout(mem_group)
        
        self.highmem = QCheckBox("High Memory Support (>4GB)")
        self.highmem.setChecked(True)
        mem_layout.addWidget(self.highmem, 0, 0, 1, 2)
        
        self.transparent_hugepage = QCheckBox("Transparent Huge Pages")
        self.transparent_hugepage.setChecked(True)
        mem_layout.addWidget(self.transparent_hugepage, 1, 0, 1, 2)
        
        layout.addWidget(mem_group)
        layout.addStretch()
        
        return tab
    
    def create_hardware_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Storage devices
        storage_group = QGroupBox("Storage Devices")
        storage_layout = QGridLayout(storage_group)
        
        self.ata_support = QCheckBox("ATA/ATAPI/MFM/RLL Support")
        self.ata_support.setChecked(True)
        storage_layout.addWidget(self.ata_support, 0, 0, 1, 2)
        
        self.scsi_support = QCheckBox("SCSI Device Support")
        self.scsi_support.setChecked(True)
        storage_layout.addWidget(self.scsi_support, 1, 0, 1, 2)
        
        self.sata_support = QCheckBox("Serial ATA Support")
        self.sata_support.setChecked(True)
        storage_layout.addWidget(self.sata_support, 2, 0, 1, 2)
        
        self.nvme_support = QCheckBox("NVMe Support")
        self.nvme_support.setChecked(True)
        storage_layout.addWidget(self.nvme_support, 3, 0, 1, 2)
        
        layout.addWidget(storage_group)
        
        # USB support
        usb_group = QGroupBox("USB Support")
        usb_layout = QGridLayout(usb_group)
        
        self.usb_support = QCheckBox("USB Support")
        self.usb_support.setChecked(True)
        usb_layout.addWidget(self.usb_support, 0, 0, 1, 2)
        
        self.usb2_support = QCheckBox("USB 2.0 (EHCI) Support")
        self.usb2_support.setChecked(True)
        usb_layout.addWidget(self.usb2_support, 1, 0, 1, 2)
        
        self.usb3_support = QCheckBox("USB 3.0 (xHCI) Support")
        self.usb3_support.setChecked(True)
        usb_layout.addWidget(self.usb3_support, 2, 0, 1, 2)
        
        layout.addWidget(usb_group)
        
        # Graphics
        graphics_group = QGroupBox("Graphics Support")
        graphics_layout = QGridLayout(graphics_group)
        
        self.drm_support = QCheckBox("Direct Rendering Manager (DRM)")
        self.drm_support.setChecked(True)
        graphics_layout.addWidget(self.drm_support, 0, 0, 1, 2)
        
        self.intel_graphics = QCheckBox("Intel Graphics (i915)")
        self.intel_graphics.setChecked(True)
        graphics_layout.addWidget(self.intel_graphics, 1, 0, 1, 2)
        
        self.amd_graphics = QCheckBox("AMD Graphics (AMDGPU)")
        self.amd_graphics.setChecked(True)
        graphics_layout.addWidget(self.amd_graphics, 2, 0, 1, 2)
        
        layout.addWidget(graphics_group)
        layout.addStretch()
        
        return tab
    
    def create_network_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Network core
        net_group = QGroupBox("Network Core")
        net_layout = QGridLayout(net_group)
        
        self.networking = QCheckBox("Enable Networking")
        self.networking.setChecked(True)
        net_layout.addWidget(self.networking, 0, 0, 1, 2)
        
        self.packet_socket = QCheckBox("Packet Socket")
        self.packet_socket.setChecked(True)
        net_layout.addWidget(self.packet_socket, 1, 0, 1, 2)
        
        self.unix_socket = QCheckBox("Unix Domain Sockets")
        self.unix_socket.setChecked(True)
        net_layout.addWidget(self.unix_socket, 2, 0, 1, 2)
        
        layout.addWidget(net_group)
        
        # TCP/IP
        tcp_group = QGroupBox("TCP/IP Networking")
        tcp_layout = QGridLayout(tcp_group)
        
        self.inet = QCheckBox("TCP/IP Networking")
        self.inet.setChecked(True)
        tcp_layout.addWidget(self.inet, 0, 0, 1, 2)
        
        self.ipv6 = QCheckBox("IPv6 Protocol")
        self.ipv6.setChecked(True)
        tcp_layout.addWidget(self.ipv6, 1, 0, 1, 2)
        
        self.netfilter = QCheckBox("Network Packet Filtering (Netfilter)")
        self.netfilter.setChecked(True)
        tcp_layout.addWidget(self.netfilter, 2, 0, 1, 2)
        
        layout.addWidget(tcp_group)
        
        # Ethernet
        eth_group = QGroupBox("Ethernet Drivers")
        eth_layout = QGridLayout(eth_group)
        
        self.ethernet = QCheckBox("Ethernet Driver Support")
        self.ethernet.setChecked(True)
        eth_layout.addWidget(self.ethernet, 0, 0, 1, 2)
        
        self.intel_e1000 = QCheckBox("Intel E1000 Gigabit Ethernet")
        self.intel_e1000.setChecked(True)
        eth_layout.addWidget(self.intel_e1000, 1, 0, 1, 2)
        
        self.realtek_8139 = QCheckBox("Realtek RTL8139 Fast Ethernet")
        self.realtek_8139.setChecked(True)
        eth_layout.addWidget(self.realtek_8139, 2, 0, 1, 2)
        
        layout.addWidget(eth_group)
        layout.addStretch()
        
        return tab
    
    def create_filesystem_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Core filesystems
        core_group = QGroupBox("Core Filesystems")
        core_layout = QGridLayout(core_group)
        
        self.ext4 = QCheckBox("Ext4 Filesystem")
        self.ext4.setChecked(True)
        core_layout.addWidget(self.ext4, 0, 0, 1, 2)
        
        self.xfs = QCheckBox("XFS Filesystem")
        self.xfs.setChecked(True)
        core_layout.addWidget(self.xfs, 1, 0, 1, 2)
        
        self.btrfs = QCheckBox("Btrfs Filesystem")
        self.btrfs.setChecked(False)
        core_layout.addWidget(self.btrfs, 2, 0, 1, 2)
        
        layout.addWidget(core_group)
        
        # Virtual filesystems
        vfs_group = QGroupBox("Virtual Filesystems")
        vfs_layout = QGridLayout(vfs_group)
        
        self.proc_fs = QCheckBox("/proc Filesystem")
        self.proc_fs.setChecked(True)
        vfs_layout.addWidget(self.proc_fs, 0, 0, 1, 2)
        
        self.sysfs = QCheckBox("/sys Filesystem (sysfs)")
        self.sysfs.setChecked(True)
        vfs_layout.addWidget(self.sysfs, 1, 0, 1, 2)
        
        self.tmpfs = QCheckBox("Tmpfs Virtual Memory Filesystem")
        self.tmpfs.setChecked(True)
        vfs_layout.addWidget(self.tmpfs, 2, 0, 1, 2)
        
        self.devtmpfs = QCheckBox("Devtmpfs (/dev) Support")
        self.devtmpfs.setChecked(True)
        vfs_layout.addWidget(self.devtmpfs, 3, 0, 1, 2)
        
        layout.addWidget(vfs_group)
        
        # Other filesystems
        other_group = QGroupBox("Other Filesystems")
        other_layout = QGridLayout(other_group)
        
        self.fat_fs = QCheckBox("FAT Filesystem (VFAT)")
        self.fat_fs.setChecked(True)
        other_layout.addWidget(self.fat_fs, 0, 0, 1, 2)
        
        self.ntfs = QCheckBox("NTFS Filesystem")
        self.ntfs.setChecked(True)
        other_layout.addWidget(self.ntfs, 1, 0, 1, 2)
        
        self.iso9660 = QCheckBox("ISO 9660 CD-ROM Filesystem")
        self.iso9660.setChecked(True)
        other_layout.addWidget(self.iso9660, 2, 0, 1, 2)
        
        layout.addWidget(other_group)
        layout.addStretch()
        
        return tab
    
    def create_advanced_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Security
        security_group = QGroupBox("Security Options")
        security_layout = QGridLayout(security_group)
        
        self.security = QCheckBox("Enable Security Framework")
        self.security.setChecked(True)
        security_layout.addWidget(self.security, 0, 0, 1, 2)
        
        self.selinux = QCheckBox("SELinux Support")
        self.selinux.setChecked(False)
        security_layout.addWidget(self.selinux, 1, 0, 1, 2)
        
        layout.addWidget(security_group)
        
        # Debugging
        debug_group = QGroupBox("Debugging Options")
        debug_layout = QGridLayout(debug_group)
        
        self.debug_kernel = QCheckBox("Kernel Debugging")
        self.debug_kernel.setChecked(False)
        debug_layout.addWidget(self.debug_kernel, 0, 0, 1, 2)
        
        self.debug_info = QCheckBox("Compile with Debug Info")
        self.debug_info.setChecked(False)
        debug_layout.addWidget(self.debug_info, 1, 0, 1, 2)
        
        layout.addWidget(debug_group)
        
        # Custom config
        custom_group = QGroupBox("Custom Configuration")
        custom_layout = QVBoxLayout(custom_group)
        
        custom_layout.addWidget(QLabel("Additional CONFIG options (one per line):"))
        self.custom_config = QTextEdit()
        self.custom_config.setPlaceholderText("CONFIG_EXAMPLE=y\nCONFIG_ANOTHER=m\n# CONFIG_DISABLED is not set")
        self.custom_config.setMaximumHeight(150)
        custom_layout.addWidget(self.custom_config)
        
        layout.addWidget(custom_group)
        layout.addStretch()
        
        return tab
    

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
                tooltip = f"{help_info['title']}\n\n{help_info['description']}"
                widget.setToolTip(tooltip)
                
                # Connect hover events for detailed help
                widget.enterEvent = lambda event, key=help_key: self.show_detailed_help(key)
                widget.leaveEvent = lambda event: self.clear_help()
    
    def show_detailed_help(self, help_key):
        """Show detailed help for a specific option"""
        help_data = KernelHelpData.HELP_TEXT
        if help_key in help_data:
            help_info = help_data[help_key]
            
            help_text = f"📋 {help_info['title']}\n\n"
            help_text += f"📝 {help_info['description']}\n\n"
            
            if 'example' in help_info:
                help_text += f"💡 {help_info['example']}\n\n"
            
            if 'recommendation' in help_info:
                help_text += f"✅ Recommendation: {help_info['recommendation']}"
            
            self.help_text.setPlainText(help_text)
    
    def clear_help(self):
        """Clear help text"""
        self.help_text.setPlainText("Hover over any option to see detailed help information.")
    

    def load_kernel_config(self):
        """Load kernel configuration from settings"""
        return self.settings.get("kernel_config", self.get_default_config())
    
    def get_default_config(self):
        """Get default kernel configuration"""
        return {
            "local_version": "-lfs",
            "compression": "XZ",
            "cpu_family": "Generic x86-64",
            "max_cpus": 64,
            "smp_support": True,
            "highmem": True,
            "transparent_hugepage": True,
            "ata_support": True,
            "scsi_support": True,
            "sata_support": True,
            "nvme_support": True,
            "usb_support": True,
            "usb2_support": True,
            "usb3_support": True,
            "drm_support": True,
            "intel_graphics": True,
            "amd_graphics": True,
            "networking": True,
            "packet_socket": True,
            "unix_socket": True,
            "inet": True,
            "ipv6": True,
            "netfilter": True,
            "ethernet": True,
            "intel_e1000": True,
            "realtek_8139": True,
            "ext4": True,
            "xfs": True,
            "btrfs": False,
            "proc_fs": True,
            "sysfs": True,
            "tmpfs": True,
            "devtmpfs": True,
            "fat_fs": True,
            "ntfs": True,
            "iso9660": True,
            "security": True,
            "selinux": False,
            "debug_kernel": False,
            "debug_info": False,
            "custom_config": ""
        }
    
    def load_config_values(self):
        """Load configuration values into UI"""
        config = self.kernel_config
        
        self.local_version.setText(config.get("local_version", ""))
        self.compression.setCurrentText(config.get("compression", "XZ"))
        self.cpu_family.setCurrentText(config.get("cpu_family", "Generic x86-64"))
        self.max_cpus.setValue(config.get("max_cpus", 64))
        
        # Set checkboxes
        checkboxes = [
            "smp_support", "highmem", "transparent_hugepage",
            "ata_support", "scsi_support", "sata_support", "nvme_support",
            "usb_support", "usb2_support", "usb3_support",
            "drm_support", "intel_graphics", "amd_graphics",
            "networking", "packet_socket", "unix_socket", "inet", "ipv6", "netfilter",
            "ethernet", "intel_e1000", "realtek_8139",
            "ext4", "xfs", "btrfs", "proc_fs", "sysfs", "tmpfs", "devtmpfs",
            "fat_fs", "ntfs", "iso9660", "security", "selinux", "debug_kernel", "debug_info"
        ]
        
        for checkbox_name in checkboxes:
            checkbox = getattr(self, checkbox_name)
            checkbox.setChecked(config.get(checkbox_name, False))
        
        self.custom_config.setPlainText(config.get("custom_config", ""))
    
    def save_config(self):
        """Save configuration and close dialog"""
        config = {}
        
        # Text fields
        config["local_version"] = self.local_version.text()
        config["compression"] = self.compression.currentText()
        config["cpu_family"] = self.cpu_family.currentText()
        config["max_cpus"] = self.max_cpus.value()
        
        # Checkboxes
        checkboxes = [
            "smp_support", "highmem", "transparent_hugepage",
            "ata_support", "scsi_support", "sata_support", "nvme_support",
            "usb_support", "usb2_support", "usb3_support",
            "drm_support", "intel_graphics", "amd_graphics",
            "networking", "packet_socket", "unix_socket", "inet", "ipv6", "netfilter",
            "ethernet", "intel_e1000", "realtek_8139",
            "ext4", "xfs", "btrfs", "proc_fs", "sysfs", "tmpfs", "devtmpfs",
            "fat_fs", "ntfs", "iso9660", "security", "selinux", "debug_kernel", "debug_info"
        ]
        
        for checkbox_name in checkboxes:
            checkbox = getattr(self, checkbox_name)
            config[checkbox_name] = checkbox.isChecked()
        
        config["custom_config"] = self.custom_config.toPlainText()
        
        # Save to settings
        self.settings.set("kernel_config", config)
        
        QMessageBox.information(self, "Configuration Saved", 
                               "Kernel configuration has been saved and will be used for the next build.")
        self.accept()
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        reply = QMessageBox.question(self, 'Reset Configuration', 
                                   'Reset all kernel configuration to defaults?',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.kernel_config = self.get_default_config()
            self.load_config_values()
    
    def load_config_file(self):
        """Load kernel .config file"""
        filename, _ = QFileDialog.getOpenFileName(self, "Load Kernel Config", "", "Config Files (*.config);;All Files (*)")
        if filename:
            try:
                # Parse .config file and update UI
                # This is a simplified parser - real implementation would be more comprehensive
                QMessageBox.information(self, "Load Config", f"Config file loading from {filename} - feature coming soon!")
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Failed to load config: {str(e)}")
    
    def save_config_file(self):
        """Save kernel .config file"""
        filename, _ = QFileDialog.getSaveFileName(self, "Save Kernel Config", "kernel.config", "Config Files (*.config);;All Files (*)")
        if filename:
            try:
                # Generate .config file from current settings
                config_content = self.generate_config_file()
                with open(filename, 'w') as f:
                    f.write(config_content)
                QMessageBox.information(self, "Save Complete", f"Kernel configuration saved to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save config: {str(e)}")
    
    def generate_config_file(self):
        """Generate .config file content from current settings"""
        lines = []
        lines.append("# Linux Kernel Configuration")
        lines.append("# Generated by LFS Build System")
        lines.append("")
        
        # Add configuration based on current settings
        if self.local_version.text():
            lines.append(f'CONFIG_LOCALVERSION="{self.local_version.text()}"')
        
        if self.smp_support.isChecked():
            lines.append("CONFIG_SMP=y")
        else:
            lines.append("# CONFIG_SMP is not set")
        
        # Add more config mappings here...
        
        # Add custom config
        custom = self.custom_config.toPlainText().strip()
        if custom:
            lines.append("")
            lines.append("# Custom Configuration")
            lines.extend(custom.split('\n'))
        
        return '\n'.join(lines)