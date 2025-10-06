import importlib
import inspect
import json
from pathlib import Path
from typing import Dict, List, Any, Callable
from abc import ABC, abstractmethod
from datetime import datetime

class PluginInterface(ABC):
    """Base interface for all plugins"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Return plugin name"""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """Return plugin version"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return plugin description"""
        pass
    
    @abstractmethod
    def initialize(self, context: Dict) -> bool:
        """Initialize plugin with system context"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Cleanup plugin resources"""
        pass

class BuildPlugin(PluginInterface):
    """Base class for build-related plugins"""
    
    def on_build_start(self, build_id: str, config: Dict):
        """Called when build starts"""
        pass
    
    def on_build_complete(self, build_id: str, result: Dict):
        """Called when build completes"""
        pass
    
    def on_stage_start(self, build_id: str, stage_name: str):
        """Called when stage starts"""
        pass
    
    def on_stage_complete(self, build_id: str, stage_name: str, result: Dict):
        """Called when stage completes"""
        pass

class AnalysisPlugin(PluginInterface):
    """Base class for analysis plugins"""
    
    def analyze_build_data(self, build_data: Dict) -> Dict:
        """Analyze build data and return insights"""
        return {}
    
    def get_recommendations(self, analysis_result: Dict) -> List[str]:
        """Get recommendations based on analysis"""
        return []

class NotificationPlugin(PluginInterface):
    """Base class for notification plugins"""
    
    def send_notification(self, event_type: str, data: Dict) -> bool:
        """Send notification for event"""
        return False

class PluginManager:
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(exist_ok=True)
        
        self.loaded_plugins = {}
        self.plugin_hooks = {
            'build_start': [],
            'build_complete': [],
            'stage_start': [],
            'stage_complete': [],
            'analysis': [],
            'notification': []
        }
        
        self.system_context = {}
        self._create_sample_plugins()
    
    def _create_sample_plugins(self):
        """Create sample plugins for demonstration"""
        
        # Build metrics plugin
        metrics_plugin = """
import json
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from plugins.plugin_manager import BuildPlugin

class BuildMetricsPlugin(BuildPlugin):
    def __init__(self):
        self.metrics = {}
    
    def get_name(self):
        return "Build Metrics Collector"
    
    def get_version(self):
        return "1.0.0"
    
    def get_description(self):
        return "Collects detailed build metrics and performance data"
    
    def initialize(self, context):
        self.metrics = {}
        return True
    
    def cleanup(self):
        pass
    
    def on_build_start(self, build_id, config):
        self.metrics[build_id] = {
            'start_time': datetime.now().isoformat(),
            'config': config,
            'stages': {}
        }
    
    def on_build_complete(self, build_id, result):
        if build_id in self.metrics:
            self.metrics[build_id]['end_time'] = datetime.now().isoformat()
            self.metrics[build_id]['result'] = result
            
            # Save metrics to file
            with open(f'build_metrics_{build_id}.json', 'w') as f:
                json.dump(self.metrics[build_id], f, indent=2)
    
    def on_stage_start(self, build_id, stage_name):
        if build_id in self.metrics:
            self.metrics[build_id]['stages'][stage_name] = {
                'start_time': datetime.now().isoformat()
            }
    
    def on_stage_complete(self, build_id, stage_name, result):
        if build_id in self.metrics and stage_name in self.metrics[build_id]['stages']:
            self.metrics[build_id]['stages'][stage_name]['end_time'] = datetime.now().isoformat()
            self.metrics[build_id]['stages'][stage_name]['result'] = result

# Plugin instance
plugin_instance = BuildMetricsPlugin()
"""
        
        metrics_file = self.plugins_dir / "build_metrics_plugin.py"
        if not metrics_file.exists():
            metrics_file.write_text(metrics_plugin)
        
        # Security scanner plugin
        security_plugin = """
import subprocess
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from plugins.plugin_manager import AnalysisPlugin

class SecurityScannerPlugin(AnalysisPlugin):
    def get_name(self):
        return "Security Scanner"
    
    def get_version(self):
        return "1.0.0"
    
    def get_description(self):
        return "Performs security analysis on build artifacts"
    
    def initialize(self, context):
        return True
    
    def cleanup(self):
        pass
    
    def analyze_build_data(self, build_data):
        # Perform security analysis
        security_issues = []
        
        # Check for common security issues
        if 'root_access' in str(build_data):
            security_issues.append("Potential root access detected")
        
        if 'password' in str(build_data).lower():
            security_issues.append("Potential password in build data")
        
        return {
            'security_score': max(0, 100 - len(security_issues) * 20),
            'issues': security_issues,
            'recommendations': self.get_recommendations({'issues': security_issues})
        }
    
    def get_recommendations(self, analysis_result):
        recommendations = []
        issues = analysis_result.get('issues', [])
        
        if any('root' in issue for issue in issues):
            recommendations.append("Review root access requirements")
        
        if any('password' in issue for issue in issues):
            recommendations.append("Remove passwords from build configurations")
        
        return recommendations

# Plugin instance
plugin_instance = SecurityScannerPlugin()
"""
        
        security_file = self.plugins_dir / "security_scanner_plugin.py"
        if not security_file.exists():
            security_file.write_text(security_plugin)
    
    def load_plugin(self, plugin_file: Path) -> bool:
        """Load a single plugin"""
        try:
            # Import plugin module
            spec = importlib.util.spec_from_file_location(plugin_file.stem, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get plugin instance
            if hasattr(module, 'plugin_instance'):
                plugin = module.plugin_instance
                
                # Validate plugin interface
                if not isinstance(plugin, PluginInterface):
                    print(f"Plugin {plugin_file.name} does not implement PluginInterface")
                    return False
                
                # Initialize plugin
                if plugin.initialize(self.system_context):
                    self.loaded_plugins[plugin.get_name()] = plugin
                    self._register_plugin_hooks(plugin)
                    print(f"✅ Loaded plugin: {plugin.get_name()} v{plugin.get_version()}")
                    return True
                else:
                    print(f"❌ Failed to initialize plugin: {plugin.get_name()}")
                    return False
            else:
                print(f"Plugin {plugin_file.name} missing plugin_instance")
                return False
                
        except Exception as e:
            print(f"Error loading plugin {plugin_file.name}: {e}")
            return False
    
    def _register_plugin_hooks(self, plugin):
        """Register plugin hooks based on plugin type"""
        if isinstance(plugin, BuildPlugin):
            self.plugin_hooks['build_start'].append(plugin.on_build_start)
            self.plugin_hooks['build_complete'].append(plugin.on_build_complete)
            self.plugin_hooks['stage_start'].append(plugin.on_stage_start)
            self.plugin_hooks['stage_complete'].append(plugin.on_stage_complete)
        
        if isinstance(plugin, AnalysisPlugin):
            self.plugin_hooks['analysis'].append(plugin.analyze_build_data)
        
        if isinstance(plugin, NotificationPlugin):
            self.plugin_hooks['notification'].append(plugin.send_notification)
    
    def load_all_plugins(self):
        """Load all plugins from plugins directory"""
        loaded_count = 0
        
        for plugin_file in self.plugins_dir.glob("*_plugin.py"):
            if self.load_plugin(plugin_file):
                loaded_count += 1
        
        print(f"📦 Loaded {loaded_count} plugins")
        return loaded_count
    
    def unload_plugin(self, plugin_name: str):
        """Unload a specific plugin"""
        if plugin_name in self.loaded_plugins:
            plugin = self.loaded_plugins[plugin_name]
            plugin.cleanup()
            del self.loaded_plugins[plugin_name]
            
            # Remove from hooks (simplified)
            for hook_list in self.plugin_hooks.values():
                hook_list.clear()
            
            # Re-register remaining plugins
            for remaining_plugin in self.loaded_plugins.values():
                self._register_plugin_hooks(remaining_plugin)
            
            print(f"🗑️ Unloaded plugin: {plugin_name}")
    
    def trigger_hook(self, hook_name: str, *args, **kwargs):
        """Trigger all plugins registered for a specific hook"""
        results = []
        
        if hook_name in self.plugin_hooks:
            for hook_func in self.plugin_hooks[hook_name]:
                try:
                    result = hook_func(*args, **kwargs)
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    print(f"Plugin hook error: {e}")
        
        return results
    
    def get_loaded_plugins(self) -> List[Dict]:
        """Get information about loaded plugins"""
        plugins_info = []
        
        for plugin in self.loaded_plugins.values():
            plugins_info.append({
                'name': plugin.get_name(),
                'version': plugin.get_version(),
                'description': plugin.get_description(),
                'type': type(plugin).__name__
            })
        
        return plugins_info
    
    def set_system_context(self, context: Dict):
        """Set system context for plugins"""
        self.system_context = context
        
        # Update context for loaded plugins
        for plugin in self.loaded_plugins.values():
            try:
                plugin.initialize(context)
            except Exception as e:
                print(f"Error updating plugin context: {e}")
    
    def start_plugin_system(self, plugin_config: dict) -> str:
        """Start plugin system and return system ID"""
        import uuid
        system_id = f"plugins-{uuid.uuid4().hex[:8]}"
        
        try:
            # Set system context
            self.set_system_context(plugin_config.get('system_context', {}))
            
            # Load plugins
            loaded_count = self.load_all_plugins()
            
            print(f"Plugin system {system_id} started with {loaded_count} plugins")
            
            return system_id
            
        except Exception as e:
            raise Exception(f"Failed to start plugin system: {str(e)}")