import os
import subprocess
import stat
import pwd
import grp
import socket
import re
from pathlib import Path


class RealComplianceScanner:
    """Real security compliance scanner that performs actual system checks"""
    
    def __init__(self):
        self.results = []
    
    def scan_filesystem_permissions(self):
        """Check filesystem permissions and configurations"""
        checks = []
        
        # CIS 1.1.1 - Check cramfs filesystem
        try:
            result = subprocess.run(['modprobe', '-n', '-v', 'cramfs'], 
                                  capture_output=True, text=True)
            if 'install /bin/true' in result.stdout or result.returncode != 0:
                checks.append({"id": "1.1.1", "status": "PASS", "desc": "cramfs filesystem disabled"})
            else:
                checks.append({"id": "1.1.1", "status": "FAIL", "desc": "cramfs filesystem not disabled"})
        except:
            checks.append({"id": "1.1.1", "status": "FAIL", "desc": "Could not check cramfs"})
        
        # CIS 5.1.2 - Check /etc/crontab permissions
        try:
            crontab_path = "/etc/crontab"
            if os.path.exists(crontab_path):
                st = os.stat(crontab_path)
                mode = stat.filemode(st.st_mode)
                owner = pwd.getpwuid(st.st_uid).pw_name
                group = grp.getgrgid(st.st_gid).gr_name
                
                if owner == 'root' and group == 'root' and oct(st.st_mode)[-3:] == '600':
                    checks.append({"id": "5.1.2", "status": "PASS", "desc": f"/etc/crontab permissions correct ({mode})"})
                else:
                    checks.append({"id": "5.1.2", "status": "FAIL", "desc": f"/etc/crontab permissions incorrect ({mode}, {owner}:{group})"})
            else:
                checks.append({"id": "5.1.2", "status": "PASS", "desc": "/etc/crontab does not exist"})
        except Exception as e:
            checks.append({"id": "5.1.2", "status": "FAIL", "desc": f"Could not check /etc/crontab: {str(e)}"})
        
        # Check SSH config permissions
        try:
            ssh_config = "/etc/ssh/sshd_config"
            if os.path.exists(ssh_config):
                st = os.stat(ssh_config)
                mode = oct(st.st_mode)[-3:]
                owner = pwd.getpwuid(st.st_uid).pw_name
                
                if owner == 'root' and mode in ['600', '644']:
                    checks.append({"id": "5.2.1", "status": "PASS", "desc": f"SSH config permissions correct ({mode})"})
                else:
                    checks.append({"id": "5.2.1", "status": "FAIL", "desc": f"SSH config permissions incorrect ({mode}, owner: {owner})"})
            else:
                checks.append({"id": "5.2.1", "status": "PASS", "desc": "SSH not installed"})
        except Exception as e:
            checks.append({"id": "5.2.1", "status": "FAIL", "desc": f"Could not check SSH config: {str(e)}"})
        
        return checks
    
    def scan_network_security(self):
        """Validate network security settings"""
        checks = []
        
        # CIS 3.1.1 - Check IP forwarding
        try:
            with open('/proc/sys/net/ipv4/ip_forward', 'r') as f:
                ip_forward = f.read().strip()
            
            if ip_forward == '0':
                checks.append({"id": "3.1.1", "status": "PASS", "desc": "IP forwarding disabled"})
            else:
                checks.append({"id": "3.1.1", "status": "FAIL", "desc": "IP forwarding enabled"})
        except Exception as e:
            checks.append({"id": "3.1.1", "status": "FAIL", "desc": f"Could not check IP forwarding: {str(e)}"})
        
        # CIS 3.2.1 - Check source routed packets
        try:
            with open('/proc/sys/net/ipv4/conf/all/accept_source_route', 'r') as f:
                source_route = f.read().strip()
            
            if source_route == '0':
                checks.append({"id": "3.2.1", "status": "PASS", "desc": "Source routed packets disabled"})
            else:
                checks.append({"id": "3.2.1", "status": "FAIL", "desc": "Source routed packets enabled"})
        except Exception as e:
            checks.append({"id": "3.2.1", "status": "FAIL", "desc": f"Could not check source routing: {str(e)}"})
        
        # Check ICMP redirects
        try:
            with open('/proc/sys/net/ipv4/conf/all/accept_redirects', 'r') as f:
                redirects = f.read().strip()
            
            if redirects == '0':
                checks.append({"id": "3.2.2", "status": "PASS", "desc": "ICMP redirects disabled"})
            else:
                checks.append({"id": "3.2.2", "status": "FAIL", "desc": "ICMP redirects enabled"})
        except Exception as e:
            checks.append({"id": "3.2.2", "status": "FAIL", "desc": f"Could not check ICMP redirects: {str(e)}"})
        
        return checks
    
    def scan_system_services(self):
        """Examine system services and processes"""
        checks = []
        
        # Check if cron is enabled
        try:
            result = subprocess.run(['systemctl', 'is-enabled', 'crond'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and 'enabled' in result.stdout:
                checks.append({"id": "5.1.1", "status": "PASS", "desc": "Cron daemon enabled"})
            else:
                checks.append({"id": "5.1.1", "status": "FAIL", "desc": "Cron daemon not enabled"})
        except Exception as e:
            checks.append({"id": "5.1.1", "status": "FAIL", "desc": f"Could not check cron service: {str(e)}"})
        
        # Check SSH service configuration
        try:
            if os.path.exists('/etc/ssh/sshd_config'):
                with open('/etc/ssh/sshd_config', 'r') as f:
                    ssh_config = f.read()
                
                # Check SSH Protocol
                if re.search(r'^Protocol\s+2', ssh_config, re.MULTILINE):
                    checks.append({"id": "5.2.2", "status": "PASS", "desc": "SSH Protocol 2 configured"})
                elif 'Protocol' not in ssh_config:
                    checks.append({"id": "5.2.2", "status": "PASS", "desc": "SSH Protocol 2 (default)"})
                else:
                    checks.append({"id": "5.2.2", "status": "FAIL", "desc": "SSH Protocol not set to 2"})
                
                # Check SSH LogLevel
                if re.search(r'^LogLevel\s+INFO', ssh_config, re.MULTILINE):
                    checks.append({"id": "5.2.3", "status": "PASS", "desc": "SSH LogLevel set to INFO"})
                else:
                    checks.append({"id": "5.2.3", "status": "FAIL", "desc": "SSH LogLevel not set to INFO"})
            else:
                checks.append({"id": "5.2.2", "status": "PASS", "desc": "SSH not installed"})
                checks.append({"id": "5.2.3", "status": "PASS", "desc": "SSH not installed"})
        except Exception as e:
            checks.append({"id": "5.2.2", "status": "FAIL", "desc": f"Could not check SSH config: {str(e)}"})
            checks.append({"id": "5.2.3", "status": "FAIL", "desc": f"Could not check SSH config: {str(e)}"})
        
        return checks
    
    def scan_access_controls(self):
        """Review audit logs and access controls"""
        checks = []
        
        # NIST AC-2 - Account Management
        try:
            # Check if user accounts are properly configured
            with open('/etc/passwd', 'r') as f:
                passwd_lines = f.readlines()
            
            system_accounts = 0
            user_accounts = 0
            
            for line in passwd_lines:
                if line.strip():
                    parts = line.split(':')
                    if len(parts) >= 3:
                        uid = int(parts[2])
                        if uid < 1000:
                            system_accounts += 1
                        else:
                            user_accounts += 1
            
            checks.append({"id": "AC-2", "status": "PASS", "desc": f"Account management: {system_accounts} system, {user_accounts} user accounts"})
        except Exception as e:
            checks.append({"id": "AC-2", "status": "FAIL", "desc": f"Could not check accounts: {str(e)}"})
        
        # NIST IA-2 - Authentication
        try:
            # Check password policies
            if os.path.exists('/etc/login.defs'):
                with open('/etc/login.defs', 'r') as f:
                    login_defs = f.read()
                
                if 'PASS_MIN_LEN' in login_defs:
                    checks.append({"id": "IA-2", "status": "PASS", "desc": "Password policies configured"})
                else:
                    checks.append({"id": "IA-2", "status": "FAIL", "desc": "Password policies not configured"})
            else:
                checks.append({"id": "IA-2", "status": "FAIL", "desc": "/etc/login.defs not found"})
        except Exception as e:
            checks.append({"id": "IA-2", "status": "FAIL", "desc": f"Could not check authentication: {str(e)}"})
        
        return checks
    
    def scan_system_integrity(self):
        """Perform system integrity checks"""
        checks = []
        
        # NIST SI-2 - Flaw Remediation
        try:
            # Check if package manager is available for updates
            result = subprocess.run(['which', 'dnf'], capture_output=True, text=True)
            if result.returncode == 0:
                # Check for available updates
                result = subprocess.run(['dnf', 'check-update'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    checks.append({"id": "SI-2", "status": "PASS", "desc": "System up to date"})
                else:
                    update_count = len([line for line in result.stdout.split('\n') 
                                      if line and not line.startswith(' ') and '.' in line])
                    checks.append({"id": "SI-2", "status": "FAIL", "desc": f"{update_count} updates available"})
            else:
                checks.append({"id": "SI-2", "status": "FAIL", "desc": "Package manager not found"})
        except Exception as e:
            checks.append({"id": "SI-2", "status": "FAIL", "desc": f"Could not check updates: {str(e)}"})
        
        # NIST SI-4 - System Monitoring
        try:
            # Check if auditd is running
            result = subprocess.run(['systemctl', 'is-active', 'auditd'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and 'active' in result.stdout:
                checks.append({"id": "SI-4", "status": "PASS", "desc": "Audit daemon active"})
            else:
                checks.append({"id": "SI-4", "status": "FAIL", "desc": "Audit daemon not active"})
        except Exception as e:
            checks.append({"id": "SI-4", "status": "FAIL", "desc": f"Could not check audit daemon: {str(e)}"})
        
        return checks
    
    def perform_full_scan(self):
        """Perform complete security assessment"""
        all_checks = []
        
        # Run all scan categories
        all_checks.extend(self.scan_filesystem_permissions())
        all_checks.extend(self.scan_network_security())
        all_checks.extend(self.scan_system_services())
        all_checks.extend(self.scan_access_controls())
        all_checks.extend(self.scan_system_integrity())
        
        # Calculate summary
        total_checks = len(all_checks)
        passed_checks = len([c for c in all_checks if c['status'] == 'PASS'])
        failed_checks = total_checks - passed_checks
        compliance_score = round((passed_checks / total_checks) * 100, 1) if total_checks > 0 else 0
        
        return {
            'results': all_checks,
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'compliance_score': compliance_score
        }