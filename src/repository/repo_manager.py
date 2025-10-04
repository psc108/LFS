import os
import json
import hashlib
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import git

from ..database.db_manager import DatabaseManager

class RepositoryManager:
    def __init__(self, db_manager: DatabaseManager, repo_path: str = "/tmp/lfs_repo"):
        self.db = db_manager
        self.repo_path = Path(repo_path)
        self.repo_path.mkdir(parents=True, exist_ok=True)
        self.git_repo = None
        self._init_repository()
    
    def _init_repository(self):
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            self.git_repo = git.Repo.init(self.repo_path)
            
            # Create initial structure
            (self.repo_path / "configs").mkdir(exist_ok=True)
            (self.repo_path / "scripts").mkdir(exist_ok=True)
            (self.repo_path / "patches").mkdir(exist_ok=True)
            (self.repo_path / "sources").mkdir(exist_ok=True)
            
            # Create initial README
            readme_content = """# LFS Build Repository

This repository contains build configurations, scripts, and patches for Linux From Scratch builds.

## Structure
- configs/: Build configuration files
- scripts/: Build stage scripts
- patches/: Custom patches
- sources/: Source code snapshots
"""
            (self.repo_path / "README.md").write_text(readme_content)
            
            # Initial commit
            self.git_repo.index.add(["."])
            self.git_repo.index.commit("Initial repository setup")
        else:
            self.git_repo = git.Repo(self.repo_path)
    
    def create_branch(self, branch_name: str, from_branch: str = "main") -> bool:
        try:
            if from_branch != "main":
                self.git_repo.git.checkout(from_branch)
            
            new_branch = self.git_repo.create_head(branch_name)
            new_branch.checkout()
            return True
        except Exception as e:
            print(f"Error creating branch: {e}")
            return False
    
    def switch_branch(self, branch_name: str) -> bool:
        try:
            self.git_repo.git.checkout(branch_name)
            return True
        except Exception as e:
            print(f"Error switching branch: {e}")
            return False
    
    def list_branches(self) -> List[str]:
        return [branch.name for branch in self.git_repo.branches]
    
    def commit_changes(self, message: str, build_id: str = None) -> str:
        try:
            # Add all changes
            self.git_repo.git.add(A=True)
            
            # Check if there are changes to commit
            if not self.git_repo.index.diff("HEAD"):
                return self.git_repo.head.commit.hexsha
            
            # Commit with metadata
            commit_message = message
            if build_id:
                commit_message += f"\n\nBuild-ID: {build_id}"
            
            commit = self.git_repo.index.commit(commit_message)
            
            # Store snapshot in database if build_id provided
            if build_id:
                self._store_snapshot(build_id, commit.hexsha)
            
            return commit.hexsha
        except Exception as e:
            print(f"Error committing changes: {e}")
            return ""
    
    def _store_snapshot(self, build_id: str, commit_hash: str):
        try:
            # Create tarball of current state
            snapshot_path = f"/tmp/snapshot_{build_id}.tar.gz"
            with tarfile.open(snapshot_path, "w:gz") as tar:
                tar.add(self.repo_path, arcname=".")
            
            # Read snapshot data
            with open(snapshot_path, "rb") as f:
                snapshot_data = f.read()
            
            # Store in database
            conn = self.db.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO repo_snapshots (build_id, commit_hash, branch_name, snapshot_data)
                VALUES (%s, %s, %s, %s)
            """, (build_id, commit_hash, self.git_repo.active_branch.name, snapshot_data))
            
            conn.commit()
            cursor.close()
            
            # Cleanup temp file
            os.remove(snapshot_path)
            
        except Exception as e:
            print(f"Error storing snapshot: {e}")
    
    def restore_snapshot(self, build_id: str) -> bool:
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT commit_hash, branch_name, snapshot_data 
                FROM repo_snapshots 
                WHERE build_id = %s
            """, (build_id,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if not result:
                return False
            
            commit_hash, branch_name, snapshot_data = result
            
            # Backup current state
            backup_path = f"/tmp/repo_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copytree(self.repo_path, backup_path)
            
            # Clear current repository
            shutil.rmtree(self.repo_path)
            self.repo_path.mkdir(parents=True)
            
            # Extract snapshot
            snapshot_path = f"/tmp/restore_{build_id}.tar.gz"
            with open(snapshot_path, "wb") as f:
                f.write(snapshot_data)
            
            with tarfile.open(snapshot_path, "r:gz") as tar:
                tar.extractall(self.repo_path)
            
            # Reinitialize git repo
            self.git_repo = git.Repo(self.repo_path)
            
            # Cleanup
            os.remove(snapshot_path)
            
            return True
            
        except Exception as e:
            print(f"Error restoring snapshot: {e}")
            return False
    
    def get_file_history(self, file_path: str) -> List[Dict]:
        try:
            commits = list(self.git_repo.iter_commits(paths=file_path))
            history = []
            
            for commit in commits:
                history.append({
                    'hash': commit.hexsha,
                    'message': commit.message.strip(),
                    'author': str(commit.author),
                    'date': datetime.fromtimestamp(commit.committed_date),
                    'files_changed': len(commit.stats.files)
                })
            
            return history
        except Exception as e:
            print(f"Error getting file history: {e}")
            return []
    
    def get_diff(self, commit1: str, commit2: str = None) -> str:
        try:
            if commit2:
                return self.git_repo.git.diff(commit1, commit2)
            else:
                return self.git_repo.git.diff(commit1)
        except Exception as e:
            print(f"Error getting diff: {e}")
            return ""
    
    def add_build_config(self, config_name: str, config_content: str) -> str:
        config_path = self.repo_path / "configs" / f"{config_name}.yaml"
        config_path.write_text(config_content)
        return str(config_path)
    
    def add_build_script(self, script_name: str, script_content: str) -> str:
        script_path = self.repo_path / "scripts" / f"{script_name}.sh"
        script_path.write_text(script_content)
        script_path.chmod(0o755)  # Make executable
        return str(script_path)
    
    def add_patch(self, patch_name: str, patch_content: str) -> str:
        patch_path = self.repo_path / "patches" / f"{patch_name}.patch"
        patch_path.write_text(patch_content)
        return str(patch_path)
    
    def list_configs(self) -> List[Dict]:
        configs_dir = self.repo_path / "configs"
        configs = []
        
        for config_file in configs_dir.glob("*.yaml"):
            stat = config_file.stat()
            configs.append({
                'name': config_file.stem,
                'path': str(config_file),
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime)
            })
        
        return configs
    
    def get_repository_status(self) -> Dict:
        try:
            status = {
                'current_branch': self.git_repo.active_branch.name,
                'branches': [branch.name for branch in self.git_repo.branches],
                'uncommitted_changes': len(self.git_repo.index.diff(None)) > 0,
                'untracked_files': len(self.git_repo.untracked_files) > 0,
                'last_commit': {
                    'hash': self.git_repo.head.commit.hexsha,
                    'message': self.git_repo.head.commit.message.strip(),
                    'date': datetime.fromtimestamp(self.git_repo.head.commit.committed_date)
                }
            }
            return status
        except Exception as e:
            print(f"Error getting repository status: {e}")
            return {}
    
    def search_repository(self, query: str) -> List[Dict]:
        results = []
        
        # Search in files
        for file_path in self.repo_path.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    content = file_path.read_text()
                    if query.lower() in content.lower():
                        results.append({
                            'type': 'file',
                            'path': str(file_path.relative_to(self.repo_path)),
                            'matches': content.lower().count(query.lower())
                        })
                except:
                    pass  # Skip binary files
        
        # Search in commit messages
        try:
            commits = list(self.git_repo.iter_commits())
            for commit in commits:
                if query.lower() in commit.message.lower():
                    results.append({
                        'type': 'commit',
                        'hash': commit.hexsha,
                        'message': commit.message.strip(),
                        'date': datetime.fromtimestamp(commit.committed_date)
                    })
        except:
            pass
        
        return results