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
    
    def start_iso_generation(self, iso_config: dict) -> str:
        """Start ISO generation and return generation ID"""
        import uuid
        generation_id = f"iso-{uuid.uuid4().hex[:8]}"
        
        try:
            # Extract configuration
            build_id = iso_config.get('source_build_id')
            iso_name = iso_config.get('iso_name', 'lfs-custom.iso')
            output_dir = iso_config.get('output_dir', '/tmp')
            
            # Start generation in background
            import threading
            generation_thread = threading.Thread(
                target=self._run_iso_generation, 
                args=(generation_id, build_id, iso_name, output_dir, iso_config)
            )
            generation_thread.daemon = True
            generation_thread.start()
            
            return generation_id
            
        except Exception as e:
            raise Exception(f"Failed to start ISO generation: {str(e)}")
    
    def _run_iso_generation(self, generation_id: str, build_id: str, iso_name: str, output_dir: str, config: dict):
        """Run the actual ISO generation process"""
        try:
            print(f"Starting ISO generation {generation_id} for build {build_id}")
            
            # Create the ISO
            result = self.create_bootable_iso(build_id, iso_name)
            
            if result.get('success'):
                # Move to output directory
                source_path = Path(result['iso_path'])
                dest_path = Path(output_dir) / iso_name
                
                if source_path != dest_path:
                    shutil.move(str(source_path), str(dest_path))
                
                # Generate checksums if requested
                if config.get('checksums', False):
                    self._generate_checksums(dest_path)
                
                # Create VM image if requested
                if config.get('vm_image', False):
                    self._create_vm_image(dest_path)
                
                print(f"ISO generation {generation_id} completed successfully")
            else:
                print(f"ISO generation {generation_id} failed: {result.get('error')}")
                
        except Exception as e:
            print(f"ISO generation {generation_id} error: {e}")
    
    def _generate_checksums(self, iso_path: Path):
        """Generate MD5 and SHA256 checksums"""
        try:
            # MD5
            result = subprocess.run(['md5sum', str(iso_path)], capture_output=True, text=True)
            if result.returncode == 0:
                (iso_path.parent / f"{iso_path.name}.md5").write_text(result.stdout)
            
            # SHA256
            result = subprocess.run(['sha256sum', str(iso_path)], capture_output=True, text=True)
            if result.returncode == 0:
                (iso_path.parent / f"{iso_path.name}.sha256").write_text(result.stdout)
                
        except Exception as e:
            print(f"Checksum generation error: {e}")
    
    def _create_vm_image(self, iso_path: Path):
        """Create VM disk image from ISO"""
        try:
            vm_path = iso_path.parent / f"{iso_path.stem}.qcow2"
            
            # Create qcow2 image
            subprocess.run([
                'qemu-img', 'create', '-f', 'qcow2', str(vm_path), '8G'
            ], check=True)
            
            print(f"VM image created: {vm_path}")
            
        except Exception as e:
            print(f"VM image creation error: {e}")