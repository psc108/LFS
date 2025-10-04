#!/bin/bash
# LFS Toolchain Build Script
# Builds cross-compilation tools (binutils, gcc, glibc)

set -e

echo "=== LFS Toolchain Build ==="

export LFS=/mnt/lfs
export LFS_TGT=$(uname -m)-lfs-linux-gnu
export PATH="$LFS/tools/bin:$PATH"
export CONFIG_SITE="$LFS/usr/share/config.site"

cd $LFS/sources

echo "Building toolchain for target: $LFS_TGT"
echo "Tools directory: $LFS/tools"

# Build Binutils Pass 1
echo "Building Binutils Pass 1..."
tar -xf binutils-2.41.tar.xz
cd binutils-2.41

mkdir -v build
cd build

../configure --prefix=$LFS/tools \
             --with-sysroot=$LFS \
             --target=$LFS_TGT   \
             --disable-nls       \
             --enable-gprofng=no \
             --disable-werror

make -j$(nproc)
make install

cd $LFS/sources
rm -rf binutils-2.41

# Build GCC Pass 1
echo "Building GCC Pass 1..."
tar -xf gcc-13.2.0.tar.xz
cd gcc-13.2.0

tar -xf ../mpfr-4.2.0.tar.xz
mv -v mpfr-4.2.0 mpfr
tar -xf ../gmp-6.3.0.tar.xz
mv -v gmp-6.3.0 gmp
tar -xf ../mpc-1.3.1.tar.gz
mv -v mpc-1.3.1 mpc

case $(uname -m) in
  x86_64)
    sed -e '/m64=/s/lib64/lib/' \
        -i.orig gcc/config/i386/t-linux64
 ;;
esac

mkdir -v build
cd build

../configure                  \
    --target=$LFS_TGT         \
    --prefix=$LFS/tools       \
    --with-glibc-version=2.38 \
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

make -j$(nproc)
make install

cd ..
cat gcc/limitx.h gcc/glimits.h gcc/limity.h > \
  `dirname $($LFS_TGT-gcc -print-libgcc-file-name)`/include/limits.h

cd $LFS/sources
rm -rf gcc-13.2.0

# Install Linux API Headers
echo "Installing Linux API Headers..."
tar -xf linux-6.4.12.tar.xz
cd linux-6.4.12

make mrproper
make headers
find usr/include -type f ! -name '*.h' -delete
cp -rv usr/include $LFS/usr

cd $LFS/sources
rm -rf linux-6.4.12

# Build Glibc
echo "Building Glibc..."
tar -xf glibc-2.38.tar.xz
cd glibc-2.38

case $(uname -m) in
    i?86)   ln -sfv ld-linux.so.2 $LFS/lib/ld-lsb.so.3
    ;;
    x86_64) ln -sfv ../lib/ld-linux-x86-64.so.2 $LFS/lib64
            ln -sfv ../lib/ld-linux-x86-64.so.2 $LFS/lib64/ld-lsb-x86-64.so.3
    ;;
esac

patch -Np1 -i ../glibc-2.38-fhs-1.patch || echo "Patch not found, continuing..."

mkdir -v build
cd build

echo "rootsbindir=/usr/sbin" > configparms

../configure                             \
      --prefix=/usr                      \
      --host=$LFS_TGT                    \
      --build=$(../scripts/config.guess) \
      --enable-kernel=4.14               \
      --with-headers=$LFS/usr/include    \
      --disable-nscd                     \
      libc_cv_slibdir=/usr/lib

make -j$(nproc)
make DESTDIR=$LFS install

sed '/RTLDLIST=/s@/usr@@g' -i $LFS/usr/bin/ldd

cd $LFS/sources
rm -rf glibc-2.38

echo "✓ Toolchain build completed"
echo "Cross-compilation tools are ready"