"""
Model Manager for ML Engine

Handles model storage, versioning, and lifecycle management.
"""

import os
import json
import pickle
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib


class ModelManager:
    """Manages ML model storage and versioning"""
    
    def __init__(self, storage_path: str = "ml_models"):
        """Initialize model manager with storage path"""
        self.storage_path = storage_path
        self.logger = logging.getLogger(__name__)
        
        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Model registry file
        self.registry_file = os.path.join(self.storage_path, "model_registry.json")
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict:
        """Load model registry from disk"""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load model registry: {e}")
        
        return {"models": {}, "last_updated": datetime.now().isoformat()}
    
    def _save_registry(self):
        """Save model registry to disk"""
        try:
            self.registry["last_updated"] = datetime.now().isoformat()
            with open(self.registry_file, 'w') as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save model registry: {e}")
    
    def save_model(self, model_name: str, model_data: Any, metadata: Dict = None) -> bool:
        """Save model with metadata"""
        try:
            # Generate model version based on content hash
            model_hash = hashlib.md5(str(model_data).encode()).hexdigest()[:8]
            version = f"v{datetime.now().strftime('%Y%m%d')}_{model_hash}"
            
            # Create model directory
            model_dir = os.path.join(self.storage_path, model_name)
            os.makedirs(model_dir, exist_ok=True)
            
            # Save model file
            model_file = os.path.join(model_dir, f"{version}.pkl")
            with open(model_file, 'wb') as f:
                pickle.dump(model_data, f)
            
            # Save metadata
            metadata_file = os.path.join(model_dir, f"{version}_metadata.json")
            full_metadata = {
                "model_name": model_name,
                "version": version,
                "created_at": datetime.now().isoformat(),
                "file_path": model_file,
                **(metadata or {})
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(full_metadata, f, indent=2)
            
            # Update registry
            if model_name not in self.registry["models"]:
                self.registry["models"][model_name] = {"versions": []}
            
            self.registry["models"][model_name]["versions"].append({
                "version": version,
                "created_at": full_metadata["created_at"],
                "metadata": full_metadata
            })
            
            # Keep only last 5 versions in registry
            versions = self.registry["models"][model_name]["versions"]
            if len(versions) > 5:
                # Remove old model files
                for old_version in versions[:-5]:
                    try:
                        old_model_file = old_version["metadata"]["file_path"]
                        if os.path.exists(old_model_file):
                            os.remove(old_model_file)
                        
                        old_metadata_file = old_model_file.replace(".pkl", "_metadata.json")
                        if os.path.exists(old_metadata_file):
                            os.remove(old_metadata_file)
                    except Exception as e:
                        self.logger.warning(f"Failed to cleanup old model version: {e}")
                
                self.registry["models"][model_name]["versions"] = versions[-5:]
            
            self._save_registry()
            self.logger.info(f"Saved model {model_name} version {version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save model {model_name}: {e}")
            return False
    
    def load_model(self, model_name: str, version: Optional[str] = None) -> Optional[Any]:
        """Load model by name and optional version"""
        try:
            if model_name not in self.registry["models"]:
                return None
            
            versions = self.registry["models"][model_name]["versions"]
            if not versions:
                return None
            
            # Use latest version if not specified
            if version is None:
                target_version = versions[-1]
            else:
                target_version = next((v for v in versions if v["version"] == version), None)
                if not target_version:
                    return None
            
            model_file = target_version["metadata"]["file_path"]
            if not os.path.exists(model_file):
                self.logger.warning(f"Model file not found: {model_file}")
                return None
            
            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)
            
            self.logger.info(f"Loaded model {model_name} version {target_version['version']}")
            return model_data
            
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {e}")
            return None
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """Get model information and metadata"""
        if model_name not in self.registry["models"]:
            return None
        
        model_info = self.registry["models"][model_name]
        if not model_info["versions"]:
            return None
        
        latest_version = model_info["versions"][-1]
        return {
            "model_name": model_name,
            "latest_version": latest_version["version"],
            "created_at": latest_version["created_at"],
            "total_versions": len(model_info["versions"]),
            "metadata": latest_version["metadata"]
        }
    
    def list_models(self) -> List[Dict]:
        """List all available models"""
        models = []
        for model_name in self.registry["models"]:
            model_info = self.get_model_info(model_name)
            if model_info:
                models.append(model_info)
        return models
    
    def delete_model(self, model_name: str) -> bool:
        """Delete model and all its versions"""
        try:
            if model_name not in self.registry["models"]:
                return False
            
            # Delete all model files
            model_dir = os.path.join(self.storage_path, model_name)
            if os.path.exists(model_dir):
                import shutil
                shutil.rmtree(model_dir)
            
            # Remove from registry
            del self.registry["models"][model_name]
            self._save_registry()
            
            self.logger.info(f"Deleted model {model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete model {model_name}: {e}")
            return False
    
    def train_models(self) -> Dict:
        """Train models - interface method for ML engine"""
        # This is a placeholder - actual training is handled by individual models
        return {
            "trained_models": [],
            "errors": ["Training handled by individual model classes"]
        }
    
    def update_models(self) -> Dict:
        """Update models - interface method for ML engine"""
        try:
            models = self.list_models()
            updated_count = 0
            
            for model_info in models:
                # Check if model needs updating (placeholder logic)
                model_name = model_info["model_name"]
                self.logger.info(f"Checking model {model_name} for updates")
                updated_count += 1
            
            return {
                "success": True,
                "updated_models": updated_count,
                "total_models": len(models)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_model_versions(self) -> Dict:
        """Get model versions - interface method for ML engine"""
        try:
            versions = {}
            for model_name in self.registry["models"]:
                model_versions = self.registry["models"][model_name]["versions"]
                versions[model_name] = [v["version"] for v in model_versions]
            
            return versions
            
        except Exception as e:
            self.logger.error(f"Failed to get model versions: {e}")
            return {}