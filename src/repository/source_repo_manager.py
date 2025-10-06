import os
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

class SourceRepositoryManager:
    """Manages LFS source package repositories with Git integration"""
    
    def __init__(self, db_manager, repo_manager):
        self.db = db_manager
        self.repo = repo_manager
        self.setup_database()
    
    def setup_database(self):
        """Setup download tracking tables"""
        try:
            schema_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'download_schema.sql')
            if os.path.exists(schema_path):
                with open(schema_path, 'r') as f:
                    schema = f.read()
                    for statement in schema.split(';'):
                        if statement.strip():
                            self.db.execute_query(statement)
        except Exception as e:
            print(f"Error setting up download schema: {e}")
    
    def create_source_repository(self, lfs_version="12.4"):
        """Create a dedicated Git repository for LFS source packages"""
        try:
            # Create sources branch
            branch_name = f"sources-{lfs_version}"
            
            if not self.repo.create_branch(branch_name):
                print(f"Branch {branch_name} already exists")
            
            # Switch to sources branch
            self.repo.switch_branch(branch_name)
            
            # Create sources directory structure
            sources_dir = os.path.join(self.repo.repo_path, "sources", lfs_version)
            os.makedirs(sources_dir, exist_ok=True)
            
            # Create README for sources
            readme_content = f"""# LFS {lfs_version} Source Packages

This directory contains all source packages for Linux From Scratch version {lfs_version}.

## Package Information
- Version: {lfs_version}
- Created: {datetime.now().isoformat()}
- Total packages: 85+ core LFS packages

## Usage
These packages are used by the LFS build system for creating Linux From Scratch builds.
All packages are verified with checksums and tracked in the database.
"""
            
            readme_path = os.path.join(sources_dir, "README.md")
            with open(readme_path, 'w') as f:
                f.write(readme_content)
            
            # Stage and commit
            self.repo.stage_all_changes()
            self.repo.commit_changes(f"Initialize LFS {lfs_version} source repository")
            
            # Record in database
            self.db.execute_query("""
                INSERT INTO source_repositories (lfs_version, repo_path, git_branch)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE last_updated = CURRENT_TIMESTAMP
            """, (lfs_version, sources_dir, branch_name))
            
            return sources_dir
            
        except Exception as e:
            print(f"Error creating source repository: {e}")
            return None
    
    def add_package_to_repository(self, lfs_version, package_name, file_path, download_info):
        """Add downloaded package to Git repository and database"""
        try:
            # Check if package already exists in database
            if self.is_package_downloaded(lfs_version, package_name):
                print(f"Package {package_name} already exists in repository")
                return True
            
            sources_dir = os.path.join(self.repo.repo_path, "sources", lfs_version)
            if not os.path.exists(sources_dir):
                sources_dir = self.create_source_repository(lfs_version)
            
            # Switch to sources branch
            branch_name = f"sources-{lfs_version}"
            self.repo.switch_branch(branch_name)
            
            # Copy package to repository
            dest_path = os.path.join(sources_dir, os.path.basename(file_path))
            if not os.path.exists(dest_path):
                shutil.copy2(file_path, dest_path)
            
            # Calculate checksums
            md5_hash = self._calculate_checksum(dest_path, 'md5')
            sha256_hash = self._calculate_checksum(dest_path, 'sha256')
            file_size = os.path.getsize(dest_path)
            
            # Extract package version from filename if possible
            package_version = self._extract_package_version(package_name)
            
            # Stage and commit package
            self.repo.stage_file(dest_path)
            commit_msg = f"Add {package_name} to LFS {lfs_version} sources\n\nPackage: {package_name}\nVersion: {package_version}\nFile: {os.path.basename(file_path)}\nSize: {file_size} bytes\nMD5: {md5_hash}\nSHA256: {sha256_hash}\nSource: {download_info.get('mirror_url', 'Unknown')}\nDownload time: {download_info.get('duration_ms', 0)}ms"
            self.repo.commit_changes(commit_msg)
            
            # Get commit hash
            commit_hash = self.repo.get_latest_commit_hash()
            
            # Record download in database with enhanced metadata
            self.db.execute_query("""
                INSERT INTO package_downloads 
                (lfs_version, package_name, package_version, file_name, download_url, mirror_url, 
                 file_size, checksum_md5, checksum_sha256, download_date, 
                 download_duration_ms, git_commit_hash, success)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                lfs_version,
                package_name,
                package_version,
                os.path.basename(file_path),
                download_info.get('original_url', ''),
                download_info.get('mirror_url', ''),
                file_size,
                md5_hash,
                sha256_hash,
                datetime.now(),
                download_info.get('duration_ms', 0),
                commit_hash,
                True
            ))
            
            print(f"Successfully added {package_name} to LFS {lfs_version} repository")
            return True
            
        except Exception as e:
            # Record failed download in database
            try:
                self.db.execute_query("""
                    INSERT INTO package_downloads 
                    (lfs_version, package_name, file_name, download_url, mirror_url, 
                     download_date, success, error_message)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    lfs_version,
                    package_name,
                    os.path.basename(file_path) if file_path else '',
                    download_info.get('original_url', ''),
                    download_info.get('mirror_url', ''),
                    datetime.now(),
                    False,
                    str(e)
                ))
            except:
                pass
            
            print(f"Error adding package to repository: {e}")
            return False
    
    def get_source_repository_path(self, lfs_version="12.4"):
        """Get the path to the source repository for a specific LFS version"""
        try:
            result = self.db.execute_query("""
                SELECT repo_path FROM source_repositories 
                WHERE lfs_version = %s
            """, (lfs_version,), fetch=True)
            
            if result:
                return result[0]['repo_path']
            else:
                # Create repository if it doesn't exist
                return self.create_source_repository(lfs_version)
                
        except Exception as e:
            print(f"Error getting source repository path: {e}")
            return None
    
    def get_downloaded_packages(self, lfs_version="12.4"):
        """Get list of downloaded packages for a specific LFS version"""
        try:
            return self.db.execute_query("""
                SELECT package_name, package_version, file_name, file_size, 
                       checksum_md5, checksum_sha256, download_date, mirror_url, 
                       git_commit_hash, download_duration_ms
                FROM package_downloads 
                WHERE lfs_version = %s AND success = TRUE
                ORDER BY download_date DESC
            """, (lfs_version,), fetch=True)
        except Exception as e:
            print(f"Error getting downloaded packages: {e}")
            return []
    
    def is_package_downloaded(self, lfs_version, package_name):
        """Check if a package is already downloaded and in repository"""
        try:
            result = self.db.execute_query("""
                SELECT COUNT(*) as count FROM package_downloads 
                WHERE lfs_version = %s AND package_name = %s AND success = TRUE
            """, (lfs_version, package_name), fetch=True)
            
            return result[0]['count'] > 0 if result else False
        except Exception as e:
            print(f"Error checking package download status: {e}")
            return False
    
    def get_repository_stats(self, lfs_version="12.4"):
        """Get statistics for a source repository"""
        try:
            return self.db.execute_query("""
                SELECT sr.*, 
                       COUNT(pd.id) as actual_downloaded,
                       SUM(pd.file_size) as actual_size
                FROM source_repositories sr
                LEFT JOIN package_downloads pd ON sr.lfs_version = pd.lfs_version 
                    AND pd.success = TRUE
                WHERE sr.lfs_version = %s
                GROUP BY sr.id
            """, (lfs_version,), fetch=True)
        except Exception as e:
            print(f"Error getting repository stats: {e}")
            return []
    
    def _calculate_checksum(self, file_path, algorithm='md5'):
        """Calculate checksum for a file"""
        hash_obj = hashlib.md5() if algorithm == 'md5' else hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    def _extract_package_version(self, package_name):
        """Extract version from package filename"""
        import re
        # Common patterns for version extraction
        patterns = [
            r'-(\d+\.\d+\.\d+)',  # x.y.z
            r'-(\d+\.\d+)',       # x.y
            r'-(\d+)',            # x
        ]
        
        for pattern in patterns:
            match = re.search(pattern, package_name)
            if match:
                return match.group(1)
        
        return 'unknown'
    
    def _update_repository_stats(self, lfs_version):
        """Update repository statistics (now handled by database trigger)"""
        # Stats are automatically updated by database trigger
        # This method kept for compatibility
        pass