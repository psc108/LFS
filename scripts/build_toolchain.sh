#!/bin/bash
set -e

echo "=== LFS Cross-Compilation Toolchain Build ==="

export LFS=/mnt/lfs
export LFS_TGT=$(uname -m)-lfs-linux-gnu
export PATH="$LFS/tools/bin:$PATH"

# Ensure directories exist
mkdir -p $LFS/tools
mkdir -p $LFS/sources

cd $LFS/sources

echo "Building toolchain for target: $LFS_TGT"

# Ensure packages are available - copy from repository if needed
echo "Ensuring source packages are available..."
if [ ! -f binutils-2.45.tar.xz ]; then
    echo "binutils-2.45.tar.xz not found, copying from repository..."
    REPO_SOURCES="/home/scottp/lfs_repositories/sources"
    if [ -f "$REPO_SOURCES/binutils-2.45.tar.xz" ]; then
        cp "$REPO_SOURCES/binutils-2.45.tar.xz" . || {
            echo "ERROR: Could not copy binutils from repository"
            exit 1
        }
        echo "✓ Copied binutils-2.45.tar.xz from repository"
    else
        echo "ERROR: binutils-2.45.tar.xz not found in repository: $REPO_SOURCES"
        exit 1
    fi
fi

echo "Building Binutils..."
# Clean up any previous build attempts
rm -rf binutils-2.45
tar -xf binutils-2.45.tar.xz
cd binutils-2.45

# Use original configure script (no autoreconf needed for LFS)

# Clean and create build directory
rm -rf build
mkdir -v build
cd build

../configure --prefix=$LFS/tools \
             --with-sysroot=$LFS \
             --target=$LFS_TGT \
             --disable-nls \
             --enable-gprofng=no \
             --disable-werror \
             --enable-default-hash-style=gnu

make -j$(nproc)
make install

echo "Binutils build completed successfully"
cd $LFS/sources
rm -rf binutils-2.45

echo "Toolchain build stage completed"