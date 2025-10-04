#!/bin/bash
# LFS Temporary System Build Script
# Builds temporary versions of core utilities

set -e

echo "=== LFS Temporary System Build ==="

export LFS=/mnt/lfs
export LFS_TGT=$(uname -m)-lfs-linux-gnu
export PATH="$LFS/tools/bin:$PATH"
export CONFIG_SITE="$LFS/usr/share/config.site"

cd $LFS/sources

# Build Libstdc++ from GCC
echo "Building Libstdc++..."
tar -xf gcc-15.2.0.tar.xz
cd gcc-15.2.0

mkdir -v build
cd build

../libstdc++-v3/configure           \
    --host=$LFS_TGT                 \
    --build=$(../config.guess)      \
    --prefix=/usr                   \
    --disable-multilib              \
    --disable-nls                   \
    --disable-libstdcxx-pch         \
    --with-gxx-include-dir=/tools/$LFS_TGT/include/c++/15.2.0

make -j$(nproc)
make DESTDIR=$LFS install
rm -v $LFS/usr/lib/lib{stdc++,stdc++fs,supc++}.la

cd $LFS/sources
rm -rf gcc-15.2.0

# Build M4
echo "Building M4..."
tar -xf m4-1.4.20.tar.xz
cd m4-1.4.20

./configure --prefix=/usr   \
            --host=$LFS_TGT \
            --build=$(build-aux/config.guess)

make -j$(nproc)
make DESTDIR=$LFS install

cd $LFS/sources
rm -rf m4-1.4.20

# Build Ncurses
echo "Building Ncurses..."
tar -xf ncurses-6.5-20250809.tgz
cd ncurses-6.5-20250809

sed -i s/mawk// configure

mkdir build
pushd build
  ../configure
  make -C include
  make -C progs tic
popd

./configure --prefix=/usr                \
            --host=$LFS_TGT              \
            --build=$(./config.guess)    \
            --mandir=/usr/share/man      \
            --with-manpage-format=normal \
            --with-shared                \
            --without-normal             \
            --with-cxx-shared            \
            --without-debug              \
            --without-ada                \
            --disable-stripping          \
            --enable-widec

make -j$(nproc)
make DESTDIR=$LFS TIC_PATH=$(pwd)/build/progs/tic install
echo "INPUT(-lncursesw)" > $LFS/usr/lib/libncurses.so

cd $LFS/sources
rm -rf ncurses-6.5-20250809

# Build Bash
echo "Building Bash..."
tar -xf bash-5.3.tar.gz
cd bash-5.3

./configure --prefix=/usr                      \
            --build=$(sh support/config.guess) \
            --host=$LFS_TGT                     \
            --without-bash-malloc

make -j$(nproc)
make DESTDIR=$LFS install
ln -sv bash $LFS/bin/sh

cd $LFS/sources
rm -rf bash-5.3

# Build Coreutils
echo "Building Coreutils..."
tar -xf coreutils-9.7.tar.xz
cd coreutils-9.7

./configure --prefix=/usr                     \
            --host=$LFS_TGT                   \
            --build=$(build-aux/config.guess) \
            --enable-install-program=hostname \
            --enable-no-install-program=kill,uptime

make -j$(nproc)
make DESTDIR=$LFS install

mv -v $LFS/usr/bin/chroot              $LFS/usr/sbin
mkdir -pv $LFS/usr/share/man/man8
mv -v $LFS/usr/share/man/man1/chroot.1 $LFS/usr/share/man/man8/chroot.8
sed -i 's/"1"/"8"/'                    $LFS/usr/share/man/man8/chroot.8

cd $LFS/sources
rm -rf coreutils-9.7

# Build Diffutils
echo "Building Diffutils..."
tar -xf diffutils-3.12.tar.xz
cd diffutils-3.12

./configure --prefix=/usr   \
            --host=$LFS_TGT \
            --build=$(./build-aux/config.guess)

make -j$(nproc)
make DESTDIR=$LFS install

cd $LFS/sources
rm -rf diffutils-3.12

# Build File
echo "Building File..."
tar -xf file-5.46.tar.gz
cd file-5.46

mkdir build
pushd build
  ../configure --disable-bzlib      \
               --disable-libseccomp \
               --disable-xzlib      \
               --disable-zlib
  make
popd

./configure --prefix=/usr --host=$LFS_TGT --build=$(./config.guess)

make FILE_COMPILE=$(pwd)/build/src/file -j$(nproc)
make DESTDIR=$LFS install
rm -v $LFS/usr/lib/libmagic.la

cd $LFS/sources
rm -rf file-5.46

echo "✓ Temporary system build completed"
echo "Core utilities are ready for chroot environment"