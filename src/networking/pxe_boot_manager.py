import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class PXEBootManager:
    def __init__(self, tftp_root: str = "/var/lib/tftpboot", dhcp_config: str = "/etc/dhcp/dhcpd.conf"):
        self.tftp_root = Path(tftp_root)
        self.dhcp_config = Path(dhcp_config)
        self.pxe_configs = self.tftp_root / "pxelinux.cfg"
        self.kernels_dir = self.tftp_root / "kernels"
        self.initrd_dir = self.tftp_root / "initrd"
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure PXE directory structure exists"""
        try:
            for directory in [self.tftp_root, self.pxe_configs, self.kernels_dir, self.initrd_dir]:
                directory.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Use alternative directory for non-root users
            self.tftp_root = Path("/tmp/tftpboot")
            self.pxe_configs = self.tftp_root / "pxelinux.cfg"
            self.kernels_dir = self.tftp_root / "kernels"
            self.initrd_dir = self.tftp_root / "initrd"
            
            for directory in [self.tftp_root, self.pxe_configs, self.kernels_dir, self.initrd_dir]:
                directory.mkdir(parents=True, exist_ok=True)
            
            print(f"⚠️ Using alternative TFTP root: {self.tftp_root}")
    
    def setup_pxe_server(self, network_config: Dict) -> Dict:
        """Setup complete PXE boot server"""
        try:
            # Install required packages
            self._install_pxe_packages()
            
            # Configure TFTP server
            self._configure_tftp_server()
            
            # Configure DHCP server
            self._configure_dhcp_server(network_config)
            
            # Setup PXE boot files
            self._setup_pxe_boot_files()
            
            # Start services
            self._start_pxe_services()
            
            return {
                'success': True,
                'tftp_root': str(self.tftp_root),
                'network_range': network_config.get('network_range'),
                'server_ip': network_config.get('server_ip')
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _install_pxe_packages(self):
        """Install required PXE packages"""
        packages = ['tftp-server', 'dhcp-server', 'syslinux', 'xinetd']
        
        for package in packages:
            try:
                subprocess.run(['dnf', 'install', '-y', package], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                # Try with yum if dnf fails
                subprocess.run(['yum', 'install', '-y', package], check=True, capture_output=True)
    
    def _configure_tftp_server(self):
        """Configure TFTP server"""
        tftp_config = f"""service tftp
{{
    socket_type = dgram
    protocol = udp
    wait = yes
    user = root
    server = /usr/sbin/in.tftpd
    server_args = -s {self.tftp_root}
    disable = no
}}"""
        
        try:
            with open('/etc/xinetd.d/tftp', 'w') as f:
                f.write(tftp_config)
        except PermissionError:
            # Create config in alternative location
            config_file = Path("/tmp/tftp_config")
            config_file.write_text(tftp_config)
            print(f"⚠️ TFTP config written to: {config_file}")
    
    def _configure_dhcp_server(self, network_config: Dict):
        """Configure DHCP server for PXE boot"""
        server_ip = network_config.get('server_ip', '192.168.1.100')
        network_range = network_config.get('network_range', '192.168.1.0')
        subnet_mask = network_config.get('subnet_mask', '255.255.255.0')
        range_start = network_config.get('range_start', '192.168.1.150')
        range_end = network_config.get('range_end', '192.168.1.200')
        
        dhcp_config = f"""
option domain-name "lfs.local";
option domain-name-servers {server_ip};
default-lease-time 600;
max-lease-time 7200;
authoritative;

subnet {network_range} netmask {subnet_mask} {{
    range {range_start} {range_end};
    option routers {server_ip};
    option broadcast-address 192.168.1.255;
    
    # PXE boot configuration
    next-server {server_ip};
    filename "pxelinux.0";
}}
"""
        
        try:
            with open(self.dhcp_config, 'w') as f:
                f.write(dhcp_config)
        except PermissionError:
            # Create config in alternative location
            config_file = Path("/tmp/dhcp_config")
            config_file.write_text(dhcp_config)
            print(f"⚠️ DHCP config written to: {config_file}")
    
    def _setup_pxe_boot_files(self):
        """Setup PXE boot files"""
        # Copy syslinux files
        syslinux_files = [
            '/usr/share/syslinux/pxelinux.0',
            '/usr/share/syslinux/menu.c32',
            '/usr/share/syslinux/ldlinux.c32',
            '/usr/share/syslinux/libcom32.c32',
            '/usr/share/syslinux/libutil.c32'
        ]
        
        for file_path in syslinux_files:
            if Path(file_path).exists():
                shutil.copy2(file_path, self.tftp_root)
    
    def _start_pxe_services(self):
        """Start PXE-related services"""
        services = ['xinetd', 'dhcpd']
        
        for service in services:
            try:
                subprocess.run(['systemctl', 'enable', service], check=True)
                subprocess.run(['systemctl', 'start', service], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Warning: Could not start {service}: {e}")
    
    def add_lfs_boot_entry(self, build_id: str, kernel_path: str, initrd_path: str) -> str:
        """Add LFS build to PXE boot menu"""
        try:
            # Copy kernel and initrd
            kernel_dest = self.kernels_dir / f"lfs-{build_id}-vmlinuz"
            initrd_dest = self.initrd_dir / f"lfs-{build_id}-initrd.img"
            
            shutil.copy2(kernel_path, kernel_dest)
            shutil.copy2(initrd_path, initrd_dest)
            
            # Create PXE config
            pxe_config = f"""
DEFAULT menu.c32
PROMPT 0
TIMEOUT 300

MENU TITLE LFS Network Boot Menu

LABEL lfs-{build_id}
    MENU LABEL LFS Build {build_id}
    KERNEL kernels/lfs-{build_id}-vmlinuz
    APPEND initrd=initrd/lfs-{build_id}-initrd.img root=/dev/nfs nfsroot=192.168.1.100:/mnt/lfs ro ip=dhcp

LABEL local
    MENU LABEL Boot from local disk
    LOCALBOOT 0
"""
            
            config_file = self.pxe_configs / "default"
            with open(config_file, 'w') as f:
                f.write(pxe_config)
            
            return f"lfs-{build_id}"
            
        except Exception as e:
            raise Exception(f"Failed to add PXE boot entry: {e}")
    
    def start_network_boot_setup(self, boot_config: dict) -> str:
        """Start network boot setup and return setup ID"""
        import uuid
        setup_id = f"pxe-{uuid.uuid4().hex[:8]}"
        
        try:
            # Setup PXE server
            result = self.setup_pxe_server(boot_config.get('network', {}))
            
            if not result.get('success'):
                raise Exception(result.get('error', 'PXE setup failed'))
            
            # Add boot entries for specified builds
            for build_entry in boot_config.get('boot_entries', []):
                self.add_lfs_boot_entry(
                    build_entry['build_id'],
                    build_entry['kernel_path'],
                    build_entry['initrd_path']
                )
            
            return setup_id
            
        except Exception as e:
            raise Exception(f"Failed to start network boot setup: {str(e)}")