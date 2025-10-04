#!/bin/bash
# LFS Toolchain Build Script
# Builds cross-compilation tools (binutils, gcc, glibc)

set -e

echo "=== LFS Toolchain Build ==="

export LFS=/mnt/lfs
export LFS_TGT=$(uname -m)-lfs-linux-gnu
export PATH="$LFS/tools/bin:$PATH"
export CONFIG_SITE="$LFS/usr/share/config.site"

# Create tools directory (permissions should already be set by LFS setup)
mkdir -p $LFS/tools 2>/dev/null || echo "Tools directory exists"
mkdir -p $LFS/usr 2>/dev/null || echo "Usr directory exists"

cd $LFS/sources

echo "Building toolchain for target: $LFS_TGT"
echo "Tools directory: $LFS/tools"

# Clean up any previous build attempts
echo "Cleaning up previous build attempts..."
rm -rf binutils-2.45 gcc-15.2.0 linux-6.16.1 glibc-2.42 2>/dev/null || true
echo "✓ Cleanup completed"

# Build Binutils Pass 1
echo "Building Binutils Pass 1..."
echo "Extracting binutils-2.45.tar.xz..."
tar -xf binutils-2.45.tar.xz
echo "✓ Binutils extracted successfully"
cd binutils-2.45

echo "Creating build directory..."
rm -rf build 2>/dev/null || true
mkdir -v build
cd build

echo "Configuring binutils..."
../configure --prefix=$LFS/tools \
             --with-sysroot=$LFS \
             --target=$LFS_TGT   \
             --disable-nls       \
             --enable-gprofng=no \
             --disable-werror
echo "✓ Binutils configuration completed"

echo "Building binutils (this may take several minutes)..."
make -j$(nproc)
echo "✓ Binutils build completed"

echo "Installing binutils..."
make install
echo "✓ Binutils installation completed"

cd $LFS/sources
rm -rf binutils-2.45

# Build GCC Pass 1
echo "Building GCC Pass 1..."
echo "Extracting GCC and dependencies..."
tar -xf gcc-15.2.0.tar.xz
cd gcc-15.2.0

echo "Extracting MPFR..."
tar -xf ../mpfr-4.2.2.tar.xz
mv -v mpfr-4.2.2 mpfr
echo "Extracting GMP..."
tar -xf ../gmp-6.3.0.tar.xz
mv -v gmp-6.3.0 gmp
echo "Extracting MPC..."
tar -xf ../mpc-1.3.1.tar.gz
mv -v mpc-1.3.1 mpc
echo "✓ All GCC dependencies extracted"

case $(uname -m) in
  x86_64)
    sed -e '/m64=/s/lib64/lib/' \
        -i.orig gcc/config/i386/t-linux64
 ;;
esac

echo "Creating GCC build directory..."
rm -rf build 2>/dev/null || true
mkdir -v build
cd build

echo "Configuring GCC (this may take a few minutes)..."
../configure                  \
    --target=$LFS_TGT         \
    --prefix=$LFS/tools       \
    --with-glibc-version=2.42 \
    --with-sysroot=$LFS       \
    --with-newlib             \
    --without-headers         \
    --enable-default-pie      \
    --enable-default-ssp      \
    --disable-nls             \
    --disable-shared          \
    --disable-multilib        \
    --disable-threads         \
    --disable-libatomic       \
    --disable-libgomp         \
    --disable-libquadmath     \
    --disable-libssp          \
    --disable-libvtv          \
    --disable-libstdcxx       \
    --enable-languages=c,c++
echo "✓ GCC configuration completed"

echo "Building GCC Pass 1 (this will take 10-30 minutes depending on system)..."
echo "Progress indicators will appear periodically..."
make -j$(nproc)
echo "✓ GCC Pass 1 build completed"

echo "Installing GCC Pass 1..."
make install
echo "✓ GCC Pass 1 installation completed"

cd ..
cat gcc/limitx.h gcc/glimits.h gcc/limity.h > \
  `dirname $($LFS_TGT-gcc -print-libgcc-file-name)`/include/limits.h

cd $LFS/sources
rm -rf gcc-15.2.0

# Install Linux API Headers
echo "Installing Linux API Headers..."
echo "Extracting Linux kernel sources..."
tar -xf linux-6.16.1.tar.xz
cd linux-6.16.1

echo "Cleaning kernel source tree..."
make mrproper
echo "Generating kernel headers..."
make headers
echo "Cleaning non-header files..."
find usr/include -type f ! -name '*.h' -delete
echo "Installing headers to $LFS/usr..."
cp -rv usr/include $LFS/usr
echo "✓ Linux API Headers installation completed"

cd $LFS/sources
rm -rf linux-6.16.1

# Build Glibc
echo "Building Glibc..."
echo "Extracting Glibc sources..."
tar -xf glibc-2.42.tar.xz
cd glibc-2.42
echo "✓ Glibc extracted successfully"

case $(uname -m) in
    i?86)   ln -sfv ld-linux.so.2 $LFS/lib/ld-lsb.so.3
    ;;
    x86_64) ln -sfv ../lib/ld-linux-x86-64.so.2 $LFS/lib64
            ln -sfv ../lib/ld-linux-x86-64.so.2 $LFS/lib64/ld-lsb-x86-64.so.3
    ;;
esac

patch -Np1 -i ../glibc-2.42-fhs-1.patch || echo "Patch not found, continuing..."

echo "Creating Glibc build directory..."
rm -rf build 2>/dev/null || true
mkdir -v build
cd build

echo "Setting up Glibc configuration parameters..."
echo "rootsbindir=/usr/sbin" > configparms

echo "Configuring Glibc..."
../configure                             \
      --prefix=/usr                      \
      --host=$LFS_TGT                    \
      --build=$(../scripts/config.guess) \
      --enable-kernel=4.14               \
      --with-headers=$LFS/usr/include    \
      --disable-nscd                     \
      libc_cv_slibdir=/usr/lib
echo "✓ Glibc configuration completed"

echo "Building Glibc (this will take 10-20 minutes)..."
make -j$(nproc)
echo "✓ Glibc build completed"

echo "Installing Glibc..."
make DESTDIR=$LFS install
echo "✓ Glibc installation completed"

sed '/RTLDLIST=/s@/usr@@g' -i $LFS/usr/bin/ldd

cd $LFS/sources
rm -rf glibc-2.42

echo "✓ Toolchain build completed"
echo "Cross-compilation tools are ready"