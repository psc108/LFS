import json
import os
from pathlib import Path
from typing import Dict, Any

class SettingsManager:
    def __init__(self):
        self.config_dir = Path.home() / ".lfs_build_system"
        self.config_file = self.config_dir / "settings.json"
        self.config_dir.mkdir(exist_ok=True)
        self.settings = self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from config file"""
        default_settings = {
            "repository_path": str(Path.home() / "lfs_repositories"),
            "lfs_build_path": "/mnt/lfs",
            "auto_backup": True,
            "max_parallel_jobs": os.cpu_count(),
            "log_level": "INFO",
            "theme": "default"
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_settings = json.load(f)
                # Merge with defaults to handle new settings
                default_settings.update(loaded_settings)
                return default_settings
            except Exception as e:
                print(f"Error loading settings: {e}")
                return default_settings
        
        return default_settings
    
    def save_settings(self):
        """Save current settings to config file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key: str, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a setting value and save"""
        self.settings[key] = value
        self.save_settings()
    
    def get_repository_path(self) -> str:
        """Get the repository path, creating it if needed"""
        repo_path = Path(self.get("repository_path"))
        repo_path.mkdir(parents=True, exist_ok=True)
        return str(repo_path)
    
    def set_repository_path(self, path: str):
        """Set repository path and create directory"""
        repo_path = Path(path)
        repo_path.mkdir(parents=True, exist_ok=True)
        self.set("repository_path", str(repo_path))
    
    def get_lfs_build_path(self) -> str:
        """Get LFS build path"""
        return self.get("lfs_build_path", "/mnt/lfs")
    
    def set_lfs_build_path(self, path: str):
        """Set LFS build path"""
        self.set("lfs_build_path", path)