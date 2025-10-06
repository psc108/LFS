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
        self.current_process = None
        self.sudo_password = None
        self.callbacks = {
            'stage_start': [],
            'stage_complete': [],
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
        
        # Generate unique build ID
        if build_name:
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            unique_suffix = str(uuid.uuid4())[:8]
            build_id = f"{build_name}-{timestamp}-{unique_suffix}"
        else:
            build_id = f"lfs-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
        
        with open(config_path, 'r') as f:
            config_content = f.read()
        config_hash = hashlib.sha256(config_content.encode()).hexdigest()[:16]
        
        total_stages = len(self.stages)
        
        if not self.db.create_build(build_id, build_name or "unnamed-build", total_stages):
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
            
            # Setup LFS permissions before starting build (non-blocking)
            try:
                self._setup_lfs_permissions(build_id)
            except Exception as e:
                print(f"⚠️ Permission setup failed, continuing build: {e}")
                self.db.add_document(
                    build_id, 'log', 'Permission Setup Warning',
                    f'Permission setup failed but build will continue: {str(e)}',
                    {'setup': True, 'warning': True}
                )
                
            print(f"🚀 Starting build execution for {build_id}")
            print(f"📁 Current working directory: {os.getcwd()}")
            print(f"📝 Total stages to execute: {len(self.stages)}")
            
            # Log build start
            self.db.add_document(
                build_id, 'log', 'Build Execution Started',
                f'Build {build_id} execution started\n'
                f'Working directory: {os.getcwd()}\n'
                f'Total stages: {len(self.stages)}\n'
                f'Stages: {", ".join([s.name for s in self.stages.values()])}',
                {'build_start': True}
            )
            
            stages_list = sorted(self.stages.values(), key=lambda x: x.order)
            print(f"📅 Executing {len(stages_list)} stages in order: {[s.name for s in stages_list]}")
            
            for i, stage in enumerate(stages_list):
                print(f"🔄 Stage {i+1}/{len(stages_list)}: {stage.name} (order: {stage.order})")
                
                if self.build_cancelled:
                    print(f"🚫 Build cancelled before stage {stage.name}")
                    self.db.update_build_status(build_id, 'cancelled', self.current_build.get('completed_stages', 0))
                    return
                
                if not self._check_dependencies(stage):
                    self._fail_stage(build_id, stage, "Dependencies not met")
                    continue
                
                self._execute_stage(build_id, stage)
                
                if stage.status == 'failed' or self.build_cancelled:
                    status = 'cancelled' if self.build_cancelled else 'failed'
                    self.db.update_build_status(build_id, status, self.current_build.get('completed_stages', 0))
                    # Perform automatic cleanup on failure
                    self._perform_build_cleanup(build_id, status, stage.name)
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
                # Perform automatic cleanup on exception
                self._perform_build_cleanup(build_id, 'failed', 'build_exception')
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
            env = os.environ.copy()  # Always copy environment
            
            if self.sudo_password:
                # Set SUDO_ASKPASS environment variable and use -A flag
                import tempfile
                
                # Create a temporary askpass script
                askpass_script = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh')
                askpass_script.write(f'#!/bin/bash\necho "{self.sudo_password}"\n')
                askpass_script.close()
                os.chmod(askpass_script.name, 0o755)
                
                # Set environment variables for sudo
                env['SUDO_ASKPASS'] = askpass_script.name
                
                # Store askpass script path for cleanup
                self._current_askpass_script = askpass_script.name
                
                print(f"🔐 Using sudo with askpass script: {askpass_script.name} for stage {stage.name}")
            else:
                # If no sudo password provided, ensure non-interactive mode
                env['SUDO_NONINTERACTIVE'] = '1'
                print(f"⚠️ No sudo password provided - build will fail on sudo commands")
            
            # Add timeout and better error handling for stuck processes
            print(f"🚀 Starting stage {stage.name} with command: {command[:100]}...")
            
            # Ensure we're in the LFS project directory where scripts exist
            project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            print(f"📁 Working directory: {project_dir}")
            
            # Verify scripts directory exists
            scripts_dir = os.path.join(project_dir, 'scripts')
            if not os.path.exists(scripts_dir):
                raise Exception(f"Scripts directory not found: {scripts_dir}")
            
            # Check if the specific script exists for this stage
            if 'scripts/' in command:
                script_name = command.split('scripts/')[1].split()[0]
                script_path = os.path.join(scripts_dir, script_name)
                if not os.path.exists(script_path):
                    raise Exception(f"Script not found: {script_path}")
                print(f"✅ Script found: {script_path}")
            
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,  # Prevent stdin input
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,
                cwd=project_dir  # Run from project root where scripts/ directory exists
            )
            
            # Store current process for cancellation
            self.current_process = process
            
            # Add timeout tracking with shorter timeout for debugging
            import time
            start_time = time.time()
            last_output_time = start_time
            timeout_seconds = 1800  # 30 minutes timeout per stage (reduced for debugging)
            
            # Log stage start with more details
            self.db.add_document(
                build_id, 'log', f'Stage Started: {stage.name}',
                f"Stage {stage.name} started at {datetime.now()}\n"
                f"Command: {command}\n"
                f"Working directory: {project_dir}\n"
                f"Timeout: {timeout_seconds} seconds",
                {'stage_order': stage.order, 'stage_start': True}
            )
            
            # Read output in real-time with periodic logging
            stdout_lines = []
            stderr_lines = []
            line_count = 0
            
            while True:
                # Check for cancellation
                if self.build_cancelled:
                    try:
                        process.terminate()
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    stage.status = 'cancelled'
                    stage.error = 'Build was cancelled by user'
                    self.current_process = None
                    return
                
                # Check for timeout (no output for too long) and log status periodically
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # Log status every 2 minutes
                if int(elapsed_time) % 120 == 0 and int(elapsed_time) > 0:
                    print(f"⏱️ Stage {stage.name} running for {int(elapsed_time/60)} minutes, {line_count} lines processed")
                    self.db.add_document(
                        build_id, 'log', f'Stage Status: {stage.name}',
                        f"Stage running for {int(elapsed_time/60)} minutes\n"
                        f"Lines processed: {line_count}\n"
                        f"Last output: {int((current_time - last_output_time)/60)} minutes ago",
                        {'stage_order': stage.order, 'status_update': True, 'elapsed_minutes': int(elapsed_time/60)}
                    )
                
                if current_time - last_output_time > timeout_seconds:
                    print(f"⏰ Stage {stage.name} timed out after {timeout_seconds} seconds of no output")
                    self.db.add_document(
                        build_id, 'error', f'Stage Timeout: {stage.name}',
                        f"Stage timed out after {timeout_seconds} seconds of no output\n"
                        f"Total runtime: {int(elapsed_time/60)} minutes\n"
                        f"Lines processed: {line_count}",
                        {'stage_order': stage.order, 'timeout': True}
                    )
                    try:
                        process.terminate()
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    stage.status = 'failed'
                    stage.error = f'Stage timed out after {timeout_seconds} seconds of no output'
                    self.current_process = None
                    return
                
                stdout_line = process.stdout.readline()
                stderr_line = process.stderr.readline()
                
                # Update last output time if we got any output
                if stdout_line or stderr_line:
                    last_output_time = current_time
                
                if stdout_line:
                    stdout_lines.append(stdout_line)
                    line_count += 1
                    
                    # Show every line in CLI for debugging stuck builds
                    line_stripped = stdout_line.strip()
                    if line_stripped:
                        print(f"📋 {stage.name}: {line_stripped}")
                    
                    # Log progress every 5 lines for better monitoring of stuck builds
                    if line_count % 5 == 0:
                        partial_output = ''.join(stdout_lines[-3:])  # Last 3 lines
                        print(f"🔄 Stage {stage.name} running... ({line_count} lines processed)")
                        
                        self.db.add_document(
                            build_id, 'log', f'Stage Progress: {stage.name}',
                            f"Lines processed: {line_count}\n\nRecent output:\n{partial_output}",
                            {'stage_order': stage.order, 'progress': True, 'line_count': line_count}
                        )
                    
                    # Also log every significant line immediately to database
                    if any(keyword in line_stripped.lower() for keyword in 
                           ['building', 'compiling', 'installing', 'extracting', 'configuring', 'make', 'gcc', 'error', 'failed']):
                        self.db.add_document(
                            build_id, 'log', f'Stage Activity: {stage.name}',
                            f"Activity: {line_stripped}",
                            {'stage_order': stage.order, 'activity': True, 'timestamp': datetime.now().isoformat()}
                        )
                
                if stderr_line:
                    stderr_lines.append(stderr_line)
                    line_stripped = stderr_line.strip()
                    if line_stripped:
                        # Check for sudo password prompts
                        if any(prompt in line_stripped.lower() for prompt in [
                            'password for', '[sudo] password', 'sudo password', 'enter password'
                        ]):
                            print(f"🚨 SUDO PROMPT DETECTED in {stage.name}: {line_stripped}")
                            self.db.add_document(
                                build_id, 'error', f'Sudo Prompt Detected: {stage.name}',
                                f"Sudo password prompt detected in CLI: {line_stripped}\n\n"
                                f"This indicates the sudo password was not properly provided or configured.\n"
                                f"The build will likely hang waiting for password input.\n\n"
                                f"Solution: Cancel this build and restart with proper sudo password.",
                                {'stage_order': stage.order, 'sudo_prompt': True, 'critical': True}
                            )
                            # This is a critical error - the build will hang
                            stage.status = 'failed'
                            stage.error = f'Sudo password prompt detected: {line_stripped}'
                            try:
                                process.terminate()
                                process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                process.kill()
                            self.current_process = None
                            return
                        
                        # Show all stderr output for debugging
                        print(f"🚨 {stage.name} stderr: {line_stripped}")
                        
                        # Check if it's a warning or info message
                        if any(word in stderr_line.lower() for word in ['warning:', 'note:', 'info:', 'makeinfo is missing', 'documentation will not be built']):
                            stage_warnings.append(line_stripped)
                        else:
                            # Log actual errors immediately
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
            
            # Clear current process reference
            self.current_process = None
            
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
                print(f"✅ Stage {stage.name} completed successfully (return code 0)")
                print(f"📊 Stage output: {len(stdout)} chars stdout, {len(stderr)} chars stderr")
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
                print(f"📊 Stage output: {len(stdout)} chars stdout, {len(stderr)} chars stderr")
                if stderr.strip():
                    print(f"🔍 Error details: {stderr.strip()[:500]}...")  # Show first 500 chars
                if stdout.strip():
                    print(f"🔍 Last stdout: {stdout.strip()[-500:]}...")  # Show last 500 chars
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
            print(f"❌ Exception in stage {stage.name}: {str(e)}")
            self.db.add_stage_log(build_id, stage.name, 'failed', str(e))
            # Clear current process reference on exception
            self.current_process = None
        
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
            
            # Terminate current process if running
            if self.current_process:
                try:
                    print(f"🛑 Terminating running process for build {build_id} (PID: {self.current_process.pid})")
                    
                    # Try to kill the entire process group to catch child processes
                    import os
                    import signal
                    try:
                        os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                        print(f"💫 Sent SIGTERM to process group {os.getpgid(self.current_process.pid)}")
                    except:
                        # Fallback to just the main process
                        self.current_process.terminate()
                        print(f"💫 Sent SIGTERM to process {self.current_process.pid}")
                    
                    # Give process 5 seconds to terminate gracefully
                    try:
                        self.current_process.wait(timeout=5)
                        print(f"✅ Process terminated gracefully")
                    except subprocess.TimeoutExpired:
                        print(f"🔥 Force killing process for build {build_id}")
                        try:
                            os.killpg(os.getpgid(self.current_process.pid), signal.SIGKILL)
                        except:
                            self.current_process.kill()
                        self.current_process.wait()
                        print(f"💫 Process force killed")
                    
                    self.current_process = None
                except Exception as e:
                    print(f"⚠ Error terminating process: {e}")
            else:
                print(f"🔍 No active process found for build {build_id}")
            
            self.db.update_build_status(build_id, 'cancelled', self.current_build['completed_stages'])
            self.db.add_document(
                build_id, 'log', 'Build Cancelled',
                f'Build was cancelled by user at {datetime.now()}', {'cancelled': True}
            )
            
            # Perform cleanup after cancellation
            self._perform_build_cleanup(build_id, 'cancelled', 'user_cancel')
            
            # Commit cancellation to build branch
            self._commit_build_completion(build_id, 'cancelled')
            
            # Emit build completion event for GUI updates
            self.emit_event('build_complete', {'build_id': build_id, 'status': 'cancelled'})
            
            print(f"✅ Build {build_id} cancelled successfully")
    
    def force_cleanup_build(self, build_id: str):
        """Force cleanup of a stuck build"""
        print(f"🧽 Force cleaning up build {build_id}")
        
        # Check if build might be stuck on sudo prompt
        sudo_stuck = self._check_for_sudo_stuck_build(build_id)
        if sudo_stuck:
            print(f"🚨 Build appears to be stuck on sudo password prompt")
        
        # Kill any processes that might be related
        import psutil
        killed_processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if any(pattern in cmdline for pattern in [
                        'bash scripts/', build_id, '/mnt/lfs', 'sudo', 'make -j', 'gcc'
                    ]):
                        print(f"🔥 Killing related process: {proc.info['pid']} - {proc.info['name']}")
                        proc.kill()
                        killed_processes.append(f"PID {proc.info['pid']}: {proc.info['name']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            print(f"⚠ Error during process cleanup: {e}")
        
        # Update database
        if self.current_build and self.current_build['id'] == build_id:
            self.build_cancelled = True
            self.current_process = None
            self.db.update_build_status(build_id, 'cancelled', self.current_build.get('completed_stages', 0))
            
            cleanup_reason = 'sudo_stuck' if sudo_stuck else 'force_cleanup'
            cleanup_msg = f'Build was force cleaned due to stuck state at {datetime.now()}\n\n'
            
            if sudo_stuck:
                cleanup_msg += 'Build appeared to be stuck waiting for sudo password input.\n'
                cleanup_msg += 'This usually happens when sudo password was not provided at build start.\n\n'
            
            cleanup_msg += f'Killed {len(killed_processes)} related processes:\n'
            for proc in killed_processes:
                cleanup_msg += f'  - {proc}\n'
            
            self.db.add_document(
                build_id, 'log', 'Build Force Cleaned',
                cleanup_msg,
                {'force_cleanup': True, 'sudo_stuck': sudo_stuck, 'killed_processes': len(killed_processes)}
            )
            
            # Perform cleanup after force cancel
            self._perform_build_cleanup(build_id, 'cancelled', cleanup_reason)
            
            # Emit completion event
            self.emit_event('build_complete', {'build_id': build_id, 'status': 'cancelled'})
        
        print(f"✅ Build {build_id} force cleanup completed")
    
    def _check_for_sudo_stuck_build(self, build_id: str) -> bool:
        """Check if a build is stuck waiting for sudo password"""
        try:
            # Check recent logs for sudo prompts
            recent_logs = self.db.execute_query(
                "SELECT content FROM build_documents WHERE build_id = %s AND document_type = 'error' AND created_at > NOW() - INTERVAL 10 MINUTE ORDER BY created_at DESC LIMIT 5",
                (build_id,), fetch=True
            )
            
            for log in recent_logs:
                content = log.get('content', '').lower()
                if any(prompt in content for prompt in [
                    'sudo password', 'password for', '[sudo] password', 'sudo prompt detected'
                ]):
                    return True
            
            # Check for processes that might be waiting for input
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if build_id in cmdline or 'bash scripts/' in cmdline:
                        # Check if process is in sleeping/waiting state
                        if proc.info.get('status') in ['sleeping', 'waiting']:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            return False
        except Exception as e:
            print(f"Error checking for sudo stuck build: {e}")
            return False
    
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
            print(f"🔧 Setting up LFS permissions for build {build_id}")
            
            # Try to create basic directories without sudo first
            basic_setup_success = False
            try:
                os.makedirs('/mnt/lfs/sources', mode=0o755, exist_ok=True)
                os.makedirs('/mnt/lfs/tools', mode=0o755, exist_ok=True)
                os.makedirs('/mnt/lfs/usr', mode=0o755, exist_ok=True)
                basic_setup_success = True
                print(f"✅ Created basic LFS directories without sudo")
            except PermissionError:
                print(f"⚠️ Need sudo for LFS directory creation")
            
            if not basic_setup_success and not self.sudo_password:
                # No sudo password available - skip advanced setup
                print(f"⚠️ No sudo password available for LFS permissions setup")
                self.db.add_document(
                    build_id, 'log', 'LFS Permissions Setup Skipped',
                    'No sudo password provided during build start - attempting build without full permissions setup\n'
                    'Build may fail if LFS directories are not accessible\n'
                    'To fix this, provide sudo password when starting the build',
                    {'setup': True, 'skipped': True, 'warning': True}
                )
                return
            
            if self.sudo_password:
                # Create askpass script
                askpass_script = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh')
                askpass_script.write(f'#!/bin/bash\necho "{self.sudo_password}"\n')
                askpass_script.close()
                os.chmod(askpass_script.name, 0o755)
                
                env = os.environ.copy()
                env['SUDO_ASKPASS'] = askpass_script.name
                
                try:
                    # Setup LFS directories with proper permissions
                    commands = [
                        ['sudo', '-A', 'mkdir', '-p', '/mnt/lfs'],
                        ['sudo', '-A', 'mkdir', '-p', '/mnt/lfs/sources'],
                        ['sudo', '-A', 'mkdir', '-p', '/mnt/lfs/tools'],
                        ['sudo', '-A', 'mkdir', '-p', '/mnt/lfs/usr'],
                        ['sudo', '-A', 'chmod', '755', '/mnt/lfs'],
                        ['sudo', '-A', 'chmod', '777', '/mnt/lfs/sources'],
                        ['sudo', '-A', 'chmod', '777', '/mnt/lfs/tools'],
                        ['sudo', '-A', 'chmod', '777', '/mnt/lfs/usr'],
                        ['sudo', '-A', 'chown', '-R', f'{os.getenv("USER", "scottp")}:{os.getenv("USER", "scottp")}', '/mnt/lfs']
                    ]
                    
                    output_lines = []
                    failed_commands = []
                    
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
                            
                            if result.returncode != 0:
                                failed_commands.append(' '.join(cmd))
                            
                            output_lines.append("")
                        except subprocess.TimeoutExpired:
                            error_msg = f"Command timed out: {' '.join(cmd)}"
                            output_lines.append(error_msg)
                            failed_commands.append(' '.join(cmd))
                        except Exception as e:
                            error_msg = f"Command failed: {' '.join(cmd)} - {str(e)}"
                            output_lines.append(error_msg)
                            failed_commands.append(' '.join(cmd))
                    
                    if failed_commands:
                        output_lines.append(f"\nFailed commands: {len(failed_commands)}")
                        for cmd in failed_commands:
                            output_lines.append(f"  - {cmd}")
                        output_lines.append("\nBuild may fail due to permission issues")
                    
                    self.db.add_document(
                        build_id, 'log', 'LFS Permissions Setup',
                        '\n'.join(output_lines),
                        {'setup': True, 'failed_commands': len(failed_commands)}
                    )
                    
                    if failed_commands:
                        print(f"⚠️ {len(failed_commands)} permission commands failed")
                    else:
                        print(f"✅ LFS permissions setup completed successfully")
                    
                finally:
                    # Cleanup askpass script
                    try:
                        os.unlink(askpass_script.name)
                    except:
                        pass
            else:
                self.db.add_document(
                    build_id, 'log', 'LFS Permissions Setup - Basic',
                    'Created basic LFS directories without sudo\n'
                    'Full permission setup skipped - build will use current user permissions',
                    {'setup': True, 'basic_only': True}
                )
                print(f"✅ Basic LFS directory setup completed")
            
        except Exception as e:
            error_msg = f"LFS permissions setup failed: {str(e)}"
            print(f"❌ {error_msg}")
            self.db.add_document(
                build_id, 'error', 'LFS Permissions Setup Failed',
                error_msg, {'setup': True, 'exception': True}
            )
            # Don't fail the build for permission setup issues
            print(f"⚠️ Continuing build despite permission setup failure")
    
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
    
    def _perform_build_cleanup(self, build_id: str, status: str, reason: str):
        """Perform automatic cleanup when builds fail and document the process"""
        cleanup_start = datetime.now()
        cleanup_actions = []
        cleanup_errors = []
        
        print(f"🧹 Starting automatic cleanup for build {build_id} (status: {status}, reason: {reason})")
        
        try:
            # 1. Clean up build directories
            lfs_sources = "/mnt/lfs/sources"
            if os.path.exists(lfs_sources):
                try:
                    # Remove extracted source directories but keep original packages
                    import glob
                    extracted_dirs = []
                    for pattern in ["binutils-*", "gcc-*", "glibc-*", "linux-*"]:
                        for path in glob.glob(os.path.join(lfs_sources, pattern)):
                            if os.path.isdir(path) and not path.endswith('.tar.xz') and not path.endswith('.tar.gz'):
                                extracted_dirs.append(path)
                    
                    for dir_path in extracted_dirs:
                        try:
                            import shutil
                            shutil.rmtree(dir_path)
                            cleanup_actions.append(f"Removed extracted directory: {os.path.basename(dir_path)}")
                        except Exception as e:
                            cleanup_errors.append(f"Failed to remove {dir_path}: {str(e)}")
                    
                    if extracted_dirs:
                        cleanup_actions.append(f"Cleaned {len(extracted_dirs)} extracted source directories")
                    else:
                        cleanup_actions.append("No extracted source directories found to clean")
                        
                except Exception as e:
                    cleanup_errors.append(f"Error during source directory cleanup: {str(e)}")
            
            # 2. Clean up temporary build files
            temp_patterns = ["/tmp/lfs_*", "/tmp/build_*", "/tmp/askpass_*"]
            for pattern in temp_patterns:
                try:
                    import glob
                    temp_files = glob.glob(pattern)
                    for temp_file in temp_files:
                        try:
                            if os.path.isfile(temp_file):
                                os.unlink(temp_file)
                                cleanup_actions.append(f"Removed temp file: {os.path.basename(temp_file)}")
                            elif os.path.isdir(temp_file):
                                import shutil
                                shutil.rmtree(temp_file)
                                cleanup_actions.append(f"Removed temp directory: {os.path.basename(temp_file)}")
                        except Exception as e:
                            cleanup_errors.append(f"Failed to remove temp file {temp_file}: {str(e)}")
                except Exception as e:
                    cleanup_errors.append(f"Error cleaning temp files with pattern {pattern}: {str(e)}")
            
            # 3. Kill any remaining build processes
            killed_processes = []
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if any(pattern in cmdline for pattern in [
                            'build_toolchain.sh', 'prepare_host.sh', 'download_sources.sh',
                            build_id, '/mnt/lfs', 'make -j', 'gcc', 'configure'
                        ]):
                            proc.terminate()
                            killed_processes.append(f"PID {proc.info['pid']}: {proc.info['name']}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                        pass
                
                if killed_processes:
                    cleanup_actions.append(f"Terminated {len(killed_processes)} build-related processes")
                    for proc_info in killed_processes:
                        cleanup_actions.append(f"  - {proc_info}")
                else:
                    cleanup_actions.append("No build-related processes found to terminate")
                    
            except Exception as e:
                cleanup_errors.append(f"Error during process cleanup: {str(e)}")
            
            # 4. Reset build state variables
            if self.current_build and self.current_build['id'] == build_id:
                self.current_process = None
                self.build_cancelled = False
                cleanup_actions.append("Reset build engine state variables")
            
            # 5. Clean up askpass scripts
            if hasattr(self, '_current_askpass_script'):
                try:
                    os.unlink(self._current_askpass_script)
                    delattr(self, '_current_askpass_script')
                    cleanup_actions.append("Removed askpass script")
                except Exception as e:
                    cleanup_errors.append(f"Failed to remove askpass script: {str(e)}")
            
            cleanup_end = datetime.now()
            cleanup_duration = (cleanup_end - cleanup_start).total_seconds()
            
            # Document the cleanup process
            cleanup_summary = f"Automatic cleanup completed for build {build_id}\n\n"
            cleanup_summary += f"Trigger: {reason}\n"
            cleanup_summary += f"Status: {status}\n"
            cleanup_summary += f"Duration: {cleanup_duration:.2f} seconds\n\n"
            
            if cleanup_actions:
                cleanup_summary += f"Cleanup Actions Performed ({len(cleanup_actions)}):" + "\n"
                for action in cleanup_actions:
                    cleanup_summary += f"  ✓ {action}\n"
            
            if cleanup_errors:
                cleanup_summary += f"\nCleanup Errors ({len(cleanup_errors)}):" + "\n"
                for error in cleanup_errors:
                    cleanup_summary += f"  ❌ {error}\n"
            
            cleanup_summary += f"\nCleanup completed at: {cleanup_end}\n"
            
            # Store cleanup documentation in database
            self.db.add_document(
                build_id, 'log', 'Automatic Build Cleanup',
                cleanup_summary,
                {
                    'cleanup': True,
                    'trigger': reason,
                    'status': status,
                    'duration_seconds': cleanup_duration,
                    'actions_count': len(cleanup_actions),
                    'errors_count': len(cleanup_errors),
                    'success': len(cleanup_errors) == 0
                }
            )
            
            print(f"✅ Automatic cleanup completed for build {build_id}")
            print(f"   Actions: {len(cleanup_actions)}, Errors: {len(cleanup_errors)}, Duration: {cleanup_duration:.2f}s")
            
        except Exception as e:
            error_msg = f"Critical error during automatic cleanup: {str(e)}"
            print(f"❌ {error_msg}")
            
            # Document cleanup failure
            try:
                self.db.add_document(
                    build_id, 'error', 'Cleanup Failed',
                    f"Automatic cleanup failed for build {build_id}\n\n"
                    f"Error: {str(e)}\n"
                    f"Trigger: {reason}\n"
                    f"Status: {status}\n"
                    f"Time: {datetime.now()}",
                    {
                        'cleanup': True,
                        'cleanup_failed': True,
                        'trigger': reason,
                        'status': status,
                        'exception_type': type(e).__name__
                    }
                )
            except Exception as db_error:
                print(f"Failed to document cleanup failure: {db_error}")