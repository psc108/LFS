import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class ContainerManager:
    def __init__(self, container_runtime: str = "auto"):
        self.runtime = self._detect_runtime(container_runtime)
        self.containers = {}
        self.images = {}
    
    def _detect_runtime(self, preferred: str) -> str:
        """Detect available container runtime"""
        if preferred != "auto":
            return preferred
        
        # Check for Docker
        if shutil.which("docker"):
            try:
                subprocess.run(["docker", "--version"], check=True, capture_output=True)
                return "docker"
            except subprocess.CalledProcessError:
                pass
        
        # Check for Podman
        if shutil.which("podman"):
            try:
                subprocess.run(["podman", "--version"], check=True, capture_output=True)
                return "podman"
            except subprocess.CalledProcessError:
                pass
        
        raise Exception("No container runtime found (Docker or Podman required)")
    
    def build_lfs_image(self, image_config: Dict) -> str:
        """Build LFS container image"""
        try:
            image_name = image_config.get('name', 'lfs-build')
            image_tag = image_config.get('tag', 'latest')
            full_image_name = f"{image_name}:{image_tag}"
            
            # Create Dockerfile
            dockerfile_content = self._generate_lfs_dockerfile(image_config)
            
            dockerfile_path = Path("Dockerfile.lfs")
            dockerfile_path.write_text(dockerfile_content)
            
            # Build image
            build_cmd = [
                self.runtime, "build",
                "-t", full_image_name,
                "-f", str(dockerfile_path),
                "."
            ]
            
            result = subprocess.run(build_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.images[full_image_name] = {
                    'name': image_name,
                    'tag': image_tag,
                    'created': datetime.now().isoformat(),
                    'config': image_config
                }
                return full_image_name
            else:
                raise Exception(f"Image build failed: {result.stderr}")
                
        except Exception as e:
            raise Exception(f"Failed to build LFS image: {e}")
        finally:
            # Cleanup
            if dockerfile_path.exists():
                dockerfile_path.unlink()
    
    def _generate_lfs_dockerfile(self, config: Dict) -> str:
        """Generate Dockerfile for LFS build"""
        base_image = config.get('base_image', 'fedora:39')
        lfs_version = config.get('lfs_version', '12.4')
        
        dockerfile = f"""
FROM {base_image}

# Install LFS build dependencies
RUN dnf update -y && \\
    dnf groupinstall -y "Development Tools" && \\
    dnf install -y \\
        bash binutils bison coreutils diffutils findutils gawk gcc \\
        glibc-devel grep gzip m4 make patch perl python3 sed tar \\
        texinfo xz git wget curl rsync sudo && \\
    dnf clean all

# Create LFS user and directory
RUN useradd -m -s /bin/bash lfs && \\
    mkdir -p /mnt/lfs && \\
    chown lfs:lfs /mnt/lfs && \\
    chmod 755 /mnt/lfs

# Set LFS environment
ENV LFS=/mnt/lfs
ENV LC_ALL=POSIX
ENV LFS_TGT=x86_64-lfs-linux-gnu
ENV PATH=/usr/bin:/bin:/mnt/lfs/tools/bin

# Copy LFS build system
COPY . /opt/lfs-build-system/
RUN chown -R lfs:lfs /opt/lfs-build-system

# Switch to LFS user
USER lfs
WORKDIR /opt/lfs-build-system

# Set up build environment
RUN echo 'export LFS=/mnt/lfs' >> ~/.bashrc && \\
    echo 'export LC_ALL=POSIX' >> ~/.bashrc && \\
    echo 'export LFS_TGT=x86_64-lfs-linux-gnu' >> ~/.bashrc && \\
    echo 'export PATH=/usr/bin:/bin:/mnt/lfs/tools/bin' >> ~/.bashrc

VOLUME ["/mnt/lfs"]
EXPOSE 5000

CMD ["python3", "main.py", "--container-mode"]
"""
        
        return dockerfile
    
    def run_lfs_container(self, container_config: Dict) -> str:
        """Run LFS build in container"""
        try:
            image_name = container_config.get('image', 'lfs-build:latest')
            container_name = container_config.get('name', f"lfs-build-{datetime.now().strftime('%Y%m%d%H%M%S')}")
            
            # Prepare run command
            run_cmd = [
                self.runtime, "run",
                "-d",  # Detached mode
                "--name", container_name,
                "--privileged",  # Required for LFS build
                "-v", "/mnt/lfs:/mnt/lfs",  # Mount LFS directory
                "-p", "5000:5000",  # Expose API port
            ]
            
            # Add environment variables
            for key, value in container_config.get('environment', {}).items():
                run_cmd.extend(["-e", f"{key}={value}"])
            
            # Add volumes
            for volume in container_config.get('volumes', []):
                run_cmd.extend(["-v", volume])
            
            run_cmd.append(image_name)
            
            # Add command if specified
            if 'command' in container_config:
                run_cmd.extend(container_config['command'].split())
            
            result = subprocess.run(run_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                container_id = result.stdout.strip()
                
                self.containers[container_name] = {
                    'id': container_id,
                    'name': container_name,
                    'image': image_name,
                    'created': datetime.now().isoformat(),
                    'config': container_config,
                    'status': 'running'
                }
                
                return container_id
            else:
                raise Exception(f"Container start failed: {result.stderr}")
                
        except Exception as e:
            raise Exception(f"Failed to run LFS container: {e}")
    
    def stop_container(self, container_name: str):
        """Stop a running container"""
        try:
            subprocess.run([self.runtime, "stop", container_name], check=True, capture_output=True)
            
            if container_name in self.containers:
                self.containers[container_name]['status'] = 'stopped'
                
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to stop container {container_name}: {e}")
    
    def remove_container(self, container_name: str):
        """Remove a container"""
        try:
            subprocess.run([self.runtime, "rm", container_name], check=True, capture_output=True)
            
            if container_name in self.containers:
                del self.containers[container_name]
                
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to remove container {container_name}: {e}")
    
    def get_container_logs(self, container_name: str, lines: int = 100) -> str:
        """Get container logs"""
        try:
            result = subprocess.run([
                self.runtime, "logs", "--tail", str(lines), container_name
            ], capture_output=True, text=True, check=True)
            
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to get logs for {container_name}: {e}")
    
    def list_containers(self) -> List[Dict]:
        """List all containers"""
        try:
            result = subprocess.run([
                self.runtime, "ps", "-a", "--format", "json"
            ], capture_output=True, text=True, check=True)
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    container_info = json.loads(line)
                    containers.append({
                        'id': container_info.get('ID', ''),
                        'name': container_info.get('Names', ''),
                        'image': container_info.get('Image', ''),
                        'status': container_info.get('Status', ''),
                        'created': container_info.get('CreatedAt', '')
                    })
            
            return containers
            
        except subprocess.CalledProcessError as e:
            return []
    
    def list_images(self) -> List[Dict]:
        """List all images"""
        try:
            result = subprocess.run([
                self.runtime, "images", "--format", "json"
            ], capture_output=True, text=True, check=True)
            
            images = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    image_info = json.loads(line)
                    images.append({
                        'id': image_info.get('ID', ''),
                        'repository': image_info.get('Repository', ''),
                        'tag': image_info.get('Tag', ''),
                        'created': image_info.get('CreatedAt', ''),
                        'size': image_info.get('Size', '')
                    })
            
            return images
            
        except subprocess.CalledProcessError as e:
            return []
    
    def create_build_cluster(self, cluster_config: Dict) -> Dict:
        """Create a cluster of LFS build containers"""
        try:
            cluster_name = cluster_config.get('name', 'lfs-cluster')
            node_count = cluster_config.get('nodes', 3)
            
            cluster_info = {
                'name': cluster_name,
                'nodes': [],
                'created': datetime.now().isoformat()
            }
            
            for i in range(node_count):
                node_config = cluster_config.copy()
                node_config['name'] = f"{cluster_name}-node-{i+1}"
                
                container_id = self.run_lfs_container(node_config)
                
                cluster_info['nodes'].append({
                    'name': node_config['name'],
                    'container_id': container_id,
                    'role': 'worker' if i > 0 else 'master'
                })
            
            return cluster_info
            
        except Exception as e:
            raise Exception(f"Failed to create build cluster: {e}")
    
    def start_container_build(self, container_config: dict) -> str:
        """Start containerized build and return container ID"""
        try:
            # Build image if needed
            if container_config.get('build_image', False):
                image_name = self.build_lfs_image(container_config.get('image_config', {}))
                container_config['image'] = image_name
            
            # Run container
            container_id = self.run_lfs_container(container_config)
            
            return container_id
            
        except Exception as e:
            raise Exception(f"Failed to start container build: {str(e)}")