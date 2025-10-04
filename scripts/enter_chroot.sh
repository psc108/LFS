#!/bin/bash
# LFS Chroot Environment Setup Script
# Enters isolated build environment

set -e

echo "=== LFS Chroot Environment Setup ==="

export LFS=/mnt/lfs

# Change ownership of LFS directory
echo "Setting ownership of $LFS to root..."
sudo chown -R root:root $LFS/{usr,lib,var,etc,bin,sbin,tools}
case $(uname -m) in
    x86_64) sudo chown -R root:root $LFS/lib64 ;;
esac

# Prepare virtual kernel file systems
echo "Preparing virtual kernel file systems..."
sudo mkdir -pv $LFS/{dev,proc,sys,run}

# Create device nodes
echo "Creating essential device nodes..."
sudo mknod -m 600 $LFS/dev/console c 5 1
sudo mknod -m 666 $LFS/dev/null c 1 3

# Mount virtual file systems
echo "Mounting virtual file systems..."
sudo mount -v --bind /dev $LFS/dev
sudo mount -v --bind /dev/pts $LFS/dev/pts
sudo mount -vt proc proc $LFS/proc
sudo mount -vt sysfs sysfs $LFS/sys
sudo mount -vt tmpfs tmpfs $LFS/run

if [ -h $LFS/dev/shm ]; then
    sudo mkdir -pv $LFS/$(readlink $LFS/dev/shm)
else
    sudo mount -t tmpfs -o nosuid,nodev tmpfs $LFS/dev/shm
fi

# Create chroot script
cat > /tmp/chroot_commands.sh << 'EOF'
#!/bin/bash
# Commands to run inside chroot

export PATH=/usr/bin:/usr/sbin
export PS1='(lfs chroot) \u:\w\$ '

echo "=== Inside LFS Chroot Environment ==="
echo "Current directory: $(pwd)"
echo "Available tools:"
ls -la /usr/bin | head -10

# Test basic functionality
echo "Testing basic commands..."
echo "Date: $(date)"
echo "Hostname: $(hostname)"
echo "User: $(whoami)"

echo "✓ Chroot environment is ready"
echo "You are now in the LFS build environment"
echo "Run 'exit' to leave chroot"

# Start interactive shell
/bin/bash --login
EOF

chmod +x /tmp/chroot_commands.sh

echo "Entering chroot environment..."
echo "Note: This will start an interactive session"
echo "Run the final system build from within chroot"

# Enter chroot
sudo chroot "$LFS" /usr/bin/env -i   \
    HOME=/root                  \
    TERM="$TERM"                \
    PS1='(lfs chroot) \u:\w\$ ' \
    PATH=/usr/bin:/usr/sbin     \
    /bin/bash /tmp/chroot_commands.sh

echo "✓ Exited chroot environment"