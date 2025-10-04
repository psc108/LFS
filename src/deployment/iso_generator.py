import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

class ISOGenerator:
    def __init__(self, lfs_root: str = "/mnt/lfs"):
        self.lfs_root = Path(lfs_root)
        self.iso_dir = Path("iso_builds")
        self.iso_dir.mkdir(exist_ok=True)
    
    def create_bootable_iso(self, build_id: str, iso_name: str = None) -> Dict:
        """Create bootable ISO from LFS build"""
        if not iso_name:
            iso_name = f"lfs-{build_id}-{datetime.now().strftime('%Y%m%d')}.iso"
        
        iso_path = self.iso_dir / iso_name
        temp_dir = self.iso_dir / f"temp_{build_id}"
        
        try:
            temp_dir.mkdir(exist_ok=True)
            self._prepare_iso_filesystem(temp_dir)
            self._install_isolinux(temp_dir)
            result = self._generate_iso(temp_dir, iso_path)
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return {
                'success': True,
                'iso_path': str(iso_path),
                'size_mb': round(iso_path.stat().st_size / (1024*1024), 2),
                'build_id': build_id
            }
            
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {'success': False, 'error': str(e)}
    
    def _prepare_iso_filesystem(self, temp_dir: Path):
        """Prepare filesystem for ISO"""
        (temp_dir / "boot").mkdir()
        (temp_dir / "isolinux").mkdir()
        
        kernel_src = self.lfs_root / "boot" / "vmlinuz"
        if kernel_src.exists():
            shutil.copy2(kernel_src, temp_dir / "boot" / "vmlinuz")
        
        self._create_squashfs(temp_dir)
    
    def _create_squashfs(self, temp_dir: Path):
        """Create compressed SquashFS filesystem"""
        squashfs_path = temp_dir / "lfs.squashfs"
        
        cmd = [
            "mksquashfs", str(self.lfs_root),
            str(squashfs_path),
            "-comp", "xz",
            "-e", "boot", "dev", "proc", "sys", "tmp"
        ]
        
        subprocess.run(cmd, check=True)
    
    def _install_isolinux(self, temp_dir: Path):
        """Install ISOLINUX bootloader"""
        isolinux_dir = temp_dir / "isolinux"
        
        isolinux_cfg = isolinux_dir / "isolinux.cfg"
        isolinux_cfg.write_text("""
DEFAULT lfs
LABEL lfs
    KERNEL /boot/vmlinuz
    APPEND root=/dev/ram0 init=/sbin/init

PROMPT 1
TIMEOUT 50
""")
    
    def _generate_iso(self, temp_dir: Path, iso_path: Path) -> bool:
        """Generate ISO image using genisoimage"""
        cmd = [
            "genisoimage",
            "-o", str(iso_path),
            "-b", "isolinux/isolinux.bin",
            "-c", "isolinux/boot.cat",
            "-no-emul-boot",
            "-boot-load-size", "4",
            "-boot-info-table",
            "-J", "-R", "-V", "LFS_LIVE",
            str(temp_dir)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0