import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

class BuildScheduler:
    def __init__(self, db_manager=None, build_engine=None):
        self.db = db_manager
        self.build_engine = build_engine
        self.scheduled_jobs = {}
        self.scheduler_thread = None
        self.running = False
        self.job_counter = 0
    
    def schedule_build(self, cron_expression: str, build_config: Dict, job_name: str = None) -> str:
        """Schedule a recurring build using cron expression"""
        import uuid
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        
        if not job_name:
            job_name = f"Scheduled Build {self.job_counter + 1}"
            self.job_counter += 1
        
        try:
            # Validate cron expression
            self._validate_cron_expression(cron_expression)
            
            # Create job record
            job = {
                'id': job_id,
                'name': job_name,
                'cron_expression': cron_expression,
                'build_config': build_config,
                'created_at': datetime.now().isoformat(),
                'enabled': True,
                'last_run': None,
                'next_run': self._calculate_next_run(cron_expression),
                'run_count': 0,
                'success_count': 0,
                'failure_count': 0
            }
            
            self.scheduled_jobs[job_id] = job
            
            # Store in database
            if self.db:
                self._store_scheduled_job(job)
            
            # Start scheduler if not running
            if not self.running:
                self.start_scheduler()
            
            return job_id
            
        except Exception as e:
            raise Exception(f"Failed to schedule build: {str(e)}")
    
    def _validate_cron_expression(self, cron_expr: str):
        """Validate cron expression format"""
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError("Cron expression must have 5 parts: minute hour day month weekday")
        
        # Basic validation for each part
        ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
        for i, (part, (min_val, max_val)) in enumerate(zip(parts, ranges)):
            if part != '*' and not part.isdigit():
                if '/' not in part and ',' not in part and '-' not in part:
                    raise ValueError(f"Invalid cron expression part: {part}")
        
        print(f"✅ Cron expression validated: {cron_expr}")
    
    def _calculate_next_run(self, cron_expr: str) -> str:
        """Calculate next run time from cron expression"""
        try:
            # Simple next run calculation (would use croniter in production)
            now = datetime.now()
            
            # For demo, calculate based on common patterns
            if cron_expr == "0 2 * * *":  # Daily at 2 AM
                next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
            elif cron_expr == "0 0 * * 0":  # Weekly on Sunday
                days_ahead = 6 - now.weekday()  # Sunday is 6
                if days_ahead <= 0:
                    days_ahead += 7
                next_run = (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                # Default to next hour for other expressions
                next_run = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            
            return next_run.isoformat()
            
        except Exception:
            # Fallback to next hour
            return (datetime.now() + timedelta(hours=1)).isoformat()
    
    def start_scheduler(self):
        """Start the build scheduler"""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            print("🕐 Build scheduler started")
    
    def stop_scheduler(self):
        """Stop the build scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("⏹️ Build scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                current_time = datetime.now()
                
                for job_id, job in self.scheduled_jobs.items():
                    if not job['enabled']:
                        continue
                    
                    next_run = datetime.fromisoformat(job['next_run'])
                    
                    if current_time >= next_run:
                        self._execute_scheduled_job(job)
                
                # Check every minute
                time.sleep(60)
                
            except Exception as e:
                print(f"Scheduler error: {e}")
                time.sleep(30)
    
    def _execute_scheduled_job(self, job: Dict):
        """Execute a scheduled job"""
        try:
            print(f"🚀 Executing scheduled job: {job['name']}")
            
            # Update job status
            job['last_run'] = datetime.now().isoformat()
            job['run_count'] += 1
            job['next_run'] = self._calculate_next_run(job['cron_expression'])
            
            # Start the build
            if self.build_engine:
                build_id = self.build_engine.start_build(
                    job['build_config'].get('config_path', ''),
                    job['build_config'].get('config_name', f"scheduled-{job['id']}")
                )
                
                # Track build result (simplified)
                job['success_count'] += 1
                print(f"✅ Scheduled build started: {build_id}")
            else:
                print("⚠️ No build engine available for scheduled job")
            
            # Update database
            if self.db:
                self._update_scheduled_job(job)
                
        except Exception as e:
            job['failure_count'] += 1
            print(f"❌ Scheduled job failed: {e}")
            
            if self.db:
                self._update_scheduled_job(job)
    
    def _store_scheduled_job(self, job: Dict):
        """Store scheduled job in database"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO scheduled_jobs 
                (job_id, job_name, cron_expression, build_config, created_at, enabled, next_run)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                job['id'], job['name'], job['cron_expression'],
                str(job['build_config']), job['created_at'], 
                job['enabled'], job['next_run']
            ))
            
            conn.commit()
            cursor.close()
            
        except Exception as e:
            print(f"Error storing scheduled job: {e}")
    
    def _update_scheduled_job(self, job: Dict):
        """Update scheduled job in database"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE scheduled_jobs 
                SET last_run = %s, next_run = %s, run_count = %s, 
                    success_count = %s, failure_count = %s
                WHERE job_id = %s
            """, (
                job['last_run'], job['next_run'], job['run_count'],
                job['success_count'], job['failure_count'], job['id']
            ))
            
            conn.commit()
            cursor.close()
            
        except Exception as e:
            print(f"Error updating scheduled job: {e}")
    
    def get_scheduled_jobs(self) -> List[Dict]:
        """Get all scheduled jobs"""
        return list(self.scheduled_jobs.values())
    
    def enable_job(self, job_id: str):
        """Enable a scheduled job"""
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id]['enabled'] = True
    
    def disable_job(self, job_id: str):
        """Disable a scheduled job"""
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id]['enabled'] = False
    
    def delete_job(self, job_id: str):
        """Delete a scheduled job"""
        if job_id in self.scheduled_jobs:
            del self.scheduled_jobs[job_id]
            
            if self.db:
                try:
                    conn = self.db.connect()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM scheduled_jobs WHERE job_id = %s", (job_id,))
                    conn.commit()
                    cursor.close()
                except Exception as e:
                    print(f"Error deleting scheduled job: {e}")
    
    def start_scheduled_build(self, schedule_config: dict) -> str:
        """Start scheduled build and return job ID"""
        try:
            job_id = self.schedule_build(
                schedule_config['cron_expression'],
                schedule_config['build_config'],
                schedule_config.get('job_name')
            )
            
            return job_id
            
        except Exception as e:
            raise Exception(f"Failed to start scheduled build: {str(e)}")