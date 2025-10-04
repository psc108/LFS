#!/bin/bash
# LFS Final System Build Script
# Builds final versions of all packages (run inside chroot)

set -e

echo "=== LFS Final System Build ==="

# Verify we're in chroot
if [ ! -f /tools/bin/bash ]; then
    echo "Error: This script must be run inside the chroot environment"
    exit 1
fi

cd /sources

# Build Man-pages
echo "Building Man-pages..."
tar -xf man-pages-6.05.01.tar.xz
cd man-pages-6.05.01
make prefix=/usr install
cd /sources
rm -rf man-pages-6.05.01

# Build Iana-Etc
echo "Building Iana-Etc..."
tar -xf iana-etc-20230810.tar.gz
cd iana-etc-20230810
cp services protocols /etc
cd /sources
rm -rf iana-etc-20230810

# Build Glibc (final)
echo "Building Glibc (final)..."
tar -xf glibc-2.38.tar.xz
cd glibc-2.38

patch -Np1 -i ../glibc-2.38-fhs-1.patch || echo "Patch not found, continuing..."

mkdir -v build
cd build

echo "rootsbindir=/usr/sbin" > configparms

../configure --prefix=/usr                            \
             --disable-werror                         \
             --enable-kernel=4.14                     \
             --enable-stack-protector=strong          \
             --with-headers=/usr/include              \
             --disable-nscd                           \
             libc_cv_slibdir=/usr/lib

make -j$(nproc)
make install

sed '/RTLDLIST=/s@/usr@@g' -i /usr/bin/ldd

# Install locales
make localedata/install-locales

# Configure Glibc
cat > /etc/nsswitch.conf << "EOF"
passwd: files
group: files
shadow: files

hosts: files dns
networks: files

protocols: files
services: files
ethers: files
rpc: files
EOF

# Add time zone data
tar -xf ../../tzdata2023c.tar.gz || echo "tzdata not found, skipping..."

cd /sources
rm -rf glibc-2.38

# Build Zlib
echo "Building Zlib..."
tar -xf zlib-1.2.13.tar.xz
cd zlib-1.2.13

./configure --prefix=/usr
make -j$(nproc)
make install
rm -fv /usr/lib/libz.a

cd /sources
rm -rf zlib-1.2.13

# Build Bzip2
echo "Building Bzip2..."
tar -xf bzip2-1.0.8.tar.gz
cd bzip2-1.0.8

patch -Np1 -i ../bzip2-1.0.8-install_docs-1.patch || echo "Patch not found, continuing..."

sed -i 's@\(ln -s -f \)$(PREFIX)/bin/@\1@' Makefile
sed -i "s@(PREFIX)/man@(PREFIX)/share/man@g" Makefile

make -f Makefile-libbz2_so
make clean
make -j$(nproc)
make PREFIX=/usr install

cp -av libbz2.so.* /usr/lib
ln -sv libbz2.so.1.0.8 /usr/lib/libbz2.so

cd /sources
rm -rf bzip2-1.0.8

# Build Xz
echo "Building Xz..."
tar -xf xz-5.4.4.tar.xz
cd xz-5.4.4

./configure --prefix=/usr    \
            --disable-static \
            --docdir=/usr/share/doc/xz-5.4.4

make -j$(nproc)
make install

cd /sources
rm -rf xz-5.4.4

# Build File (final)
echo "Building File (final)..."
tar -xf file-5.45.tar.gz
cd file-5.45

./configure --prefix=/usr
make -j$(nproc)
make install

cd /sources
rm -rf file-5.45

# Build Readline
echo "Building Readline..."
tar -xf readline-8.2.tar.gz
cd readline-8.2

sed -i '/MV.*old/d' Makefile.in
sed -i '/{OLDSUFF}/c:' support/shlib-install

./configure --prefix=/usr    \
            --disable-static \
            --with-curses    \
            --docdir=/usr/share/doc/readline-8.2

make SHLIB_LIBS="-lncursesw" -j$(nproc)
make SHLIB_LIBS="-lncursesw" install

cd /sources
rm -rf readline-8.2

echo "✓ Final system build completed"
echo "Core system packages are installed"