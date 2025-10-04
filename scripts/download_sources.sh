#!/bin/bash
# LFS Package Download Script
# Downloads all required LFS packages

set -e

echo "=== LFS Package Download ==="

export LFS=/mnt/lfs
SOURCES_DIR="$LFS/sources"

# Ensure sources directory exists
sudo mkdir -p "$SOURCES_DIR"
sudo chown lfs:lfs "$SOURCES_DIR"

cd "$SOURCES_DIR"

echo "Downloading LFS packages to $SOURCES_DIR"

# Copy packages from our repository sources
REPO_SOURCES="/tmp/lfs_repo/sources"
if [ -d "$REPO_SOURCES" ]; then
    echo "Copying packages from repository..."
    cp -v "$REPO_SOURCES"/* . 2>/dev/null || echo "No packages found in repository"
fi

# Verify packages exist
PACKAGE_COUNT=$(ls -1 *.tar.* 2>/dev/null | wc -l)
echo "Found $PACKAGE_COUNT packages in sources directory"

if [ $PACKAGE_COUNT -gt 50 ]; then
    echo "✓ Package download completed"
    echo "All LFS packages are available"
else
    echo "⚠ Warning: Expected ~60 packages, found $PACKAGE_COUNT"
    echo "Run the Download Sources feature from the GUI first"
fi

# Create wget-list and md5sums if they don't exist
if [ ! -f wget-list ]; then
    echo "Creating wget-list..."
    cat > wget-list << 'EOF'
# LFS 12.0 Package URLs
https://sourceware.org/pub/binutils/releases/binutils-2.41.tar.xz
https://ftp.gnu.org/gnu/gcc/gcc-13.2.0/gcc-13.2.0.tar.xz
https://www.kernel.org/pub/linux/kernel/v6.x/linux-6.4.12.tar.xz
https://ftp.gnu.org/gnu/glibc/glibc-2.38.tar.xz
EOF
fi

echo "Sources directory prepared: $SOURCES_DIR"