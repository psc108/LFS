#!/bin/bash
# LFS Partition Setup Script
# Creates LFS partition and mount points

set -e

echo "=== LFS Partition Setup ==="

export LFS=/mnt/lfs

# Check if LFS directory exists
if [ ! -d "$LFS" ]; then
    echo "Creating LFS directory: $LFS"
    sudo mkdir -pv $LFS
else
    echo "LFS directory already exists: $LFS"
fi

# Check if already mounted
if mountpoint -q $LFS; then
    echo "LFS partition already mounted at $LFS"
else
    echo "LFS partition not mounted"
    echo "Please manually create and mount your LFS partition"
    echo "Example commands:"
    echo "  sudo mkfs.ext4 /dev/sdXY"
    echo "  sudo mount /dev/sdXY $LFS"
    echo ""
    echo "For this demo, creating a bind mount to simulate partition"
    sudo mkdir -p /tmp/lfs_build
    sudo mount --bind /tmp/lfs_build $LFS
fi

# Create directory structure
echo "Creating LFS directory structure..."
sudo mkdir -pv $LFS/{etc,var,usr,tools,lib,lib64,bin,sbin}
sudo mkdir -pv $LFS/usr/{bin,lib,sbin}

# Create sources directory
sudo mkdir -pv $LFS/sources
sudo chmod -v a+wt $LFS/sources

# Create tools directory
sudo mkdir -pv $LFS/tools
sudo ln -sfv $LFS/tools /

# Set ownership
sudo chown -v lfs $LFS/{usr{,/*},lib,var,etc,bin,sbin,tools}
sudo chown -v lfs $LFS/sources

echo "✓ LFS partition setup completed"
echo "LFS root: $LFS"
echo "Sources: $LFS/sources"
echo "Tools: $LFS/tools"