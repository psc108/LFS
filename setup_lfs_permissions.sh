#!/bin/bash
# LFS Directory Permissions Setup Script

echo "Setting up LFS directory permissions..."

# Create and setup all LFS directories
sudo mkdir -p /mnt/lfs/sources
sudo mkdir -p /mnt/lfs/tools
sudo mkdir -p /mnt/lfs/usr
sudo mkdir -p /mnt/lfs/lib
sudo mkdir -p /mnt/lfs/lib64

# Make directories writable for build operations
sudo chmod 777 /mnt/lfs/sources
sudo chmod 777 /mnt/lfs/tools
sudo chmod 777 /mnt/lfs/usr
sudo chmod 755 /mnt/lfs/lib
sudo chmod 755 /mnt/lfs/lib64

# Fix permissions on existing source files to make them readable
if [ -d "/mnt/lfs/sources" ]; then
    echo "Fixing permissions on existing source files..."
    sudo find /mnt/lfs/sources -type f \( -name "*.tar.*" -o -name "*.tgz" \) -exec chmod 644 {} \; 2>/dev/null || true
fi

echo "✓ LFS directories created and configured"
echo "✓ Source file permissions fixed"
echo "You can now run builds successfully"