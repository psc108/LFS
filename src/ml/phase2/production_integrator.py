"""
Production-Ready Cross-System Integration
Real integration with Git, CI/CD, and Security systems
"""

import subprocess
import json
import os
from typing import Dict, List, Optional
import logging

class ProductionGitIntegrator:
    """Production Git integration using actual Git commands"""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.logger = logging.getLogger(__name__)
    
    def extract_real_git_features(self, build_id: str) -> Dict:
        """Extract real Git features using Git commands"""
        try:
            features = {}
            
            # Get branch information
            result = subprocess.run(['git', 'branch', '-a'], 
                                  capture_output=True, text=True, cwd=self.repo_path)
            if result.returncode == 0:
                branches = result.stdout.strip().split('\n')
                features['branch_count'] = len([b for b in branches if b.strip()])
                features['has_remote_branches'] = any('remotes/' in b for b in branches)
            
            # Get commit activity
            result = subprocess.run(['git', 'log', '--oneline', '--since=24.hours'], 
                                  capture_output=True, text=True, cwd=self.repo_path)
            if result.returncode == 0:
                recent_commits = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
                features['recent_commits'] = recent_commits
            
            # Get repository status
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, cwd=self.repo_path)
            if result.returncode == 0:
                uncommitted_files = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
                features['uncommitted_changes'] = min(1.0, uncommitted_files / 10.0)
            
            # Get repository size
            result = subprocess.run(['git', 'count-objects', '-v'], 
                                  capture_output=True, text=True, cwd=self.repo_path)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('size '):
                        repo_size_kb = int(line.split()[1])
                        features['repo_size_mb'] = repo_size_kb / 1024
                        break
            
            return features
            
        except Exception as e:
            self.logger.error(f"Git feature extraction failed: {e}")
            return {}

class ProductionSystemMonitor:
    """Production system monitoring for real metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_real_system_metrics(self) -> Dict:
        """Get real system metrics using psutil and system commands"""
        try:
            import psutil
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024**3)
            
            # Process metrics
            process_count = len(psutil.pids())
            
            return {
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'load_average': load_avg,
                'memory_percent': memory_percent,
                'memory_available_gb': memory_available_gb,
                'disk_percent': disk_percent,
                'disk_free_gb': disk_free_gb,
                'process_count': process_count,
                'system_load_factor': min(1.0, load_avg / cpu_count) if cpu_count > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"System metrics collection failed: {e}")
            return {}

class ProductionSecurityIntegrator:
    """Production security integration with actual compliance checks"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_real_security_metrics(self) -> Dict:
        """Get real security metrics from system"""
        try:
            metrics = {}
            
            # Check file permissions on critical directories
            lfs_path = '/mnt/lfs'
            if os.path.exists(lfs_path):
                stat_info = os.stat(lfs_path)
                metrics['lfs_permissions_secure'] = (stat_info.st_mode & 0o777) == 0o755
            
            # Check for running security services
            try:
                result = subprocess.run(['systemctl', 'is-active', 'firewalld'], 
                                      capture_output=True, text=True)
                metrics['firewall_active'] = result.returncode == 0
            except:
                metrics['firewall_active'] = False
            
            # Check SSH configuration security
            ssh_config = '/etc/ssh/sshd_config'
            if os.path.exists(ssh_config):
                try:
                    with open(ssh_config, 'r') as f:
                        config_content = f.read()
                        metrics['ssh_root_login_disabled'] = 'PermitRootLogin no' in config_content
                        metrics['ssh_password_auth_disabled'] = 'PasswordAuthentication no' in config_content
                except:
                    metrics['ssh_root_login_disabled'] = False
                    metrics['ssh_password_auth_disabled'] = False
            
            # Calculate overall security score
            security_checks = [
                metrics.get('lfs_permissions_secure', False),
                metrics.get('firewall_active', False),
                metrics.get('ssh_root_login_disabled', False)
            ]
            metrics['security_score'] = sum(security_checks) / len(security_checks)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Security metrics collection failed: {e}")
            return {}

class ProductionCrossSystemIntegrator:
    """Production cross-system integrator with real data"""
    
    def __init__(self, db_manager, repo_path: str = "."):
        self.db = db_manager
        self.git_integrator = ProductionGitIntegrator(repo_path)
        self.system_monitor = ProductionSystemMonitor()
        self.security_integrator = ProductionSecurityIntegrator()
        self.logger = logging.getLogger(__name__)
    
    def get_production_features(self, build_id: str) -> Dict:
        """Get production-ready features from all systems"""
        features = {}
        
        # Real Git features
        git_features = self.git_integrator.extract_real_git_features(build_id)
        features.update({f'git_{k}': v for k, v in git_features.items()})
        
        # Real system metrics
        system_features = self.system_monitor.get_real_system_metrics()
        features.update({f'system_{k}': v for k, v in system_features.items()})
        
        # Real security metrics
        security_features = self.security_integrator.get_real_security_metrics()
        features.update({f'security_{k}': v for k, v in security_features.items()})
        
        # Database-derived features
        db_features = self._get_database_features(build_id)
        features.update(db_features)
        
        return features
    
    def _get_database_features(self, build_id: str) -> Dict:
        """Extract features from database with real queries"""
        try:
            # Build history features
            recent_builds = self.db.execute_query("""
                SELECT status, duration_seconds, 
                       TIMESTAMPDIFF(HOUR, start_time, NOW()) as hours_ago
                FROM builds 
                WHERE start_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY start_time DESC
                LIMIT 20
            """, fetch=True)
            
            if recent_builds:
                success_rate = len([b for b in recent_builds if b['status'] == 'success']) / len(recent_builds)
                avg_duration = sum(b['duration_seconds'] or 0 for b in recent_builds) / len(recent_builds)
                
                return {
                    'db_recent_success_rate': success_rate,
                    'db_avg_duration_hours': avg_duration / 3600 if avg_duration else 0,
                    'db_build_frequency': len(recent_builds) / 7.0  # builds per day
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Database feature extraction failed: {e}")
            return {}