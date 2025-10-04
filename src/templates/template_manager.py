import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class BuildTemplateManager:
    def __init__(self, templates_dir: str = None):
        self.templates_dir = Path(templates_dir or "templates")
        self.templates_dir.mkdir(exist_ok=True)
        self._init_default_templates()
    
    def _init_default_templates(self):
        """Initialize default LFS templates"""
        templates = {
            "minimal_lfs": {
                "name": "Minimal LFS",
                "description": "Basic LFS build with essential packages only",
                "category": "minimal",
                "config": {
                    "name": "Minimal Linux From Scratch",
                    "version": "12.4",
                    "target_arch": "x86_64",
                    "optimization": "size",
                    "packages": ["essential"],
                    "stages": self._get_minimal_stages()
                }
            },
            "desktop_lfs": {
                "name": "Desktop LFS",
                "description": "Full desktop environment with GUI applications",
                "category": "desktop",
                "config": {
                    "name": "Desktop Linux From Scratch",
                    "version": "12.4",
                    "target_arch": "x86_64",
                    "optimization": "performance",
                    "packages": ["essential", "xorg", "desktop", "multimedia"],
                    "stages": self._get_desktop_stages()
                }
            },
            "server_lfs": {
                "name": "Server LFS",
                "description": "Server-optimized build with networking and services",
                "category": "server",
                "config": {
                    "name": "Server Linux From Scratch",
                    "version": "12.4",
                    "target_arch": "x86_64",
                    "optimization": "performance",
                    "packages": ["essential", "networking", "server"],
                    "stages": self._get_server_stages()
                }
            }
        }
        
        for template_id, template in templates.items():
            template_file = self.templates_dir / f"{template_id}.json"
            if not template_file.exists():
                with open(template_file, 'w') as f:
                    json.dump(template, f, indent=2)
    
    def _get_minimal_stages(self):
        return [
            {"name": "prepare_host", "order": 1, "command": "bash scripts/prepare_host.sh"},
            {"name": "download_sources", "order": 2, "command": "bash scripts/download_minimal.sh"},
            {"name": "build_toolchain", "order": 3, "command": "bash scripts/build_toolchain.sh"},
            {"name": "build_system", "order": 4, "command": "bash scripts/build_minimal_system.sh"},
            {"name": "configure_system", "order": 5, "command": "bash scripts/configure_minimal.sh"},
            {"name": "build_kernel", "order": 6, "command": "bash scripts/build_kernel_minimal.sh"},
            {"name": "install_bootloader", "order": 7, "command": "bash scripts/install_bootloader.sh"}
        ]
    
    def _get_desktop_stages(self):
        return [
            {"name": "prepare_host", "order": 1, "command": "bash scripts/prepare_host.sh"},
            {"name": "download_sources", "order": 2, "command": "bash scripts/download_desktop.sh"},
            {"name": "build_toolchain", "order": 3, "command": "bash scripts/build_toolchain.sh"},
            {"name": "build_system", "order": 4, "command": "bash scripts/build_system.sh"},
            {"name": "build_xorg", "order": 5, "command": "bash scripts/build_xorg.sh"},
            {"name": "build_desktop", "order": 6, "command": "bash scripts/build_desktop.sh"},
            {"name": "configure_system", "order": 7, "command": "bash scripts/configure_desktop.sh"},
            {"name": "build_kernel", "order": 8, "command": "bash scripts/build_kernel.sh"},
            {"name": "install_bootloader", "order": 9, "command": "bash scripts/install_bootloader.sh"}
        ]
    
    def _get_server_stages(self):
        return [
            {"name": "prepare_host", "order": 1, "command": "bash scripts/prepare_host.sh"},
            {"name": "download_sources", "order": 2, "command": "bash scripts/download_server.sh"},
            {"name": "build_toolchain", "order": 3, "command": "bash scripts/build_toolchain.sh"},
            {"name": "build_system", "order": 4, "command": "bash scripts/build_system.sh"},
            {"name": "build_networking", "order": 5, "command": "bash scripts/build_networking.sh"},
            {"name": "build_services", "order": 6, "command": "bash scripts/build_services.sh"},
            {"name": "configure_system", "order": 7, "command": "bash scripts/configure_server.sh"},
            {"name": "build_kernel", "order": 8, "command": "bash scripts/build_kernel_server.sh"},
            {"name": "install_bootloader", "order": 9, "command": "bash scripts/install_bootloader.sh"}
        ]
    
    def list_templates(self) -> List[Dict]:
        """List all available templates"""
        templates = []
        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    template = json.load(f)
                    template['id'] = template_file.stem
                    templates.append(template)
            except Exception as e:
                print(f"Error loading template {template_file}: {e}")
        return templates
    
    def get_template(self, template_id: str) -> Optional[Dict]:
        """Get specific template"""
        template_file = self.templates_dir / f"{template_id}.json"
        if template_file.exists():
            try:
                with open(template_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading template {template_id}: {e}")
        return None
    
    def generate_config_from_template(self, template_id: str, customizations: Dict = None) -> str:
        """Generate YAML config from template"""
        template = self.get_template(template_id)
        if not template:
            return ""
        
        config = template['config'].copy()
        
        # Apply customizations
        if customizations:
            config.update(customizations)
        
        # Add metadata
        config['template_id'] = template_id
        config['generated_at'] = datetime.now().isoformat()
        
        return yaml.dump(config, default_flow_style=False)