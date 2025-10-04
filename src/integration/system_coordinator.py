from typing import Dict, List, Optional
import threading
import time
from datetime import datetime

class SystemCoordinator:
    """Central coordinator for all system components with integrated fault analysis"""
    
    def __init__(self, db_manager, build_engine=None, repo_manager=None):
        self.db = db_manager
        self.build_engine = build_engine
        self.repo_manager = repo_manager
        
        # Initialize integrated components
        self.fault_analyzer = None
        self.parallel_engine = None
        self.api_server = None
        self.template_manager = None
        self.security_scanner = None
        self.iso_generator = None
        self.user_manager = None
        self.metrics_dashboard = None
        
        # System state
        self.system_status = "initializing"
        self.active_builds = {}
        self.health_monitor_thread = None
        self.monitoring_active = False
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all system components with fault analysis integration"""
        try:
            # Initialize fault analyzer first
            from ..analysis.integrated_analyzer import IntegratedFaultAnalyzer
            self.fault_analyzer = IntegratedFaultAnalyzer(
                self.db, self.build_engine, self.parallel_engine, self.api_server
            )
            
            # Initialize other components with fault analyzer
            from ..orchestration.parallel_builder import ParallelBuildEngine
            self.parallel_engine = ParallelBuildEngine(fault_analyzer=self.fault_analyzer)
            
            from ..api.rest_api import LFSBuildAPI
            self.api_server = LFSBuildAPI(
                self.build_engine, self.db, self.repo_manager, self.fault_analyzer
            )
            
            from ..templates.template_manager import BuildTemplateManager
            self.template_manager = BuildTemplateManager()
            
            from ..security.vulnerability_scanner import VulnerabilityScanner
            self.security_scanner = VulnerabilityScanner()
            
            from ..deployment.iso_generator import ISOGenerator
            self.iso_generator = ISOGenerator()
            
            from ..collaboration.user_manager import UserManager
            self.user_manager = UserManager()
            
            from ..analytics.metrics_dashboard import MetricsDashboard
            self.metrics_dashboard = MetricsDashboard(self.db)
            
            # Update fault analyzer with all components
            self.fault_analyzer.parallel_engine = self.parallel_engine
            self.fault_analyzer.api_server = self.api_server
            
            self.system_status = "ready"
            print("✅ System coordinator initialized successfully")
            
        except Exception as e:
            self.system_status = "error"
            print(f"❌ System coordinator initialization failed: {e}")
    
    def start_system_monitoring(self):
        """Start system health monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.health_monitor_thread = threading.Thread(
                target=self._health_monitor_loop, daemon=True
            )
            self.health_monitor_thread.start()
            print("🔍 System health monitoring started")
    
    def get_system_overview(self) -> Dict:
        """Get comprehensive system overview"""
        try:
            overview = {
                'system_status': self.system_status,
                'monitoring_active': self.monitoring_active,
                'components': {},
                'health_summary': {},
                'recent_activity': {}
            }
            
            # Component status
            components = [
                ('build_engine', self.build_engine),
                ('parallel_engine', self.parallel_engine),
                ('api_server', self.api_server),
                ('fault_analyzer', self.fault_analyzer),
                ('template_manager', self.template_manager),
                ('security_scanner', self.security_scanner),
                ('iso_generator', self.iso_generator),
                ('user_manager', self.user_manager),
                ('metrics_dashboard', self.metrics_dashboard)
            ]
            
            for name, component in components:
                overview['components'][name] = {
                    'available': component is not None,
                    'status': 'active' if component else 'not_initialized'
                }
            
            # Get health summary from fault analyzer
            if self.fault_analyzer:
                overview['health_summary'] = self.fault_analyzer.get_system_health_dashboard()
            
            return overview
            
        except Exception as e:
            return {'error': str(e)}
    
    def _health_monitor_loop(self):
        """Main health monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                health_data = self._collect_system_health()
                
                # Store health metrics in database
                self._store_health_metrics(health_data)
                
                # Sleep for monitoring interval
                time.sleep(60)  # Monitor every minute
                
            except Exception as e:
                print(f"Health monitoring error: {e}")
                time.sleep(30)  # Shorter sleep on error
    
    def _collect_system_health(self) -> Dict:
        """Collect comprehensive system health data"""
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'system_status': self.system_status,
            'active_builds': len(self.active_builds)
        }
        
        try:
            # Get system resource metrics
            import psutil
            health_data['cpu_percent'] = psutil.cpu_percent()
            health_data['memory_percent'] = psutil.virtual_memory().percent
            health_data['disk_percent'] = psutil.disk_usage('/').percent
            
        except Exception as e:
            health_data['error'] = str(e)
        
        return health_data
    
    def _store_health_metrics(self, health_data: Dict):
        """Store health metrics in database"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Store key metrics
            metrics = [
                ('cpu_percent', health_data.get('cpu_percent', 0), 80, 95),
                ('memory_percent', health_data.get('memory_percent', 0), 85, 95),
                ('disk_percent', health_data.get('disk_percent', 0), 90, 98)
            ]
            
            for metric_type, value, warning_threshold, critical_threshold in metrics:
                status = 'OK'
                if value >= critical_threshold:
                    status = 'CRITICAL'
                elif value >= warning_threshold:
                    status = 'WARNING'
                
                cursor.execute("""
                    INSERT INTO system_health_metrics 
                    (metric_type, metric_value, threshold_warning, threshold_critical, status, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    metric_type, value, warning_threshold, critical_threshold, 
                    status, '{"source": "system_coordinator"}'
                ))
            
            conn.commit()
            cursor.close()
            
        except Exception as e:
            print(f"Error storing health metrics: {e}")
    
    def start_build_with_wizard(self, wizard_config: Dict) -> str:
        """Start build using wizard configuration with integrated analysis"""
        try:
            # Generate configuration from template
            if self.template_manager:
                config_yaml = self.template_manager.generate_config_from_template(
                    wizard_config.get('template_id', 'minimal_lfs'),
                    wizard_config
                )
                
                # Save configuration
                config_name = f"{wizard_config.get('name', 'wizard_build')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                config_path = self.repo_manager.add_build_config(config_name, config_yaml)
                
                # Start build with fault analysis enabled
                build_id = self.build_engine.start_build(config_path, config_name)
                
                # Track active build
                self.active_builds[build_id] = {
                    'config': wizard_config,
                    'started_at': datetime.now().isoformat(),
                    'config_path': config_path
                }
                
                return build_id
            else:
                raise Exception("Template manager not available")
                
        except Exception as e:
            raise Exception(f"Failed to start wizard build: {e}")