import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

class ProductionSystemManager:
    """Production-ready system manager integrating all LFS build system components"""
    
    def __init__(self, db_manager=None):
        self.db = db_manager
        self.components = {}
        self.services = {}
        self.system_status = "initializing"
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Initialize all production components
        self._initialize_production_components()
    
    def _initialize_production_components(self):
        """Initialize all production components without demo modes"""
        try:
            print("🚀 Initializing production LFS build system...")
            
            # Import with absolute paths to avoid relative import issues
            import sys
            from pathlib import Path
            
            # Add src directory to path
            src_path = Path(__file__).parent.parent
            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))
            
            # Core build components
            try:
                from analytics.metrics_dashboard import MetricsDashboard
                self.components['metrics_dashboard'] = MetricsDashboard(self.db)
            except ImportError as e:
                print(f"Warning: Could not import MetricsDashboard: {e}")
            
            # Security and compliance
            try:
                from security.vulnerability_scanner import VulnerabilityScanner
                self.components['vulnerability_scanner'] = VulnerabilityScanner()
            except ImportError as e:
                print(f"Warning: Could not import VulnerabilityScanner: {e}")
            
            # Deployment and orchestration
            try:
                from deployment.cloud_deployer import CloudDeployer
                from deployment.iso_generator import ISOGenerator
                from orchestration.parallel_builder import ParallelBuildOrchestrator
                
                self.components['cloud_deployer'] = CloudDeployer()
                self.components['iso_generator'] = ISOGenerator()
                self.components['parallel_builder'] = ParallelBuildOrchestrator()
            except ImportError as e:
                print(f"Warning: Could not import deployment components: {e}")
            
            # Infrastructure services
            try:
                from api.rest_api import APIServer
                from scheduling.build_scheduler import BuildScheduler
                from notifications.notification_system import NotificationSystem
                
                self.components['api_server'] = APIServer()
                self.components['scheduler'] = BuildScheduler(self.db, None)  # Build engine will be set later
                self.components['notifications'] = NotificationSystem()
            except ImportError as e:
                print(f"Warning: Could not import infrastructure services: {e}")
            
            # Advanced features
            try:
                from plugins.plugin_manager import PluginManager
                from containers.container_manager import ContainerManager
                from networking.pxe_boot_manager import PXEBootManager
                from templates.template_manager import BuildTemplateManager
                
                self.components['plugin_manager'] = PluginManager()
                self.components['container_manager'] = ContainerManager()
                self.components['pxe_manager'] = PXEBootManager()
                self.components['template_manager'] = BuildTemplateManager()
            except ImportError as e:
                print(f"Warning: Could not import advanced features: {e}")
            
            # Collaboration and user management
            try:
                from config.settings_manager import SettingsManager
                self.components['settings_manager'] = SettingsManager()
            except ImportError as e:
                print(f"Warning: Could not import settings manager: {e}")
            
            self.system_status = "ready"
            print("✅ Production system initialization complete")
            
        except Exception as e:
            self.system_status = "error"
            print(f"❌ Production system initialization failed: {e}")
            raise
    
    def start_all_services(self) -> Dict[str, Any]:
        """Start all production services"""
        try:
            print("🔄 Starting all production services...")
            
            service_results = {}
            
            # Start API server
            try:
                port = self.components['api_server'].start_server(5000)
                service_results['api_server'] = {'status': 'running', 'port': port}
                self.services['api_server'] = {'port': port, 'status': 'running'}
            except Exception as e:
                service_results['api_server'] = {'status': 'failed', 'error': str(e)}
            
            # Start build scheduler
            try:
                self.components['scheduler'].start_scheduler()
                service_results['scheduler'] = {'status': 'running'}
                self.services['scheduler'] = {'status': 'running'}
            except Exception as e:
                service_results['scheduler'] = {'status': 'failed', 'error': str(e)}
            
            # Initialize plugin system
            try:
                plugin_count = self.components['plugin_manager'].load_all_plugins()
                service_results['plugins'] = {'status': 'running', 'loaded_plugins': plugin_count}
                self.services['plugins'] = {'status': 'running', 'count': plugin_count}
            except Exception as e:
                service_results['plugins'] = {'status': 'failed', 'error': str(e)}
            
            # Start system monitoring
            self.start_system_monitoring()
            service_results['monitoring'] = {'status': 'running'}
            
            print("✅ All production services started")
            return service_results
            
        except Exception as e:
            print(f"❌ Failed to start services: {e}")
            return {'error': str(e)}
    
    def start_system_monitoring(self):
        """Start comprehensive system monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            print("📊 System monitoring started")
    
    def _monitoring_loop(self):
        """Main monitoring loop for production system"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                metrics = self._collect_comprehensive_metrics()
                
                # Store metrics in database
                self._store_system_metrics(metrics)
                
                # Check for alerts
                alerts = self._check_system_alerts(metrics)
                if alerts:
                    self._handle_system_alerts(alerts)
                
                # Sleep for monitoring interval
                time.sleep(60)  # Monitor every minute
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(30)
    
    def _collect_comprehensive_metrics(self) -> Dict:
        """Collect comprehensive system metrics"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'system_status': self.system_status,
            'services': {}
        }
        
        try:
            import psutil
            
            # System resources
            metrics['cpu_percent'] = psutil.cpu_percent(interval=1)
            metrics['memory_percent'] = psutil.virtual_memory().percent
            metrics['disk_percent'] = psutil.disk_usage('/').percent
            
            # Service status
            for service_name, service_info in self.services.items():
                metrics['services'][service_name] = service_info.copy()
            
            # Component health
            metrics['components'] = {}
            for comp_name, component in self.components.items():
                metrics['components'][comp_name] = {
                    'available': component is not None,
                    'type': type(component).__name__
                }
            
        except Exception as e:
            metrics['error'] = str(e)
        
        return metrics
    
    def _store_system_metrics(self, metrics: Dict):
        """Store system metrics in database"""
        try:
            if self.db:
                conn = self.db.connect()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO system_metrics 
                    (timestamp, cpu_percent, memory_percent, disk_percent, 
                     service_count, component_count, raw_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    metrics['timestamp'],
                    metrics.get('cpu_percent', 0),
                    metrics.get('memory_percent', 0),
                    metrics.get('disk_percent', 0),
                    len(metrics.get('services', {})),
                    len(metrics.get('components', {})),
                    str(metrics)
                ))
                
                conn.commit()
                cursor.close()
                
        except Exception as e:
            print(f"Error storing system metrics: {e}")
    
    def _check_system_alerts(self, metrics: Dict) -> List[Dict]:
        """Check for system alerts based on metrics"""
        alerts = []
        
        # CPU alert
        cpu_percent = metrics.get('cpu_percent', 0)
        if cpu_percent > 90:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'critical',
                'message': f'CPU usage at {cpu_percent}%',
                'threshold': 90
            })
        elif cpu_percent > 80:
            alerts.append({
                'type': 'cpu_warning',
                'severity': 'warning',
                'message': f'CPU usage at {cpu_percent}%',
                'threshold': 80
            })
        
        # Memory alert
        memory_percent = metrics.get('memory_percent', 0)
        if memory_percent > 95:
            alerts.append({
                'type': 'memory_critical',
                'severity': 'critical',
                'message': f'Memory usage at {memory_percent}%',
                'threshold': 95
            })
        elif memory_percent > 85:
            alerts.append({
                'type': 'memory_warning',
                'severity': 'warning',
                'message': f'Memory usage at {memory_percent}%',
                'threshold': 85
            })
        
        # Disk alert
        disk_percent = metrics.get('disk_percent', 0)
        if disk_percent > 95:
            alerts.append({
                'type': 'disk_critical',
                'severity': 'critical',
                'message': f'Disk usage at {disk_percent}%',
                'threshold': 95
            })
        elif disk_percent > 90:
            alerts.append({
                'type': 'disk_warning',
                'severity': 'warning',
                'message': f'Disk usage at {disk_percent}%',
                'threshold': 90
            })
        
        return alerts
    
    def _handle_system_alerts(self, alerts: List[Dict]):
        """Handle system alerts"""
        for alert in alerts:
            print(f"🚨 ALERT [{alert['severity'].upper()}]: {alert['message']}")
            
            # Send notifications if configured
            try:
                if 'notifications' in self.components:
                    self.components['notifications'].send_build_notification(
                        'system_alert',
                        {
                            'alert_type': alert['type'],
                            'severity': alert['severity'],
                            'message': alert['message'],
                            'timestamp': datetime.now().isoformat()
                        }
                    )
            except Exception as e:
                print(f"Error sending alert notification: {e}")
    
    def execute_production_workflow(self, workflow_config: Dict) -> str:
        """Execute a complete production workflow"""
        import uuid
        workflow_id = f"workflow-{uuid.uuid4().hex[:8]}"
        
        try:
            print(f"🔄 Starting production workflow {workflow_id}")
            
            workflow_type = workflow_config.get('type', 'build')
            
            if workflow_type == 'build':
                return self._execute_build_workflow(workflow_id, workflow_config)
            elif workflow_type == 'deployment':
                return self._execute_deployment_workflow(workflow_id, workflow_config)
            elif workflow_type == 'security_scan':
                return self._execute_security_workflow(workflow_id, workflow_config)
            elif workflow_type == 'analysis':
                return self._execute_analysis_workflow(workflow_id, workflow_config)
            else:
                raise Exception(f"Unknown workflow type: {workflow_type}")
                
        except Exception as e:
            print(f"❌ Workflow {workflow_id} failed: {e}")
            raise Exception(f"Production workflow failed: {str(e)}")
    
    def _execute_build_workflow(self, workflow_id: str, config: Dict) -> str:
        """Execute production build workflow"""
        try:
            # 1. Security pre-check
            if config.get('security_scan', True):
                scan_id = self.components['vulnerability_scanner'].start_security_scan({
                    'cve_scan': True,
                    'compliance_check': True,
                    'package_analysis': True
                })
                print(f"🔒 Security scan started: {scan_id}")
            
            # 2. Start build (parallel if configured)
            if config.get('parallel_build', False):
                build_id = self.components['parallel_builder'].start_parallel_build(
                    config.get('config_path', ''),
                    config.get('build_config', {})
                )
            else:
                build_id = self.components['build_engine'].start_build(
                    config.get('config_path', ''),
                    config.get('config_name', 'production-build')
                )
            
            print(f"🏗️ Build started: {build_id}")
            
            # 3. Enable ML monitoring
            if config.get('ml_monitoring', True) and 'ml_engine' in self.components:
                try:
                    self.components['ml_engine'].start_build_monitoring(build_id)
                except Exception as e:
                    print(f"Warning: ML monitoring failed: {e}")
            
            # 4. Schedule notifications
            if config.get('notifications', True):
                self.components['notifications'].send_build_notification(
                    'build_started',
                    {'build_id': build_id, 'workflow_id': workflow_id}
                )
            
            return build_id
            
        except Exception as e:
            raise Exception(f"Build workflow failed: {str(e)}")
    
    def _execute_deployment_workflow(self, workflow_id: str, config: Dict) -> str:
        """Execute production deployment workflow"""
        try:
            deployment_type = config.get('deployment_type', 'cloud')
            
            if deployment_type == 'cloud':
                deployment_id = self.components['cloud_deployer'].start_cloud_deployment(config)
            elif deployment_type == 'iso':
                deployment_id = self.components['iso_generator'].start_iso_generation(config)
            elif deployment_type == 'container':
                deployment_id = self.components['container_manager'].start_container_build(config)
            elif deployment_type == 'pxe':
                deployment_id = self.components['pxe_manager'].start_network_boot_setup(config)
            else:
                raise Exception(f"Unknown deployment type: {deployment_type}")
            
            print(f"🚀 Deployment started: {deployment_id}")
            return deployment_id
            
        except Exception as e:
            raise Exception(f"Deployment workflow failed: {str(e)}")
    
    def _execute_security_workflow(self, workflow_id: str, config: Dict) -> str:
        """Execute production security workflow"""
        try:
            # Run comprehensive security scan
            scan_id = self.components['vulnerability_scanner'].start_security_scan(config)
            
            # Run compliance checks
            compliance_results = self.components['compliance_scanner'].run_compliance_scan(
                config.get('standards', ['cis', 'nist'])
            )
            
            print(f"🔒 Security workflow completed: {scan_id}")
            return scan_id
            
        except Exception as e:
            raise Exception(f"Security workflow failed: {str(e)}")
    
    def _execute_analysis_workflow(self, workflow_id: str, config: Dict) -> str:
        """Execute production analysis workflow"""
        try:
            # Run ML analysis
            analysis_results = self.components['ml_engine'].analyze_system_performance()
            
            # Generate metrics dashboard
            metrics = self.components['metrics_dashboard'].get_performance_overview()
            
            # Run fault analysis
            fault_analysis = self.components['fault_analyzer'].analyze_system_health()
            
            print(f"📊 Analysis workflow completed: {workflow_id}")
            return workflow_id
            
        except Exception as e:
            raise Exception(f"Analysis workflow failed: {str(e)}")
    
    def get_production_status(self) -> Dict:
        """Get comprehensive production system status"""
        return {
            'system_status': self.system_status,
            'monitoring_active': self.monitoring_active,
            'services_count': len(self.services),
            'components_count': len(self.components),
            'services': self.services.copy(),
            'components': {
                name: {
                    'available': comp is not None,
                    'type': type(comp).__name__
                } for name, comp in self.components.items()
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def shutdown_system(self):
        """Gracefully shutdown production system"""
        try:
            print("🔄 Shutting down production system...")
            
            # Stop monitoring
            self.monitoring_active = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            
            # Stop services
            if 'api_server' in self.components:
                self.components['api_server'].stop_server()
            
            if 'scheduler' in self.components:
                self.components['scheduler'].stop_scheduler()
            
            # Cleanup components
            for component in self.components.values():
                if hasattr(component, 'cleanup'):
                    try:
                        component.cleanup()
                    except Exception as e:
                        print(f"Component cleanup error: {e}")
            
            self.system_status = "shutdown"
            print("✅ Production system shutdown complete")
            
        except Exception as e:
            print(f"❌ System shutdown error: {e}")