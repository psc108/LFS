import subprocess
import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Callable, Any
from pathlib import Path
import yaml
import threading
import queue
import os
import tempfile

from ..database.db_manager import DatabaseManager
from .downloader import LFSDownloader
from ..analysis.integrated_analyzer import IntegratedFaultAnalyzer

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
    def __init__(self, db_manager: DatabaseManager, repo_manager=None):
        self.db = db_manager
        self.repo = repo_manager
        self.downloader = LFSDownloader(repo_manager, db_manager) if repo_manager else None
        self.fault_analyzer = IntegratedFaultAnalyzer(db_manager, self)
        self.stages = {}
        self.build_queue = queue.Queue()
        self.current_build = None
        self.build_thread = None
        self.build_cancelled = False
        self.sudo_password = None
        self.callbacks = {
            'stage_start': [],
            'stage_complete': [],
            'build_complete': [],
            'build_error': [],
            'sudo_required': []
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
            'version': '12.4',
            'stages': [
                {
                    'name': 'prepare_host',
                    'order': 1,
                    'command': 'bash scripts/prepare_host.sh',
                    'dependencies': [],
                    'rollback_command': 'echo "Host preparation rollback"'
                },
                {
                    'name': 'create_partition',
                    'order': 2,
                    'command': 'bash scripts/create_partition.sh',
                    'dependencies': ['prepare_host'],
                    'rollback_command': 'sudo umount /mnt/lfs || true'
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
                    'name': 'build_temp_system',
                    'order': 5,
                    'command': 'bash scripts/build_temp_system.sh',
                    'dependencies': ['build_toolchain'],
                    'rollback_command': 'rm -rf /mnt/lfs/usr/*'
                },
                {
                    'name': 'enter_chroot',
                    'order': 6,
                    'command': 'bash scripts/enter_chroot.sh',
                    'dependencies': ['build_temp_system'],
                    'rollback_command': 'sudo umount /mnt/lfs/{dev/pts,dev,proc,sys,run} || true'
                },
                {
                    'name': 'build_final_system',
                    'order': 7,
                    'command': 'bash scripts/build_final_system.sh',
                    'dependencies': ['enter_chroot'],
                    'rollback_command': 'echo "Final system rollback"'
                },
                {
                    'name': 'configure_system',
                    'order': 8,
                    'command': 'bash scripts/configure_system.sh',
                    'dependencies': ['build_final_system'],
                    'rollback_command': 'echo "System config rollback"'
                },
                {
                    'name': 'build_kernel',
                    'order': 9,
                    'command': 'bash scripts/build_kernel.sh',
                    'dependencies': ['configure_system'],
                    'rollback_command': 'rm -rf /mnt/lfs/boot/*'
                },
                {
                    'name': 'install_bootloader',
                    'order': 10,
                    'command': 'bash scripts/install_bootloader.sh',
                    'dependencies': ['build_kernel'],
                    'rollback_command': 'rm -rf /mnt/lfs/boot/grub'
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
        
        # Create dedicated Git branch for this build
        build_branch = self._create_build_branch(build_id)
        
        self.db.add_document(
            build_id, 'config', 'Build Configuration', 
            config_content, {'config_path': config_path}
        )
        
        self.current_build = {
            'id': build_id,
            'config_hash': config_hash,
            'stages': dict(self.stages),
            'completed_stages': 0,
            'branch': build_branch
        }
        
        if self.build_thread and self.build_thread.is_alive():
            raise Exception("Another build is already running")
        
        self.build_cancelled = False
        self.build_thread = threading.Thread(target=self._execute_build, args=(build_id,), daemon=True)
        self.build_thread.start()
        
        return build_id
    
    def _execute_build(self, build_id: str):
        try:
            if not self.current_build:
                return
            
            # Commit initial build state to branch
            self._commit_build_start(build_id)
            
            # Setup LFS permissions before starting build
            self._setup_lfs_permissions(build_id)
                
            stages_list = sorted(self.stages.values(), key=lambda x: x.order)
            
            for stage in stages_list:
                if self.build_cancelled:
                    self.db.update_build_status(build_id, 'cancelled', self.current_build.get('completed_stages', 0))
                    return
                
                if not self._check_dependencies(stage):
                    self._fail_stage(build_id, stage, "Dependencies not met")
                    continue
                
                self._execute_stage(build_id, stage)
                
                if stage.status == 'failed' or self.build_cancelled:
                    status = 'cancelled' if self.build_cancelled else 'failed'
                    self.db.update_build_status(build_id, status, self.current_build.get('completed_stages', 0))
                    # Commit failed/cancelled build state
                    self._commit_build_completion(build_id, status)
                    self.emit_event('build_error', {'build_id': build_id, 'stage': stage.name})
                    return
                
                self.current_build['completed_stages'] = self.current_build.get('completed_stages', 0) + 1
                # Commit stage completion to build branch
                self._commit_stage_completion(build_id, stage)
            
            self.db.update_build_status(build_id, 'success', self.current_build.get('completed_stages', 0))
            # Commit successful build completion
            self._commit_build_completion(build_id, 'success')
            self.emit_event('build_complete', {'build_id': build_id, 'status': 'success'})
            
        except Exception as e:
            print(f"Build execution error: {e}")
            try:
                self.db.update_build_status(build_id, 'failed', self.current_build.get('completed_stages', 0) if self.current_build else 0)
                self.db.add_document(
                    build_id, 'error', 'Build Exception', 
                    str(e), {'exception_type': type(e).__name__}
                )
                # Commit failed build state
                if self.current_build:
                    self._commit_build_completion(build_id, 'failed')
                self.emit_event('build_error', {'build_id': build_id, 'error': str(e)})
            except Exception as db_error:
                print(f"Database error during exception handling: {db_error}")
    
    def _check_dependencies(self, stage: BuildStage) -> bool:
        for dep_name in stage.dependencies:
            if dep_name not in self.stages:
                return False
            if self.stages[dep_name].status != 'success':
                return False
        return True
    
    def _execute_stage(self, build_id: str, stage: BuildStage):
        stage.status = 'running'
        self.db.add_stage_log(build_id, stage.name, 'running')
        self.emit_event('stage_start', {'build_id': build_id, 'stage': stage.name})
        
        # Collect warnings for this stage
        stage_warnings = []
        
        try:
            # Modify command to use sudo with password if needed
            command = stage.command
            if self.sudo_password:
                # Set SUDO_ASKPASS environment variable and use -A flag
                import tempfile
                import os
                
                # Create a temporary askpass script
                askpass_script = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh')
                askpass_script.write(f'#!/bin/bash\necho "{self.sudo_password}"\n')
                askpass_script.close()
                os.chmod(askpass_script.name, 0o755)
                
                # Set environment variables for sudo
                env = os.environ.copy()
                env['SUDO_ASKPASS'] = askpass_script.name
                
                # Replace sudo commands to use askpass
                import re
                command = re.sub(r'sudo\s+', 'sudo -A ', command)
                
                # Store askpass script path for cleanup
                self._current_askpass_script = askpass_script.name
            else:
                env = None
            
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            # Read output in real-time with periodic logging
            stdout_lines = []
            stderr_lines = []
            line_count = 0
            
            while True:
                stdout_line = process.stdout.readline()
                stderr_line = process.stderr.readline()
                
                if stdout_line:
                    stdout_lines.append(stdout_line)
                    line_count += 1
                    # Log progress every 50 lines and show key progress in CLI
                    if line_count % 50 == 0:
                        partial_output = ''.join(stdout_lines[-10:])  # Last 10 lines
                        # Show progress indicators in CLI
                        recent_line = stdout_lines[-1].strip() if stdout_lines else ''
                        if recent_line and any(word in recent_line.lower() for word in ['✓', 'completed', 'installing', 'building', 'configuring', 'extracting']):
                            print(f"📋 Build Progress: {recent_line}")
                        else:
                            # Show periodic "still running" indicator
                            print(f"🔄 Stage {stage.name} running... ({line_count} lines processed)")
                        
                        self.db.add_document(
                            build_id, 'log', f'Stage Progress: {stage.name}',
                            f"Lines processed: {line_count}\n\nRecent output:\n{partial_output}",
                            {'stage_order': stage.order, 'progress': True, 'line_count': line_count}
                        )
                
                if stderr_line:
                    stderr_lines.append(stderr_line)
                    line_stripped = stderr_line.strip()
                    if line_stripped:
                        # Check if it's a warning or info message
                        if any(word in stderr_line.lower() for word in ['warning:', 'note:', 'info:', 'makeinfo is missing', 'documentation will not be built']):
                            stage_warnings.append(line_stripped)
                        else:
                            # Log actual errors immediately
                            print(f"🚨 Build Error: {line_stripped}")  # Show in CLI
                            self.db.add_document(
                                build_id, 'log', f'Stage Error Output: {stage.name}',
                                f"Error line: {line_stripped}",
                                {'stage_order': stage.order, 'error_line': True}
                            )
                
                if process.poll() is not None:
                    break
            
            # Get final output
            remaining_stdout, remaining_stderr = process.communicate()
            if remaining_stdout:
                stdout_lines.append(remaining_stdout)
            if remaining_stderr:
                stderr_lines.append(remaining_stderr)
            
            stdout = ''.join(stdout_lines)
            stderr = ''.join(stderr_lines)
            
            # Log final line count and show completion status
            if line_count > 0:
                print(f"📊 Stage {stage.name} generated {line_count} lines of output")
                self.db.add_document(
                    build_id, 'log', f'Stage Output Summary: {stage.name}',
                    f"Total output lines: {line_count}\nStdout size: {len(stdout)} chars\nStderr size: {len(stderr)} chars",
                    {'stage_order': stage.order, 'summary': True, 'total_lines': line_count}
                )
            
            stage.output = stdout
            stage.error = stderr
            
            # Cleanup askpass script if it was created
            if hasattr(self, '_current_askpass_script'):
                try:
                    os.unlink(self._current_askpass_script)
                    delattr(self, '_current_askpass_script')
                except:
                    pass
            
            if process.returncode == 0:
                stage.status = 'success'
                print(f"✓ Stage {stage.name} completed successfully")
                self.db.add_stage_log(build_id, stage.name, 'success', stdout)
                
                self.db.add_document(
                    build_id, 'log', f'Stage: {stage.name}', 
                    f"Command: {stage.command}\n\nOutput:\n{stdout}\n\nErrors:\n{stderr}",
                    {'stage_order': stage.order, 'return_code': process.returncode}
                )
                
                # Save warnings document if any warnings were collected
                if stage_warnings:
                    warnings_content = f"Warnings collected during {stage.name} stage:\n\n"
                    warnings_content += "\n".join(f"• {warning}" for warning in stage_warnings)
                    warnings_content += f"\n\nTotal warnings: {len(stage_warnings)}"
                    
                    self.db.add_document(
                        build_id, 'log', f'Stage Warnings: {stage.name}',
                        warnings_content,
                        {'stage_order': stage.order, 'warning_count': len(stage_warnings), 'warnings': True}
                    )
            else:
                stage.status = 'failed'
                print(f"❌ Stage {stage.name} failed with return code {process.returncode}")
                if stderr.strip():
                    print(f"Error details: {stderr.strip()[:200]}...")  # Show first 200 chars
                self.db.add_stage_log(build_id, stage.name, 'failed', stdout)
                
                # Perform fault analysis on failure
                try:
                    analysis_result = self.fault_analyzer.analyze_build_failure(build_id, stderr + "\n" + stdout)
                    if 'auto_fixes' in analysis_result and analysis_result['auto_fixes']:
                        print(f"🔧 Auto-fix suggestions available for {stage.name}")
                        for fix in analysis_result['auto_fixes']:
                            print(f"   Suggested fix: {fix}")
                except Exception as e:
                    print(f"Fault analysis error: {e}")
                
                self.db.add_document(
                    build_id, 'error', f'Stage Failed: {stage.name}', 
                    f"Command: {stage.command}\n\nOutput:\n{stdout}\n\nErrors:\n{stderr}",
                    {'stage_order': stage.order, 'return_code': process.returncode}
                )
                
                # Save warnings document even for failed stages
                if stage_warnings:
                    warnings_content = f"Warnings collected during {stage.name} stage (before failure):\n\n"
                    warnings_content += "\n".join(f"• {warning}" for warning in stage_warnings)
                    warnings_content += f"\n\nTotal warnings: {len(stage_warnings)}"
                    
                    self.db.add_document(
                        build_id, 'log', f'Stage Warnings: {stage.name}',
                        warnings_content,
                        {'stage_order': stage.order, 'warning_count': len(stage_warnings), 'warnings': True}
                    )
        
        except Exception as e:
            stage.status = 'failed'
            stage.error = str(e)
            self.db.add_stage_log(build_id, stage.name, 'failed', str(e))
        
        self.emit_event('stage_complete', {
            'build_id': build_id, 
            'stage': stage.name, 
            'status': stage.status
        })
    
    def _fail_stage(self, build_id: str, stage: BuildStage, reason: str):
        stage.status = 'failed'
        stage.error = reason
        self.db.add_stage_log(build_id, stage.name, 'failed', reason)
    
    def set_sudo_password(self, password: str):
        """Set sudo password for build operations"""
        self.sudo_password = password
    
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
            self.build_cancelled = True
            self.db.update_build_status(build_id, 'cancelled', self.current_build['completed_stages'])
            self.db.add_document(
                build_id, 'log', 'Build Cancelled',
                'Build was cancelled by user', {'cancelled': True}
            )
    
    def get_build_status(self, build_id: str) -> Dict:
        return self.db.get_build_details(build_id)
    
    def download_lfs_sources(self, build_id: str = None) -> Dict:
        """Download all LFS source packages"""
        if not self.downloader:
            return {"success": [], "failed": [{"package": "downloader", "error": "Repository manager not available"}]}
        
        return self.downloader.download_all_packages(build_id)
    
    def get_download_status(self) -> Dict:
        """Get status of downloaded packages"""
        if not self.downloader:
            return {"downloaded": [], "missing": [], "corrupted": []}
        
        return self.downloader.get_download_status()
    
    def _setup_lfs_permissions(self, build_id: str):
        """Setup LFS directory permissions before build"""
        try:
            if not self.sudo_password:
                self.db.add_document(
                    build_id, 'log', 'LFS Permissions Setup Skipped',
                    'No sudo password available - skipping permissions setup',
                    {'setup': True, 'skipped': True}
                )
                return
            
            # Create askpass script
            askpass_script = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh')
            askpass_script.write(f'#!/bin/bash\necho "{self.sudo_password}"\n')
            askpass_script.close()
            os.chmod(askpass_script.name, 0o755)
            
            env = os.environ.copy()
            env['SUDO_ASKPASS'] = askpass_script.name
            
            try:
                # Setup LFS directories directly
                commands = [
                    ['sudo', '-A', 'mkdir', '-p', '/mnt/lfs/sources'],
                    ['sudo', '-A', 'mkdir', '-p', '/mnt/lfs/tools'],
                    ['sudo', '-A', 'mkdir', '-p', '/mnt/lfs/usr'],
                    ['sudo', '-A', 'mkdir', '-p', '/mnt/lfs/lib'],
                    ['sudo', '-A', 'mkdir', '-p', '/mnt/lfs/lib64'],
                    ['sudo', '-A', 'chmod', '777', '/mnt/lfs/sources'],
                    ['sudo', '-A', 'chmod', '777', '/mnt/lfs/tools'],
                    ['sudo', '-A', 'chmod', '777', '/mnt/lfs/usr'],
                    ['sudo', '-A', 'chmod', '755', '/mnt/lfs/lib'],
                    ['sudo', '-A', 'chmod', '755', '/mnt/lfs/lib64'],
                    ['sudo', '-A', 'chown', '-R', f'{os.getenv("USER", "scottp")}:{os.getenv("USER", "scottp")}', '/mnt/lfs/sources/']
                ]
                
                output_lines = []
                for cmd in commands:
                    try:
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            env=env,
                            timeout=30
                        )
                        output_lines.append(f"Command: {' '.join(cmd)}")
                        output_lines.append(f"Return code: {result.returncode}")
                        if result.stdout:
                            output_lines.append(f"Output: {result.stdout}")
                        if result.stderr:
                            output_lines.append(f"Errors: {result.stderr}")
                        output_lines.append("")
                    except subprocess.TimeoutExpired:
                        output_lines.append(f"Command timed out: {' '.join(cmd)}")
                    except Exception as e:
                        output_lines.append(f"Command failed: {' '.join(cmd)} - {str(e)}")
                
                self.db.add_document(
                    build_id, 'log', 'LFS Permissions Setup',
                    '\n'.join(output_lines),
                    {'setup': True, 'return_code': 0}
                )
                
            finally:
                # Cleanup askpass script
                try:
                    os.unlink(askpass_script.name)
                except:
                    pass
            
        except Exception as e:
            self.db.add_document(
                build_id, 'error', 'LFS Permissions Setup Failed',
                str(e), {'setup': True}
            )
    
    def _create_build_branch(self, build_id: str) -> str:
        """Create a dedicated Git branch for this build"""
        if not self.repo:
            return None
        
        try:
            branch_name = f"build/{build_id}"
            
            # Create and switch to new branch
            if self.repo.create_branch(branch_name):
                self.repo.switch_branch(branch_name)
                return branch_name
            else:
                # If branch creation fails, use current branch
                return self.repo.get_current_branch()
        except Exception as e:
            print(f"Failed to create build branch: {e}")
            return None
    
    def _commit_build_start(self, build_id: str):
        """Commit initial build state to the build branch"""
        if not self.repo or not self.current_build.get('branch'):
            return
        
        try:
            # Stage any changes
            self.repo.stage_all_changes()
            
            # Commit build start
            commit_msg = f"Start build {build_id}\n\nBuild configuration loaded with {len(self.stages)} stages"
            self.repo.commit_changes(commit_msg)
            
        except Exception as e:
            print(f"Failed to commit build start: {e}")
    
    def _commit_stage_completion(self, build_id: str, stage: BuildStage):
        """Commit stage completion to the build branch"""
        if not self.repo or not self.current_build.get('branch'):
            return
        
        try:
            # Stage any changes
            self.repo.stage_all_changes()
            
            # Commit stage completion
            status_emoji = "✅" if stage.status == 'success' else "❌"
            commit_msg = f"{status_emoji} Stage {stage.order}: {stage.name} - {stage.status}\n\nBuild: {build_id}\nStage: {stage.name}\nStatus: {stage.status}"
            
            if stage.status == 'success':
                commit_msg += f"\nCompleted stage {stage.order} of {len(self.stages)}"
            else:
                commit_msg += f"\nFailed at stage {stage.order} of {len(self.stages)}"
            
            self.repo.commit_changes(commit_msg)
            
        except Exception as e:
            print(f"Failed to commit stage completion: {e}")
    
    def _commit_build_completion(self, build_id: str, status: str):
        """Commit final build state to the build branch"""
        if not self.repo or not self.current_build.get('branch'):
            return
        
        try:
            # Stage any changes
            self.repo.stage_all_changes()
            
            # Commit build completion
            status_emoji = {"success": "🎉", "failed": "💥", "cancelled": "🛑"}.get(status, "❓")
            completed_stages = self.current_build.get('completed_stages', 0)
            total_stages = len(self.stages)
            
            commit_msg = f"{status_emoji} Build {build_id} - {status.upper()}\n\n"
            commit_msg += f"Completed {completed_stages} of {total_stages} stages\n"
            commit_msg += f"Final status: {status}\n"
            commit_msg += f"Build branch: {self.current_build.get('branch')}"
            
            self.repo.commit_changes(commit_msg)
            
            # Tag successful builds
            if status == 'success':
                tag_name = f"build-{build_id}-success"
                tag_msg = f"Successful LFS build {build_id}\nCompleted all {total_stages} stages"
                self.repo.create_tag(tag_name, tag_msg)
            
        except Exception as e:
            print(f"Failed to commit build completion: {e}")