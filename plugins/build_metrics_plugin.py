
import json
from datetime import datetime
from src.plugins.plugin_manager import BuildPlugin

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
