import os
import json
import hashlib
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import git
from git.exc import GitCommandError

from ..database.db_manager import DatabaseManager
from ..config.settings_manager import SettingsManager

class RepositoryManager:
    def __init__(self, db_manager: DatabaseManager, repo_path: str = None):
        self.db = db_manager
        self.settings = SettingsManager()
        
        if repo_path is None:
            repo_path = self.settings.get_repository_path()
        
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
            
            # Set up default branch as main if not already
            try:
                if self.git_repo.active_branch.name != 'main':
                    self.git_repo.git.branch('-M', 'main')
            except:
                pass
        else:
            self.git_repo = git.Repo(self.repo_path)
    
    def create_branch(self, branch_name: str, from_branch: str = None, checkout: bool = True) -> bool:
        """Enhanced branch creation with flexible source"""
        try:
            # Check if branch already exists
            if branch_name in [b.name for b in self.git_repo.branches]:
                print(f"Branch {branch_name} already exists")
                if checkout:
                    return self.switch_branch(branch_name)
                return True
            
            if from_branch:
                # Create from specific branch/commit
                new_branch = self.git_repo.create_head(branch_name, from_branch)
            else:
                # Create from current HEAD
                new_branch = self.git_repo.create_head(branch_name)
            
            if checkout:
                new_branch.checkout()
            
            return True
        except Exception as e:
            print(f"Error creating branch: {e}")
            return False
    
    def switch_branch(self, branch_name: str) -> bool:
        try:
            # Handle branches with slashes (like build/xxx)
            if '/' in branch_name:
                # Check if it's a local branch first
                local_branches = [b.name for b in self.git_repo.branches]
                if branch_name in local_branches:
                    self.git_repo.git.checkout(branch_name)
                else:
                    # Try to checkout as new local branch from remote
                    self.git_repo.git.checkout('-b', branch_name, f'origin/{branch_name}')
            else:
                self.git_repo.git.checkout(branch_name)
            return True
        except Exception as e:
            print(f"Error switching branch: {e}")
            return False
    
    def list_branches(self) -> List[str]:
        return [branch.name for branch in self.git_repo.branches]
    
    def commit_changes(self, message: str, build_id: str = None, amend: bool = False) -> str:
        """Enhanced commit with amend support"""
        try:
            # Check if there are changes to commit (unless amending)
            if not amend and not self.git_repo.index.diff("HEAD") and not self.git_repo.untracked_files:
                return self.git_repo.head.commit.hexsha
            
            # Commit with metadata
            commit_message = message
            if build_id:
                commit_message += f"\n\nBuild-ID: {build_id}"
            
            if amend:
                commit = self.git_repo.git.commit('--amend', '-m', commit_message)
                commit_hash = self.git_repo.head.commit.hexsha
            else:
                commit = self.git_repo.index.commit(commit_message)
                commit_hash = commit.hexsha
            
            # Store snapshot in database if build_id provided
            if build_id:
                self._store_snapshot(build_id, commit_hash)
            
            return commit_hash
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
    
    def get_file_history(self, file_path: str, max_count: int = 50) -> List[Dict]:
        """Enhanced file history with diff information"""
        try:
            commits = list(self.git_repo.iter_commits(paths=file_path, max_count=max_count))
            history = []
            
            for i, commit in enumerate(commits):
                commit_info = {
                    'hash': commit.hexsha,
                    'short_hash': commit.hexsha[:8],
                    'message': commit.message.strip(),
                    'author': str(commit.author),
                    'author_email': commit.author.email,
                    'date': datetime.fromtimestamp(commit.committed_date),
                    'files_changed': len(commit.stats.files)
                }
                
                # Get diff for this file in this commit
                if i < len(commits) - 1:
                    try:
                        diff = self.git_repo.git.diff(commits[i+1].hexsha, commit.hexsha, '--', file_path)
                        commit_info['diff'] = diff
                    except:
                        commit_info['diff'] = ''
                
                history.append(commit_info)
            
            return history
        except Exception as e:
            print(f"Error getting file history: {e}")
            return []
    
    def get_diff(self, commit1: str, commit2: str = None, file_path: str = None, staged: bool = False) -> str:
        """Enhanced diff with file-specific and staged options"""
        try:
            args = []
            if staged:
                args.append('--cached')
            
            if commit2:
                args.extend([commit1, commit2])
            elif commit1:
                args.append(commit1)
            
            if file_path:
                args.extend(['--', file_path])
            
            return self.git_repo.git.diff(*args)
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
        """Enhanced repository status with detailed information"""
        try:
            detailed_status = self.get_detailed_status()
            
            status = {
                'current_branch': self.git_repo.active_branch.name,
                'branches': [branch.name for branch in self.git_repo.branches],
                'remotes': [remote.name for remote in self.git_repo.remotes],
                'tags': [tag.name for tag in self.git_repo.tags],
                'staged_files': detailed_status['staged'],
                'modified_files': detailed_status['modified'],
                'untracked_files': detailed_status['untracked'],
                'deleted_files': detailed_status['deleted'],
                'renamed_files': detailed_status['renamed'],
                'conflicted_files': detailed_status['conflicted'],
                'stashes': len(self.list_stashes()),
                'last_commit': {
                    'hash': self.git_repo.head.commit.hexsha,
                    'short_hash': self.git_repo.head.commit.hexsha[:8],
                    'message': self.git_repo.head.commit.message.strip(),
                    'author': str(self.git_repo.head.commit.author),
                    'date': datetime.fromtimestamp(self.git_repo.head.commit.committed_date)
                },
                'is_dirty': self.git_repo.is_dirty(),
                'head_is_detached': self.git_repo.head.is_detached
            }
            
            # Check for ongoing operations
            git_dir = self.repo_path / ".git"
            status['ongoing_merge'] = (git_dir / "MERGE_HEAD").exists()
            status['ongoing_rebase'] = (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()
            status['ongoing_cherry_pick'] = (git_dir / "CHERRY_PICK_HEAD").exists()
            
            return status
        except Exception as e:
            print(f"Error getting repository status: {e}")
            return {}
    
    def search_repository(self, query: str, search_type: str = 'all') -> List[Dict]:
        """Enhanced repository search with type filtering"""
        results = []
        
        if search_type in ['all', 'files']:
            # Search in files
            for file_path in self.repo_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    try:
                        content = file_path.read_text()
                        if query.lower() in content.lower():
                            results.append({
                                'type': 'file',
                                'path': str(file_path.relative_to(self.repo_path)),
                                'matches': content.lower().count(query.lower()),
                                'size': file_path.stat().st_size,
                                'modified': datetime.fromtimestamp(file_path.stat().st_mtime)
                            })
                    except:
                        pass  # Skip binary files
        
        if search_type in ['all', 'commits']:
            # Search in commit messages
            try:
                commits = list(self.git_repo.iter_commits())
                for commit in commits:
                    if query.lower() in commit.message.lower():
                        results.append({
                            'type': 'commit',
                            'hash': commit.hexsha,
                            'short_hash': commit.hexsha[:8],
                            'message': commit.message.strip(),
                            'author': str(commit.author),
                            'date': datetime.fromtimestamp(commit.committed_date)
                        })
            except:
                pass
        
        if search_type in ['all', 'branches']:
            # Search in branch names
            for branch in self.git_repo.branches:
                if query.lower() in branch.name.lower():
                    results.append({
                        'type': 'branch',
                        'name': branch.name,
                        'commit': branch.commit.hexsha,
                        'message': branch.commit.message.strip(),
                        'date': datetime.fromtimestamp(branch.commit.committed_date)
                    })
        
        if search_type in ['all', 'tags']:
            # Search in tag names
            for tag in self.git_repo.tags:
                if query.lower() in tag.name.lower():
                    tag_info = {
                        'type': 'tag',
                        'name': tag.name,
                        'commit': tag.commit.hexsha,
                        'date': datetime.fromtimestamp(tag.commit.committed_date)
                    }
                    if hasattr(tag.tag, 'message') and tag.tag.message:
                        tag_info['message'] = tag.tag.message.strip()
                    results.append(tag_info)
        
        return results
    
    # === STAGING AREA OPERATIONS ===
    
    def stage_file(self, file_path: str) -> bool:
        """Add file to staging area"""
        try:
            self.git_repo.index.add([file_path])
            return True
        except Exception as e:
            print(f"Error staging file: {e}")
            return False
    
    def unstage_file(self, file_path: str) -> bool:
        """Remove file from staging area"""
        try:
            self.git_repo.index.reset([file_path])
            return True
        except Exception as e:
            print(f"Error unstaging file: {e}")
            return False
    
    def get_staged_files(self) -> List[str]:
        """List files in staging area"""
        try:
            return [item.a_path for item in self.git_repo.index.diff("HEAD")]
        except:
            return []
    
    def get_detailed_status(self) -> Dict:
        """Git status equivalent with staged/unstaged/untracked"""
        try:
            status = {
                'staged': [],
                'modified': [],
                'untracked': [],
                'deleted': [],
                'renamed': [],
                'conflicted': []
            }
            
            # Staged files (index vs HEAD)
            for item in self.git_repo.index.diff("HEAD"):
                if item.change_type == 'D':
                    status['deleted'].append(item.a_path)
                elif item.change_type == 'R':
                    status['renamed'].append(f"{item.a_path} -> {item.b_path}")
                else:
                    status['staged'].append(item.a_path)
            
            # Modified files (working tree vs index)
            for item in self.git_repo.index.diff(None):
                if item.change_type == 'D':
                    status['deleted'].append(item.a_path)
                else:
                    status['modified'].append(item.a_path)
            
            # Untracked files
            status['untracked'] = self.git_repo.untracked_files
            
            return status
        except Exception as e:
            print(f"Error getting detailed status: {e}")
            return {'staged': [], 'modified': [], 'untracked': [], 'deleted': [], 'renamed': [], 'conflicted': []}
    
    # === STASH OPERATIONS ===
    
    def stash_changes(self, message: str = "") -> str:
        """Save current changes to stash"""
        try:
            stash_message = message or f"WIP on {self.git_repo.active_branch.name}: {self.git_repo.head.commit.message.strip()[:50]}"
            self.git_repo.git.stash('push', '-m', stash_message)
            return stash_message
        except Exception as e:
            print(f"Error stashing changes: {e}")
            return ""
    
    def apply_stash(self, stash_id: str = "stash@{0}") -> bool:
        """Apply stashed changes"""
        try:
            self.git_repo.git.stash('apply', stash_id)
            return True
        except Exception as e:
            print(f"Error applying stash: {e}")
            return False
    
    def pop_stash(self, stash_id: str = "stash@{0}") -> bool:
        """Apply and remove stash"""
        try:
            self.git_repo.git.stash('pop', stash_id)
            return True
        except Exception as e:
            print(f"Error popping stash: {e}")
            return False
    
    def drop_stash(self, stash_id: str = "stash@{0}") -> bool:
        """Delete stash without applying"""
        try:
            self.git_repo.git.stash('drop', stash_id)
            return True
        except Exception as e:
            print(f"Error dropping stash: {e}")
            return False
    
    def list_stashes(self) -> List[Dict]:
        """List all stashes"""
        try:
            stash_list = self.git_repo.git.stash('list').split('\n')
            stashes = []
            for stash in stash_list:
                if stash.strip():
                    parts = stash.split(': ', 2)
                    if len(parts) >= 3:
                        stashes.append({
                            'id': parts[0],
                            'branch': parts[1],
                            'message': parts[2]
                        })
            return stashes
        except Exception as e:
            print(f"Error listing stashes: {e}")
            return []
    
    # === TAG MANAGEMENT ===
    
    def create_tag(self, tag_name: str, message: str = "", commit: str = None) -> bool:
        """Create annotated tag"""
        try:
            if message:
                if commit:
                    self.git_repo.create_tag(tag_name, ref=commit, message=message)
                else:
                    self.git_repo.create_tag(tag_name, message=message)
            else:
                if commit:
                    self.git_repo.create_tag(tag_name, ref=commit)
                else:
                    self.git_repo.create_tag(tag_name)
            return True
        except Exception as e:
            print(f"Error creating tag: {e}")
            return False
    
    def delete_tag(self, tag_name: str) -> bool:
        """Delete tag"""
        try:
            self.git_repo.delete_tag(tag_name)
            return True
        except Exception as e:
            print(f"Error deleting tag: {e}")
            return False
    
    def list_tags(self) -> List[Dict]:
        """List all tags with details"""
        try:
            tags = []
            for tag in self.git_repo.tags:
                tag_info = {
                    'name': tag.name,
                    'commit': tag.commit.hexsha,
                    'date': datetime.fromtimestamp(tag.commit.committed_date)
                }
                if hasattr(tag.tag, 'message') and tag.tag.message:
                    tag_info['message'] = tag.tag.message.strip()
                tags.append(tag_info)
            return sorted(tags, key=lambda x: x['date'], reverse=True)
        except Exception as e:
            print(f"Error listing tags: {e}")
            return []
    
    # === ENHANCED DIFF OPERATIONS ===
    
    def get_file_diff(self, file_path: str, staged: bool = False) -> str:
        """Show diff for specific file"""
        try:
            if staged:
                return self.git_repo.git.diff('--cached', file_path)
            else:
                return self.git_repo.git.diff(file_path)
        except Exception as e:
            print(f"Error getting file diff: {e}")
            return ""
    
    def get_commit_diff(self, commit_hash: str) -> Dict:
        """Show what changed in a commit"""
        try:
            commit = self.git_repo.commit(commit_hash)
            diff_text = self.git_repo.git.show(commit_hash)
            
            # Get file stats
            stats = commit.stats.files
            files_changed = []
            for file_path, changes in stats.items():
                files_changed.append({
                    'path': file_path,
                    'insertions': changes['insertions'],
                    'deletions': changes['deletions']
                })
            
            return {
                'commit': commit_hash,
                'message': commit.message.strip(),
                'author': str(commit.author),
                'date': datetime.fromtimestamp(commit.committed_date),
                'diff': diff_text,
                'files_changed': files_changed,
                'total_insertions': commit.stats.total['insertions'],
                'total_deletions': commit.stats.total['deletions']
            }
        except Exception as e:
            print(f"Error getting commit diff: {e}")
            return {}
    
    # === MERGE OPERATIONS ===
    
    def merge_branch(self, branch_name: str, no_ff: bool = False) -> Tuple[bool, str]:
        """Merge another branch into current"""
        try:
            if no_ff:
                self.git_repo.git.merge(branch_name, '--no-ff')
            else:
                self.git_repo.git.merge(branch_name)
            return True, "Merge completed successfully"
        except GitCommandError as e:
            if "CONFLICT" in str(e):
                return False, "Merge conflicts detected - resolve manually"
            return False, f"Merge failed: {e}"
        except Exception as e:
            return False, f"Error during merge: {e}"
    
    def abort_merge(self) -> bool:
        """Abort current merge"""
        try:
            self.git_repo.git.merge('--abort')
            return True
        except Exception as e:
            print(f"Error aborting merge: {e}")
            return False
    
    def get_merge_conflicts(self) -> List[str]:
        """Get list of files with merge conflicts"""
        try:
            status = self.git_repo.git.status('--porcelain')
            conflicts = []
            for line in status.split('\n'):
                if line.startswith('UU ') or line.startswith('AA '):
                    conflicts.append(line[3:])
            return conflicts
        except Exception as e:
            print(f"Error getting merge conflicts: {e}")
            return []
    
    def resolve_conflict(self, file_path: str, resolution: str) -> bool:
        """Mark conflict as resolved"""
        try:
            # Write resolution to file
            full_path = self.repo_path / file_path
            full_path.write_text(resolution)
            
            # Stage the resolved file
            self.git_repo.index.add([file_path])
            return True
        except Exception as e:
            print(f"Error resolving conflict: {e}")
            return False
    
    # === RESET OPERATIONS ===
    
    def reset_soft(self, commit_hash: str) -> bool:
        """Reset to commit, keep changes staged"""
        try:
            self.git_repo.git.reset('--soft', commit_hash)
            return True
        except Exception as e:
            print(f"Error in soft reset: {e}")
            return False
    
    def reset_mixed(self, commit_hash: str) -> bool:
        """Reset to commit, unstage changes"""
        try:
            self.git_repo.git.reset('--mixed', commit_hash)
            return True
        except Exception as e:
            print(f"Error in mixed reset: {e}")
            return False
    
    def reset_hard(self, commit_hash: str) -> bool:
        """Reset to commit, discard all changes"""
        try:
            self.git_repo.git.reset('--hard', commit_hash)
            return True
        except Exception as e:
            print(f"Error in hard reset: {e}")
            return False
    
    # === REBASE OPERATIONS ===
    
    def interactive_rebase(self, base_commit: str) -> Tuple[bool, str]:
        """Start interactive rebase"""
        try:
            self.git_repo.git.rebase('-i', base_commit)
            return True, "Interactive rebase started"
        except GitCommandError as e:
            if "CONFLICT" in str(e):
                return False, "Rebase conflicts detected - resolve manually"
            return False, f"Rebase failed: {e}"
        except Exception as e:
            return False, f"Error starting rebase: {e}"
    
    def rebase_continue(self) -> Tuple[bool, str]:
        """Continue rebase after conflict resolution"""
        try:
            self.git_repo.git.rebase('--continue')
            return True, "Rebase continued"
        except GitCommandError as e:
            if "CONFLICT" in str(e):
                return False, "More conflicts detected - resolve manually"
            return False, f"Rebase continue failed: {e}"
        except Exception as e:
            return False, f"Error continuing rebase: {e}"
    
    def rebase_abort(self) -> bool:
        """Abort current rebase"""
        try:
            self.git_repo.git.rebase('--abort')
            return True
        except Exception as e:
            print(f"Error aborting rebase: {e}")
            return False
    
    def rebase_skip(self) -> bool:
        """Skip current commit in rebase"""
        try:
            self.git_repo.git.rebase('--skip')
            return True
        except Exception as e:
            print(f"Error skipping rebase commit: {e}")
            return False
    
    # === CHERRY-PICK OPERATIONS ===
    
    def cherry_pick(self, commit_hash: str) -> Tuple[bool, str]:
        """Apply specific commit to current branch"""
        try:
            self.git_repo.git.cherry_pick(commit_hash)
            return True, "Cherry-pick completed successfully"
        except GitCommandError as e:
            if "CONFLICT" in str(e):
                return False, "Cherry-pick conflicts detected - resolve manually"
            return False, f"Cherry-pick failed: {e}"
        except Exception as e:
            return False, f"Error during cherry-pick: {e}"
    
    def cherry_pick_abort(self) -> bool:
        """Abort current cherry-pick"""
        try:
            self.git_repo.git.cherry_pick('--abort')
            return True
        except Exception as e:
            print(f"Error aborting cherry-pick: {e}")
            return False
    
    def cherry_pick_continue(self) -> bool:
        """Continue cherry-pick after conflict resolution"""
        try:
            self.git_repo.git.cherry_pick('--continue')
            return True
        except Exception as e:
            print(f"Error continuing cherry-pick: {e}")
            return False
    
    # === COMMIT GRAPH AND LOG ===
    
    def get_commit_graph(self, max_count: int = 50) -> List[Dict]:
        """Get commit history with graph information"""
        try:
            commits = []
            for commit in self.git_repo.iter_commits(max_count=max_count):
                commit_info = {
                    'hash': commit.hexsha,
                    'short_hash': commit.hexsha[:8],
                    'message': commit.message.strip(),
                    'author': str(commit.author),
                    'author_email': commit.author.email,
                    'date': datetime.fromtimestamp(commit.committed_date),
                    'parents': [p.hexsha for p in commit.parents],
                    'branches': [],
                    'tags': []
                }
                
                # Find branches containing this commit
                try:
                    branches = self.git_repo.git.branch('--contains', commit.hexsha).split('\n')
                    commit_info['branches'] = [b.strip().replace('* ', '') for b in branches if b.strip()]
                except:
                    pass
                
                # Find tags pointing to this commit
                for tag in self.git_repo.tags:
                    if tag.commit.hexsha == commit.hexsha:
                        commit_info['tags'].append(tag.name)
                
                commits.append(commit_info)
            
            return commits
        except Exception as e:
            print(f"Error getting commit graph: {e}")
            return []
    
    # === BRANCH OPERATIONS ENHANCEMENT ===
    
    def delete_branch(self, branch_name: str, force: bool = False) -> bool:
        """Delete branch"""
        try:
            if force:
                self.git_repo.git.branch('-D', branch_name)
            else:
                self.git_repo.git.branch('-d', branch_name)
            return True
        except Exception as e:
            print(f"Error deleting branch: {e}")
            return False
    
    def rename_branch(self, old_name: str, new_name: str) -> bool:
        """Rename branch"""
        try:
            self.git_repo.git.branch('-m', old_name, new_name)
            return True
        except Exception as e:
            print(f"Error renaming branch: {e}")
            return False
    
    def get_branch_info(self, branch_name: str) -> Dict:
        """Get detailed branch information"""
        try:
            branch = self.git_repo.heads[branch_name]
            ahead_behind = self.git_repo.git.rev_list('--left-right', '--count', f'{branch_name}...origin/{branch_name}').split('\t')
            
            return {
                'name': branch_name,
                'commit': branch.commit.hexsha,
                'message': branch.commit.message.strip(),
                'author': str(branch.commit.author),
                'date': datetime.fromtimestamp(branch.commit.committed_date),
                'ahead': int(ahead_behind[0]) if len(ahead_behind) > 0 else 0,
                'behind': int(ahead_behind[1]) if len(ahead_behind) > 1 else 0
            }
        except Exception as e:
            print(f"Error getting branch info: {e}")
            return {}
    
    # === REMOTE OPERATIONS ===
    
    def add_remote(self, name: str, url: str) -> bool:
        """Add remote repository"""
        try:
            self.git_repo.create_remote(name, url)
            return True
        except Exception as e:
            print(f"Error adding remote: {e}")
            return False
    
    def remove_remote(self, name: str) -> bool:
        """Remove remote repository"""
        try:
            self.git_repo.delete_remote(name)
            return True
        except Exception as e:
            print(f"Error removing remote: {e}")
            return False
    
    def list_remotes(self) -> List[Dict]:
        """List remote repositories"""
        try:
            remotes = []
            for remote in self.git_repo.remotes:
                remotes.append({
                    'name': remote.name,
                    'url': list(remote.urls)[0] if remote.urls else ''
                })
            return remotes
        except Exception as e:
            print(f"Error listing remotes: {e}")
            return []
    
    def get_current_branch(self) -> str:
        """Get current branch name"""
        try:
            return self.git_repo.active_branch.name
        except Exception as e:
            print(f"Error getting current branch: {e}")
            return "main"
    
    def stage_all_changes(self) -> bool:
        """Stage all changes (modified, new, deleted files)"""
        try:
            # Add all files (including new ones)
            self.git_repo.git.add('-A')
            return True
        except Exception as e:
            print(f"Error staging all changes: {e}")
            return False
    
    def get_status(self) -> Dict:
        """Get repository status (alias for get_repository_status)"""
        return self.get_repository_status()
    
    def get_recent_commits(self, max_count: int = 10) -> List[Dict]:
        """Get recent commits"""
        try:
            commits = []
            for commit in self.git_repo.iter_commits(max_count=max_count):
                commits.append({
                    'hash': commit.hexsha,
                    'short_hash': commit.hexsha[:8],
                    'message': commit.message.strip(),
                    'author': str(commit.author),
                    'date': datetime.fromtimestamp(commit.committed_date)
                })
            return commits
        except Exception as e:
            print(f"Error getting recent commits: {e}")
            return []