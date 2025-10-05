#!/usr/bin/env python3

import os
import json
import subprocess
from typing import Dict, List, Optional
from datetime import datetime

class GitIntegration:
    """Git integration for CI/CD pipeline triggers"""
    
    def __init__(self, pipeline_engine, repo_manager):
        self.pipeline_engine = pipeline_engine
        self.repo_manager = repo_manager
        self.hooks_installed = False
        
    def setup_git_hooks(self):
        """Setup Git hooks for automatic pipeline triggering"""
        try:
            repo_path = getattr(self.repo_manager, 'repo_path', '.')
            hooks_dir = os.path.join(repo_path, '.git', 'hooks')
            
            if not os.path.exists(hooks_dir):
                print("❌ Git hooks directory not found")
                return False
            
            # Create post-commit hook
            post_commit_hook = os.path.join(hooks_dir, 'post-commit')
            self.create_post_commit_hook(post_commit_hook)
            
            # Create post-merge hook
            post_merge_hook = os.path.join(hooks_dir, 'post-merge')
            self.create_post_merge_hook(post_merge_hook)
            
            self.hooks_installed = True
            print("✅ Git hooks installed for CI/CD integration")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up Git hooks: {e}")
            return False
    
    def create_post_commit_hook(self, hook_path: str):
        """Create post-commit hook script"""
        hook_content = '''#!/bin/bash
# LFS CI/CD Post-Commit Hook

# Get current branch and commit
BRANCH=$(git rev-parse --abbrev-ref HEAD)
COMMIT=$(git rev-parse HEAD)

# Trigger CI/CD pipeline
python3 -c "
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.cicd.git_integration import trigger_on_commit
trigger_on_commit('$BRANCH', '$COMMIT')
"
'''
        
        with open(hook_path, 'w') as f:
            f.write(hook_content)
        
        # Make executable
        os.chmod(hook_path, 0o755)
    
    def create_post_merge_hook(self, hook_path: str):
        """Create post-merge hook script"""
        hook_content = '''#!/bin/bash
# LFS CI/CD Post-Merge Hook

# Get current branch and commit
BRANCH=$(git rev-parse --abbrev-ref HEAD)
COMMIT=$(git rev-parse HEAD)

# Trigger CI/CD pipeline for merge
python3 -c "
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.cicd.git_integration import trigger_on_merge
trigger_on_merge('$BRANCH', '$COMMIT')
"
'''
        
        with open(hook_path, 'w') as f:
            f.write(hook_content)
        
        # Make executable
        os.chmod(hook_path, 0o755)
    
    def trigger_pipelines_for_branch(self, branch: str, commit_hash: str, trigger_type: str = 'push'):
        """Trigger pipelines configured for a specific branch"""
        try:
            # Get all active pipelines
            pipelines = self.pipeline_engine.db.execute_query("""
                SELECT id, name, config_path FROM cicd_pipelines 
                WHERE status = 'active'
            """, fetch=True) or []
            
            triggered_count = 0
            
            for pipeline in pipelines:
                pipeline_id = pipeline['id']
                config = self.pipeline_engine.get_pipeline_config(pipeline_id)
                
                if not config:
                    continue
                
                # Check if pipeline should trigger for this branch
                if self.should_trigger_pipeline(config, branch, trigger_type):
                    trigger_data = {
                        'branch': branch,
                        'commit': commit_hash,
                        'trigger_time': datetime.now().isoformat()
                    }
                    
                    run_id = self.pipeline_engine.trigger_pipeline(
                        pipeline_id, trigger_type, trigger_data
                    )
                    
                    print(f"🚀 Triggered pipeline '{pipeline['name']}' (run: {run_id})")
                    triggered_count += 1
            
            if triggered_count > 0:
                print(f"✅ Triggered {triggered_count} pipelines for {trigger_type} on {branch}")
            else:
                print(f"ℹ️ No pipelines configured for {trigger_type} on {branch}")
                
        except Exception as e:
            print(f"❌ Error triggering pipelines: {e}")
    
    def should_trigger_pipeline(self, config: Dict, branch: str, trigger_type: str) -> bool:
        """Check if pipeline should trigger for given branch and trigger type"""
        try:
            triggers = config.get('triggers', {})
            
            if trigger_type == 'push' and 'push' in triggers:
                push_config = triggers['push']
                target_branches = push_config.get('branches', ['main', 'master'])
                
                # Check if branch matches
                if branch in target_branches:
                    return True
                
                # Check for pattern matching
                for pattern in target_branches:
                    if '*' in pattern:
                        # Simple wildcard matching
                        if pattern.replace('*', '') in branch:
                            return True
            
            elif trigger_type == 'merge' and 'merge' in triggers:
                merge_config = triggers['merge']
                target_branches = merge_config.get('branches', ['main', 'master'])
                return branch in target_branches
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking pipeline trigger conditions: {e}")
            return False
    
    def get_commit_info(self, commit_hash: str) -> Dict:
        """Get detailed commit information"""
        try:
            repo_path = getattr(self.repo_manager, 'repo_path', '.')
            
            # Get commit details
            cmd = f"git show --format='%H|%an|%ae|%s|%ct' --no-patch {commit_hash}"
            result = subprocess.run(
                cmd, shell=True, cwd=repo_path,
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split('|')
                if len(parts) >= 5:
                    return {
                        'hash': parts[0],
                        'author_name': parts[1],
                        'author_email': parts[2],
                        'message': parts[3],
                        'timestamp': int(parts[4])
                    }
            
            return {'hash': commit_hash}
            
        except Exception as e:
            print(f"❌ Error getting commit info: {e}")
            return {'hash': commit_hash}
    
    def get_changed_files(self, commit_hash: str) -> List[str]:
        """Get list of files changed in commit"""
        try:
            repo_path = getattr(self.repo_manager, 'repo_path', '.')
            
            cmd = f"git diff-tree --no-commit-id --name-only -r {commit_hash}"
            result = subprocess.run(
                cmd, shell=True, cwd=repo_path,
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                return [f.strip() for f in result.stdout.split('\n') if f.strip()]
            
            return []
            
        except Exception as e:
            print(f"❌ Error getting changed files: {e}")
            return []
    
    def create_pipeline_status_commit(self, run_id: str, status: str, pipeline_name: str):
        """Create a commit with pipeline status (optional)"""
        try:
            if not hasattr(self.repo_manager, 'repo_path'):
                return
            
            repo_path = self.repo_manager.repo_path
            
            # Create a status file
            status_dir = os.path.join(repo_path, '.cicd', 'status')
            os.makedirs(status_dir, exist_ok=True)
            
            status_file = os.path.join(status_dir, f"{run_id}.json")
            status_data = {
                'run_id': run_id,
                'pipeline_name': pipeline_name,
                'status': status,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
            
            # Commit the status file
            subprocess.run(['git', 'add', status_file], cwd=repo_path)
            subprocess.run([
                'git', 'commit', '-m', 
                f"CI/CD: Pipeline {pipeline_name} {status} (run: {run_id})"
            ], cwd=repo_path)
            
            print(f"📝 Created status commit for pipeline run {run_id}")
            
        except Exception as e:
            print(f"❌ Error creating status commit: {e}")

# Global functions for Git hooks
def trigger_on_commit(branch: str, commit_hash: str):
    """Called by post-commit hook"""
    try:
        # This would be called by the Git hook
        # For now, just log the event
        print(f"🔗 Git commit detected: {commit_hash} on {branch}")
        
        # In a real implementation, this would:
        # 1. Load the pipeline engine
        # 2. Trigger appropriate pipelines
        # 3. Update the database
        
    except Exception as e:
        print(f"❌ Error in commit trigger: {e}")

def trigger_on_merge(branch: str, commit_hash: str):
    """Called by post-merge hook"""
    try:
        print(f"🔗 Git merge detected: {commit_hash} on {branch}")
        
        # Similar to commit trigger but for merges
        
    except Exception as e:
        print(f"❌ Error in merge trigger: {e}")