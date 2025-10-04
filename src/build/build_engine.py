import subprocess
import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Callable, Any
from pathlib import Path
import yaml
import threading
import queue

from ..database.db_manager import DatabaseManager

class BuildStage:
    def __init__(self, name: str, order: int, command: str, 
                 dependencies: List[str] = None, rollback_command: str = ""):
        self.name = name
        self.order = order
        self.command = command
        self.dependencies = dependencies or []
        self.rollback_command = rollback_command
        self.status = "pending"
        self.output = ""
        self.error = ""

class BuildEngine:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.stages = {}
        self.build_queue = queue.Queue()
        self.current_build = None
        self.build_thread = None
        self.callbacks = {
            'stage_start': [],
            'stage_complete': [],
            'build_complete': [],
            'build_error': []
        }
    
    def register_callback(self, event: str, callback: Callable):
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def emit_event(self, event: str, data: Any):
        for callback in self.callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def load_build_config(self, config_path: str):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.stages.clear()
        for stage_config in config.get('stages', []):
            stage = BuildStage(
                name=stage_config['name'],
                order=stage_config['order'],
                command=stage_config['command'],
                dependencies=stage_config.get('dependencies', []),
                rollback_command=stage_config.get('rollback_command', '')
            )
            self.stages[stage.name] = stage
    
    def create_default_lfs_config(self, output_path: str):
        default_config = {
            'name': 'Linux From Scratch Build',
            'version': '12.0',
            'stages': [
                {
                    'name': 'prepare_host',
                    'order': 1,
                    'command': 'bash scripts/prepare_host.sh',
                    'dependencies': [],
                    'rollback_command': 'bash scripts/cleanup_host.sh'
                },
                {
                    'name': 'create_partition',
                    'order': 2,
                    'command': 'bash scripts/create_partition.sh',
                    'dependencies': ['prepare_host'],
                    'rollback_command': 'bash scripts/remove_partition.sh'
                },
                {
                    'name': 'download_sources',
                    'order': 3,
                    'command': 'bash scripts/download_sources.sh',
                    'dependencies': ['create_partition'],
                    'rollback_command': 'rm -rf /mnt/lfs/sources/*'
                },
                {
                    'name': 'build_toolchain',
                    'order': 4,
                    'command': 'bash scripts/build_toolchain.sh',
                    'dependencies': ['download_sources'],
                    'rollback_command': 'rm -rf /mnt/lfs/tools/*'
                },
                {
                    'name': 'build_system',
                    'order': 5,
                    'command': 'bash scripts/build_system.sh',
                    'dependencies': ['build_toolchain'],
                    'rollback_command': 'bash scripts/cleanup_system.sh'
                },
                {
                    'name': 'configure_system',
                    'order': 6,
                    'command': 'bash scripts/configure_system.sh',
                    'dependencies': ['build_system'],
                    'rollback_command': 'bash scripts/reset_config.sh'
                },
                {
                    'name': 'build_kernel',
                    'order': 7,
                    'command': 'bash scripts/build_kernel.sh',
                    'dependencies': ['configure_system'],
                    'rollback_command': 'rm -rf /mnt/lfs/boot/*'
                },
                {
                    'name': 'finalize_system',
                    'order': 8,
                    'command': 'bash scripts/finalize_system.sh',
                    'dependencies': ['build_kernel'],
                    'rollback_command': 'bash scripts/cleanup_final.sh'
                }
            ]
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
    
    def start_build(self, config_path: str, build_name: str = None) -> str:
        self.load_build_config(config_path)
        
        build_id = build_name or f"lfs-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
        
        with open(config_path, 'r') as f:
            config_content = f.read()
        config_hash = hashlib.sha256(config_content.encode()).hexdigest()[:16]
        
        total_stages = len(self.stages)
        
        if not self.db.create_build(build_id, config_hash, total_stages):
            raise Exception("Failed to create build record")
        
        self.db.add_document(
            build_id, 'config', 'Build Configuration', 
            config_content, {'config_path': config_path}
        )
        
        self.current_build = {
            'id': build_id,
            'config_hash': config_hash,
            'stages': dict(self.stages),
            'completed_stages': 0
        }
        
        if self.build_thread and self.build_thread.is_alive():
            raise Exception("Another build is already running")
        
        self.build_thread = threading.Thread(target=self._execute_build, args=(build_id,))
        self.build_thread.start()
        
        return build_id
    
    def _execute_build(self, build_id: str):
        try:
            stages_list = sorted(self.stages.values(), key=lambda x: x.order)
            
            for stage in stages_list:
                if not self._check_dependencies(stage):
                    self._fail_stage(build_id, stage, "Dependencies not met")
                    continue
                
                self._execute_stage(build_id, stage)
                
                if stage.status == 'failed':
                    self.db.update_build_status(build_id, 'failed', self.current_build['completed_stages'])
                    self.emit_event('build_error', {'build_id': build_id, 'stage': stage.name})
                    return
                
                self.current_build['completed_stages'] += 1
            
            self.db.update_build_status(build_id, 'success', self.current_build['completed_stages'])
            self.emit_event('build_complete', {'build_id': build_id, 'status': 'success'})
            
        except Exception as e:
            self.db.update_build_status(build_id, 'failed', self.current_build['completed_stages'])
            self.db.add_document(
                build_id, 'error', 'Build Exception', 
                str(e), {'exception_type': type(e).__name__}
            )
            self.emit_event('build_error', {'build_id': build_id, 'error': str(e)})
    
    def _check_dependencies(self, stage: BuildStage) -> bool:
        for dep_name in stage.dependencies:
            if dep_name not in self.stages:
                return False
            if self.stages[dep_name].status != 'success':
                return False
        return True
    
    def _execute_stage(self, build_id: str, stage: BuildStage):
        stage.status = 'running'
        self.db.add_stage_log(build_id, stage.name, stage.order, 'running')
        self.emit_event('stage_start', {'build_id': build_id, 'stage': stage.name})
        
        try:
            process = subprocess.Popen(
                stage.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            
            stage.output = stdout
            stage.error = stderr
            
            if process.returncode == 0:
                stage.status = 'success'
                self.db.add_stage_log(build_id, stage.name, stage.order, 'success', stdout, stderr)
                
                self.db.add_document(
                    build_id, 'log', f'Stage: {stage.name}', 
                    f"Command: {stage.command}\n\nOutput:\n{stdout}\n\nErrors:\n{stderr}",
                    {'stage_order': stage.order, 'return_code': process.returncode}
                )
            else:
                stage.status = 'failed'
                self.db.add_stage_log(build_id, stage.name, stage.order, 'failed', stdout, stderr)
                
                self.db.add_document(
                    build_id, 'error', f'Stage Failed: {stage.name}', 
                    f"Command: {stage.command}\n\nOutput:\n{stdout}\n\nErrors:\n{stderr}",
                    {'stage_order': stage.order, 'return_code': process.returncode}
                )
        
        except Exception as e:
            stage.status = 'failed'
            stage.error = str(e)
            self.db.add_stage_log(build_id, stage.name, stage.order, 'failed', "", str(e))
        
        self.emit_event('stage_complete', {
            'build_id': build_id, 
            'stage': stage.name, 
            'status': stage.status
        })
    
    def _fail_stage(self, build_id: str, stage: BuildStage, reason: str):
        stage.status = 'failed'
        stage.error = reason
        self.db.add_stage_log(build_id, stage.name, stage.order, 'failed', "", reason)
    
    def rollback_stage(self, build_id: str, stage_name: str) -> bool:
        if stage_name not in self.stages:
            return False
        
        stage = self.stages[stage_name]
        if not stage.rollback_command:
            return False
        
        try:
            process = subprocess.run(
                stage.rollback_command,
                shell=True,
                capture_output=True,
                text=True
            )
            
            self.db.add_document(
                build_id, 'log', f'Rollback: {stage_name}', 
                f"Command: {stage.rollback_command}\n\nOutput:\n{process.stdout}\n\nErrors:\n{process.stderr}",
                {'rollback': True, 'return_code': process.returncode}
            )
            
            return process.returncode == 0
        
        except Exception as e:
            self.db.add_document(
                build_id, 'error', f'Rollback Failed: {stage_name}', 
                str(e), {'rollback': True}
            )
            return False
    
    def cancel_build(self, build_id: str):
        if self.current_build and self.current_build['id'] == build_id:
            self.db.update_build_status(build_id, 'cancelled', self.current_build['completed_stages'])
            # Note: In a real implementation, you'd need to handle process termination
    
    def get_build_status(self, build_id: str) -> Dict:
        return self.db.get_build_details(build_id)