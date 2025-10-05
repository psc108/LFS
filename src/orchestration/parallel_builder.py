import threading
import multiprocessing
import queue
import time
import os
from typing import Dict, List, Set, Optional
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class BuildTask:
    id: str
    name: str
    command: str
    dependencies: List[str]
    cpu_cores: int = 1
    memory_mb: int = 1024
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    output: str = ""
    error: str = ""

class ParallelBuildEngine:
    def __init__(self, max_workers: int = None, max_memory_mb: int = 8192, fault_analyzer=None):
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.max_memory_mb = max_memory_mb
        self.fault_analyzer = fault_analyzer
        self.tasks: Dict[str, BuildTask] = {}
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.running_tasks: Dict[str, threading.Thread] = {}
        self.resource_lock = threading.Lock()
        self.current_memory_usage = 0
        self.callbacks = {'task_start': [], 'task_complete': [], 'task_failed': [], 'build_complete': []}
    
    def add_task(self, task: BuildTask):
        self.tasks[task.id] = task
    
    def can_run_task(self, task: BuildTask) -> bool:
        for dep in task.dependencies:
            if dep not in self.completed_tasks:
                return False
        
        with self.resource_lock:
            if (len(self.running_tasks) >= self.max_workers or
                self.current_memory_usage + task.memory_mb > self.max_memory_mb):
                return False
        return True
    
    def execute_task(self, task: BuildTask):
        import subprocess
        
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()
        
        with self.resource_lock:
            self.current_memory_usage += task.memory_mb
        
        try:
            env = os.environ.copy()
            if task.cpu_cores > 1:
                env['OMP_NUM_THREADS'] = str(task.cpu_cores)
                env['MAKEFLAGS'] = f'-j{task.cpu_cores}'
            
            process = subprocess.Popen(task.command, shell=True, stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, text=True, env=env)
            
            stdout, stderr = process.communicate()
            task.output = stdout
            task.error = stderr
            
            if process.returncode == 0:
                task.status = TaskStatus.COMPLETED
                self.completed_tasks.add(task.id)
            else:
                task.status = TaskStatus.FAILED
                self.failed_tasks.add(task.id)
        
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.failed_tasks.add(task.id)
        
        finally:
            task.end_time = time.time()
            with self.resource_lock:
                self.current_memory_usage -= task.memory_mb
                if task.id in self.running_tasks:
                    del self.running_tasks[task.id]
    
    def start_parallel_build(self):
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while True:
                ready_tasks = []
                for task_id, task in self.tasks.items():
                    if (task.status == TaskStatus.PENDING and 
                        task_id not in self.running_tasks and
                        self.can_run_task(task)):
                        ready_tasks.append(task)
                
                for task in ready_tasks:
                    if len(self.running_tasks) < self.max_workers:
                        future = executor.submit(self.execute_task, task)
                        self.running_tasks[task.id] = future
                
                all_done = all(task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] 
                              for task in self.tasks.values())
                
                if all_done:
                    break
                
                time.sleep(1)
        
        # Analyze parallel build performance
        if self.fault_analyzer:
            try:
                task_data = [{
                    'id': task.id,
                    'status': task.status.value,
                    'duration': (task.end_time - task.start_time) if task.end_time and task.start_time else 0
                } for task in self.tasks.values()]
                
                performance_analysis = self.fault_analyzer.analyze_parallel_build_performance(task_data)
                print(f"📈 Parallel build analysis: Risk score {performance_analysis.get('risk_score', 0)}")
            except Exception as e:
                print(f"Performance analysis error: {e}")
    
    def get_build_status(self) -> Dict:
        return {
            'total_tasks': len(self.tasks),
            'completed': len(self.completed_tasks),
            'failed': len(self.failed_tasks),
            'running': len(self.running_tasks),
            'pending': len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
            'memory_usage': self.current_memory_usage,
            'max_memory': self.max_memory_mb
        }

class ParallelBuildOrchestrator:
    """High-level orchestrator for parallel builds"""
    
    def __init__(self):
        self.engine = None
        self.active_builds = {}
    
    def start_parallel_build(self, config_path: str, build_config: dict) -> str:
        """Start a parallel build and return build ID"""
        import uuid
        # Import will be done below after path setup
        
        build_id = f"parallel-{uuid.uuid4().hex[:8]}"
        
        try:
            # Initialize components
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent))
            
            from database.db_manager import DatabaseManager
            from analysis.integrated_analyzer import IntegratedAnalyzer
            
            db = DatabaseManager()
            analyzer = IntegratedAnalyzer(db)
            
            # Create parallel engine
            self.engine = ParallelBuildEngine(
                max_workers=build_config.get('max_parallel_jobs', 4),
                max_memory_mb=build_config.get('memory_limit_gb', 8) * 1024,
                fault_analyzer=analyzer
            )
            
            # Store build record
            db.create_build(build_id, config_path, build_config.get('max_parallel_jobs', 4))
            
            # Start build in background thread
            import threading
            build_thread = threading.Thread(target=self._run_parallel_build, args=(build_id, config_path))
            build_thread.daemon = True
            build_thread.start()
            
            self.active_builds[build_id] = {
                'engine': self.engine,
                'thread': build_thread,
                'config': build_config
            }
            
            return build_id
            
        except Exception as e:
            raise Exception(f"Failed to start parallel build: {str(e)}")
    
    def _run_parallel_build(self, build_id: str, config_path: str):
        """Run the actual parallel build"""
        try:
            # Load build configuration and create tasks
            # This would parse the YAML config and create BuildTask objects
            # For now, create sample tasks
            
            sample_tasks = [
                BuildTask("prepare", "Prepare Host", "echo 'Preparing host system'", [], 1, 512),
                BuildTask("download", "Download Sources", "echo 'Downloading sources'", ["prepare"], 2, 1024),
                BuildTask("toolchain", "Build Toolchain", "echo 'Building toolchain'", ["download"], 4, 2048),
                BuildTask("system", "Build System", "echo 'Building system'", ["toolchain"], 4, 4096)
            ]
            
            for task in sample_tasks:
                self.engine.add_task(task)
            
            # Start the parallel build
            self.engine.start_parallel_build()
            
            # Update build status
            from database.db_manager import DatabaseManager
            db = DatabaseManager()
            
            if len(self.engine.failed_tasks) == 0:
                db.update_build_status(build_id, 'success', len(sample_tasks))
            else:
                db.update_build_status(build_id, 'failed', len(self.engine.completed_tasks))
            
        except Exception as e:
            print(f"Parallel build error: {e}")
            # Update build status to failed
            try:
                from database.db_manager import DatabaseManager
                db = DatabaseManager()
                db.update_build_status(build_id, 'failed', 0)
            except:
                pass