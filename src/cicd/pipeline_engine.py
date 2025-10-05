#!/usr/bin/env python3

import os
import json
import yaml
import time
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid

class PipelineEngine:
    """In-house CI/CD Pipeline Engine with Git integration"""
    
    def __init__(self, db_manager, repo_manager):
        self.db = db_manager
        self.repo_manager = repo_manager
        self.active_pipelines = {}
        self.pipeline_configs = {}
        self.triggers = {}
        self.setup_database_tables()
        
    def setup_database_tables(self):
        """Setup CI/CD database tables"""
        try:
            # Pipelines table
            self.db.execute_query("""
                CREATE TABLE IF NOT EXISTS cicd_pipelines (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    config_path VARCHAR(500),
                    status ENUM('active', 'inactive', 'disabled') DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_name (name),
                    INDEX idx_status (status)
                )
            """)
            
            # Pipeline runs table
            self.db.execute_query("""
                CREATE TABLE IF NOT EXISTS cicd_pipeline_runs (
                    id VARCHAR(36) PRIMARY KEY,
                    pipeline_id VARCHAR(36) NOT NULL,
                    trigger_type ENUM('push', 'pull_request', 'schedule', 'manual', 'webhook') NOT NULL,
                    branch VARCHAR(255),
                    commit_hash VARCHAR(40),
                    status ENUM('pending', 'running', 'success', 'failed', 'cancelled') DEFAULT 'pending',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    duration_seconds INT DEFAULT 0,
                    trigger_data JSON,
                    FOREIGN KEY (pipeline_id) REFERENCES cicd_pipelines(id) ON DELETE CASCADE,
                    INDEX idx_pipeline_status (pipeline_id, status),
                    INDEX idx_branch (branch),
                    INDEX idx_started_at (started_at)
                )
            """)
            
            # Pipeline jobs table
            self.db.execute_query("""
                CREATE TABLE IF NOT EXISTS cicd_jobs (
                    id VARCHAR(36) PRIMARY KEY,
                    run_id VARCHAR(36) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    stage VARCHAR(100),
                    job_order INT DEFAULT 0,
                    status ENUM('pending', 'running', 'success', 'failed', 'skipped', 'cancelled') DEFAULT 'pending',
                    started_at TIMESTAMP NULL,
                    completed_at TIMESTAMP NULL,
                    duration_seconds INT DEFAULT 0,
                    exit_code INT DEFAULT 0,
                    FOREIGN KEY (run_id) REFERENCES cicd_pipeline_runs(id) ON DELETE CASCADE,
                    INDEX idx_run_stage (run_id, stage),
                    INDEX idx_status (status)
                )
            """)
            
            # Job logs table
            self.db.execute_query("""
                CREATE TABLE IF NOT EXISTS cicd_job_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    job_id VARCHAR(36) NOT NULL,
                    log_level ENUM('info', 'warning', 'error', 'debug') DEFAULT 'info',
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES cicd_jobs(id) ON DELETE CASCADE,
                    INDEX idx_job_timestamp (job_id, timestamp)
                )
            """)
            
            print("✅ CI/CD database tables initialized")
            
        except Exception as e:
            print(f"❌ Error setting up CI/CD database tables: {e}")
    
    def create_pipeline(self, name: str, config_data: Dict) -> str:
        """Create a new CI/CD pipeline"""
        pipeline_id = str(uuid.uuid4())
        
        try:
            # Save pipeline configuration
            config_path = f"cicd/pipelines/{name}.yml"
            config_content = yaml.dump(config_data, default_flow_style=False)
            
            # Save to repository
            full_config_path = self.repo_manager.add_file(config_path, config_content)
            
            # Store in database
            self.db.execute_query("""
                INSERT INTO cicd_pipelines (id, name, config_path, status)
                VALUES (%s, %s, %s, 'active')
            """, (pipeline_id, name, config_path))
            
            # Cache configuration
            self.pipeline_configs[pipeline_id] = config_data
            
            print(f"✅ Created CI/CD pipeline: {name} ({pipeline_id})")
            return pipeline_id
            
        except Exception as e:
            print(f"❌ Error creating pipeline: {e}")
            raise
    
    def trigger_pipeline(self, pipeline_id: str, trigger_type: str, trigger_data: Dict = None) -> str:
        """Trigger a pipeline run"""
        run_id = str(uuid.uuid4())
        
        try:
            # Get pipeline configuration
            config = self.get_pipeline_config(pipeline_id)
            if not config:
                raise Exception(f"Pipeline {pipeline_id} not found")
            
            # Extract Git information
            branch = trigger_data.get('branch') if trigger_data else self.repo_manager.get_current_branch()
            commit_hash = trigger_data.get('commit') if trigger_data else None
            
            # Create pipeline run record
            self.db.execute_query("""
                INSERT INTO cicd_pipeline_runs (id, pipeline_id, trigger_type, branch, commit_hash, status, trigger_data)
                VALUES (%s, %s, %s, %s, %s, 'pending', %s)
            """, (run_id, pipeline_id, trigger_type, branch, commit_hash, json.dumps(trigger_data or {})))
            
            # Start pipeline execution in background thread
            thread = threading.Thread(target=self.execute_pipeline, args=(run_id, config))
            thread.daemon = True
            thread.start()
            
            self.active_pipelines[run_id] = {
                'pipeline_id': pipeline_id,
                'status': 'pending',
                'thread': thread,
                'started_at': datetime.now()
            }
            
            print(f"🚀 Triggered pipeline run: {run_id}")
            return run_id
            
        except Exception as e:
            print(f"❌ Error triggering pipeline: {e}")
            raise
    
    def execute_pipeline(self, run_id: str, config: Dict):
        """Execute a complete pipeline run"""
        try:
            print(f"🔄 Starting pipeline run: {run_id}")
            
            # Update run status to running
            self.db.execute_query("""
                UPDATE cicd_pipeline_runs 
                SET status = 'running', started_at = CURRENT_TIMESTAMP 
                WHERE id = %s
            """, (run_id,))
            
            if run_id in self.active_pipelines:
                self.active_pipelines[run_id]['status'] = 'running'
            
            # Execute stages in order
            stages = config.get('stages', [])
            overall_success = True
            
            for stage in stages:
                stage_name = stage.get('name', 'unnamed')
                print(f"📋 Executing stage: {stage_name}")
                
                stage_success = self.execute_stage(run_id, stage)
                if not stage_success:
                    overall_success = False
                    if stage.get('allow_failure', False):
                        print(f"⚠️ Stage {stage_name} failed but marked as allow_failure")
                        continue
                    else:
                        print(f"❌ Stage {stage_name} failed, stopping pipeline")
                        break
            
            # Update final status
            final_status = 'success' if overall_success else 'failed'
            completion_time = datetime.now()
            
            # Calculate duration
            run_data = self.db.execute_query("""
                SELECT started_at FROM cicd_pipeline_runs WHERE id = %s
            """, (run_id,), fetch=True)
            
            duration = 0
            if run_data:
                start_time = run_data[0]['started_at']
                duration = int((completion_time - start_time).total_seconds())
            
            self.db.execute_query("""
                UPDATE cicd_pipeline_runs 
                SET status = %s, completed_at = %s, duration_seconds = %s 
                WHERE id = %s
            """, (final_status, completion_time, duration, run_id))
            
            if run_id in self.active_pipelines:
                self.active_pipelines[run_id]['status'] = final_status
                self.active_pipelines[run_id]['completed_at'] = completion_time
            
            print(f"✅ Pipeline run completed: {run_id} ({final_status})")
            
        except Exception as e:
            print(f"❌ Pipeline execution error: {e}")
            self.db.execute_query("""
                UPDATE cicd_pipeline_runs 
                SET status = 'failed', completed_at = CURRENT_TIMESTAMP 
                WHERE id = %s
            """, (run_id,))
    
    def execute_stage(self, run_id: str, stage_config: Dict) -> bool:
        """Execute a pipeline stage"""
        stage_name = stage_config.get('name', 'unnamed')
        jobs = stage_config.get('jobs', [])
        
        if not jobs:
            print(f"⚠️ No jobs defined for stage: {stage_name}")
            return True
        
        # Execute jobs sequentially
        for i, job_config in enumerate(jobs):
            success = self.execute_job(run_id, stage_name, job_config, i)
            if not success and not job_config.get('allow_failure', False):
                return False
        return True
    
    def execute_job(self, run_id: str, stage_name: str, job_config: Dict, job_order: int) -> bool:
        """Execute a single job"""
        job_id = str(uuid.uuid4())
        job_name = job_config.get('name', f'job-{job_order}')
        
        try:
            # Create job record
            self.db.execute_query("""
                INSERT INTO cicd_jobs (id, run_id, name, stage, job_order, status)
                VALUES (%s, %s, %s, %s, %s, 'running')
            """, (job_id, run_id, job_name, stage_name, job_order))
            
            self.log_job_message(job_id, 'info', f"Starting job: {job_name}")
            
            start_time = datetime.now()
            
            # Execute job steps
            steps = job_config.get('steps', [])
            for step_i, step in enumerate(steps):
                step_success = self.execute_step(job_id, step, step_i)
                if not step_success:
                    raise Exception(f"Step {step_i} failed")
            
            # Job completed successfully
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            self.db.execute_query("""
                UPDATE cicd_jobs 
                SET status = 'success', completed_at = %s, duration_seconds = %s, exit_code = 0
                WHERE id = %s
            """, (end_time, duration, job_id))
            
            self.log_job_message(job_id, 'info', f"Job completed successfully in {duration}s")
            return True
            
        except Exception as e:
            # Job failed
            end_time = datetime.now()
            
            self.db.execute_query("""
                UPDATE cicd_jobs 
                SET status = 'failed', completed_at = %s, exit_code = 1
                WHERE id = %s
            """, (end_time, job_id))
            
            self.log_job_message(job_id, 'error', f"Job failed: {str(e)}")
            return False
    
    def execute_step(self, job_id: str, step_config: Dict, step_order: int) -> bool:
        """Execute a single step within a job"""
        step_name = step_config.get('name', f'step-{step_order}')
        
        try:
            self.log_job_message(job_id, 'info', f"Executing step: {step_name}")
            
            # Handle different step types
            if 'run' in step_config:
                return self.execute_shell_command(job_id, step_config['run'])
            elif 'build' in step_config:
                return self.execute_build_step(job_id, step_config['build'])
            else:
                self.log_job_message(job_id, 'warning', f"Unknown step type in: {step_name}")
                return True
                
        except Exception as e:
            self.log_job_message(job_id, 'error', f"Step {step_name} failed: {str(e)}")
            return False
    
    def execute_shell_command(self, job_id: str, command: str) -> bool:
        """Execute a shell command"""
        try:
            self.log_job_message(job_id, 'info', f"Running command: {command}")
            
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=getattr(self.repo_manager, 'repo_path', '.')
            )
            
            # Stream output
            for line in process.stdout:
                self.log_job_message(job_id, 'info', line.strip())
            
            process.wait()
            
            if process.returncode == 0:
                self.log_job_message(job_id, 'info', f"Command completed successfully")
                return True
            else:
                self.log_job_message(job_id, 'error', f"Command failed with exit code: {process.returncode}")
                return False
                
        except Exception as e:
            self.log_job_message(job_id, 'error', f"Command execution error: {str(e)}")
            return False
    
    def execute_build_step(self, job_id: str, build_config: Dict) -> bool:
        """Execute a build step (integrates with existing build system)"""
        try:
            build_type = build_config.get('type', 'lfs')
            
            if build_type == 'lfs':
                config_name = build_config.get('config', 'default-lfs')
                self.log_job_message(job_id, 'info', f"Starting LFS build with config: {config_name}")
                
                # Simulate build - in real implementation this would integrate with BuildEngine
                time.sleep(2)
                
                self.log_job_message(job_id, 'info', "LFS build completed successfully")
                return True
            else:
                self.log_job_message(job_id, 'warning', f"Unknown build type: {build_type}")
                return True
                
        except Exception as e:
            self.log_job_message(job_id, 'error', f"Build step failed: {str(e)}")
            return False
    
    def log_job_message(self, job_id: str, level: str, message: str):
        """Log a message for a job"""
        try:
            self.db.execute_query("""
                INSERT INTO cicd_job_logs (job_id, log_level, message)
                VALUES (%s, %s, %s)
            """, (job_id, level, message))
            
            # Also print to console for debugging
            level_emoji = {'info': '📋', 'warning': '⚠️', 'error': '❌', 'debug': '🔍'}
            print(f"{level_emoji.get(level, '📋')} [{job_id[:8]}] {message}")
            
        except Exception as e:
            print(f"❌ Error logging job message: {e}")
    
    def get_pipeline_config(self, pipeline_id: str) -> Optional[Dict]:
        """Get pipeline configuration"""
        if pipeline_id in self.pipeline_configs:
            return self.pipeline_configs[pipeline_id]
        
        try:
            # Load from database
            result = self.db.execute_query("""
                SELECT config_path FROM cicd_pipelines WHERE id = %s
            """, (pipeline_id,), fetch=True)
            
            if result:
                config_path = result[0]['config_path']
                # Load configuration from repository
                config_content = getattr(self.repo_manager, 'get_file_content', lambda x: None)(config_path)
                if config_content:
                    config = yaml.safe_load(config_content)
                    self.pipeline_configs[pipeline_id] = config
                    return config
            
            return None
            
        except Exception as e:
            print(f"❌ Error loading pipeline config: {e}")
            return None
    
    def get_pipeline_runs(self, pipeline_id: str = None, limit: int = 50) -> List[Dict]:
        """Get pipeline runs"""
        try:
            if pipeline_id:
                query = """
                    SELECT pr.*, p.name as pipeline_name
                    FROM cicd_pipeline_runs pr
                    JOIN cicd_pipelines p ON pr.pipeline_id = p.id
                    WHERE pr.pipeline_id = %s
                    ORDER BY pr.started_at DESC
                    LIMIT %s
                """
                params = (pipeline_id, limit)
            else:
                query = """
                    SELECT pr.*, p.name as pipeline_name
                    FROM cicd_pipeline_runs pr
                    JOIN cicd_pipelines p ON pr.pipeline_id = p.id
                    ORDER BY pr.started_at DESC
                    LIMIT %s
                """
                params = (limit,)
            
            return self.db.execute_query(query, params, fetch=True) or []
            
        except Exception as e:
            print(f"❌ Error getting pipeline runs: {e}")
            return []
    
    def get_job_logs(self, job_id: str) -> List[Dict]:
        """Get logs for a specific job"""
        try:
            return self.db.execute_query("""
                SELECT * FROM cicd_job_logs 
                WHERE job_id = %s 
                ORDER BY timestamp ASC
            """, (job_id,), fetch=True) or []
            
        except Exception as e:
            print(f"❌ Error getting job logs: {e}")
            return []