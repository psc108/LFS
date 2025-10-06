#!/bin/bash
# Copy LFS packages from repository to build directory

set -e

echo "=== Copying LFS Packages from Repository ==="

export LFS=/mnt/lfs
SOURCES_DIR="$LFS/sources"
REPO_SOURCES="/home/scottp/lfs_repositories/sources"

# Ensure directories exist
echo "Setting up LFS directories..."
sudo mkdir -p "$LFS/sources" "$LFS/tools" "$LFS/usr" 2>/dev/null || true
sudo chown -R $(whoami):$(whoami) "$LFS" 2>/dev/null || true
sudo chmod -R 755 "$LFS" 2>/dev/null || true

# Ensure sources directory is writable
mkdir -p "$SOURCES_DIR"
cd "$SOURCES_DIR"

echo "Copying packages from repository: $REPO_SOURCES"
echo "To build directory: $SOURCES_DIR"

if [ ! -d "$REPO_SOURCES" ]; then
    echo "ERROR: Repository sources directory not found: $REPO_SOURCES"
    exit 1
fi

# Essential packages for toolchain build
ESSENTIAL_PACKAGES=(
    "binutils-2.45.tar.xz"
    "gcc-15.2.0.tar.xz"
    "glibc-2.42.tar.xz"
    "gmp-6.3.0.tar.xz"
    "mpfr-4.2.2.tar.xz"
    "mpc-1.3.1.tar.gz"
    "linux-6.16.1.tar.xz"
)

COPIED_COUNT=0
EXISTING_COUNT=0

for package in "${ESSENTIAL_PACKAGES[@]}"; do
    if [ -f "$package" ]; then
        echo "✓ $package already exists"
        EXISTING_COUNT=$((EXISTING_COUNT + 1))
    elif [ -f "$REPO_SOURCES/$package" ]; then
        if cp "$REPO_SOURCES/$package" . 2>/dev/null; then
            echo "✓ Copied $package"
            COPIED_COUNT=$((COPIED_COUNT + 1))
        else
            echo "❌ Failed to copy $package"
        fi
    else
        echo "⚠️ $package not found in repository"
    fi
done

echo ""
echo "Package Status:"
echo "  Existing: $EXISTING_COUNT"
echo "  Copied: $COPIED_COUNT"
echo "  Total Available: $((EXISTING_COUNT + COPIED_COUNT)) of ${#ESSENTIAL_PACKAGES[@]}"

if [ $((EXISTING_COUNT + COPIED_COUNT)) -eq ${#ESSENTIAL_PACKAGES[@]} ]; then
    echo "✅ All essential packages are available for toolchain build"
else
    echo "⚠️ Some packages are missing - build may fail"
fi

echo "✓ Package copy completed"