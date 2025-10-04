#!/bin/bash
# LFS Kernel Build Script
# Compiles and installs Linux kernel

set -e

echo "=== LFS Kernel Build ==="

cd /sources

# Extract kernel source
echo "Extracting Linux kernel..."
tar -xf linux-6.16.1.tar.xz
cd linux-6.16.1

# Clean kernel source
make mrproper

# Create basic kernel configuration
echo "Creating kernel configuration..."
make defconfig

# Enable essential features for LFS
cat >> .config << "EOF"
CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y
CONFIG_EXT4_FS=y
CONFIG_PROC_FS=y
CONFIG_SYSFS=y
CONFIG_TMPFS=y
CONFIG_UNIX=y
CONFIG_INET=y
CONFIG_NET=y
CONFIG_PACKET=y
CONFIG_NETDEVICES=y
CONFIG_ETHERNET=y
CONFIG_E1000=y
CONFIG_E1000E=y
CONFIG_VIRTIO_NET=y
CONFIG_INPUT=y
CONFIG_INPUT_KEYBOARD=y
CONFIG_KEYBOARD_ATKBD=y
CONFIG_VT=y
CONFIG_VT_CONSOLE=y
CONFIG_HW_CONSOLE=y
CONFIG_SERIAL_8250=y
CONFIG_SERIAL_8250_CONSOLE=y
CONFIG_PRINTK=y
CONFIG_BUG=y
CONFIG_ELF_CORE=y
CONFIG_BASE_FULL=y
CONFIG_FUTEX=y
CONFIG_EPOLL=y
CONFIG_SIGNALFD=y
CONFIG_TIMERFD=y
CONFIG_EVENTFD=y
CONFIG_SHMEM=y
CONFIG_AIO=y
CONFIG_ADVISE_SYSCALLS=y
CONFIG_MEMBARRIER=y
CONFIG_KALLSYMS=y
CONFIG_BPF_SYSCALL=y
CONFIG_USERFAULTFD=y
CONFIG_RSEQ=y
EOF

# Update configuration
make olddefconfig

echo "Building kernel..."
make -j$(nproc)

echo "Installing kernel modules..."
make modules_install

# Install kernel
echo "Installing kernel..."
cp -iv arch/x86/boot/bzImage /boot/vmlinuz-6.16.1-lfs-12.4
cp -iv System.map /boot/System.map-6.16.1
cp -iv .config /boot/config-6.16.1

# Create symlinks
ln -sfv vmlinuz-6.16.1-lfs-12.4 /boot/vmlinuz
ln -sfv System.map-6.16.1 /boot/System.map

# Install kernel headers for userspace
echo "Installing kernel headers..."
make headers_install INSTALL_HDR_PATH=/usr

# Create initramfs (basic)
echo "Creating initramfs..."
mkdir -p /boot/initramfs
cd /boot/initramfs

# Create basic initramfs structure
mkdir -p {bin,sbin,etc,proc,sys,dev,lib,lib64,usr/{bin,sbin}}

# Copy essential binaries
cp /bin/sh bin/
cp /bin/mount bin/
cp /bin/umount bin/
cp /sbin/switch_root sbin/

# Copy essential libraries
ldd /bin/sh | grep -o '/lib[^ ]*' | xargs -I {} cp {} lib/
ldd /bin/mount | grep -o '/lib[^ ]*' | xargs -I {} cp {} lib/

# Create init script
cat > init << "EOF"
#!/bin/sh

# Mount essential filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev

# Switch to real root
exec switch_root /mnt/root /sbin/init
EOF

chmod +x init

# Create initramfs archive
find . | cpio -o -H newc | gzip > /boot/initramfs-6.16.1-lfs-12.4.img
ln -sfv initramfs-6.16.1-lfs-12.4.img /boot/initramfs.img

cd /sources
rm -rf linux-6.16.1

echo "✓ Kernel build completed"
echo "Kernel: /boot/vmlinuz-6.16.1-lfs-12.4"
echo "Modules: /lib/modules/6.16.1"
echo "Initramfs: /boot/initramfs-6.16.1-lfs-12.4.img"