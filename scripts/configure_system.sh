#!/bin/bash
# LFS System Configuration Script
# Configures boot, networking, users

set -e

echo "=== LFS System Configuration ==="

# Create essential files and directories
echo "Creating essential system files..."

# Create /etc/passwd
cat > /etc/passwd << "EOF"
root:x:0:0:root:/root:/bin/bash
bin:x:1:1:bin:/dev/null:/usr/bin/false
daemon:x:6:6:Daemon User:/dev/null:/usr/bin/false
messagebus:x:18:18:D-Bus Message Daemon User:/run/dbus:/usr/bin/false
uuidd:x:80:80:UUID Generation Daemon User:/dev/null:/usr/bin/false
nobody:x:65534:65534:Unprivileged User:/dev/null:/usr/bin/false
EOF

# Create /etc/group
cat > /etc/group << "EOF"
root:x:0:
sys:x:2:
kmem:x:3:
tape:x:4:
tty:x:5:
daemon:x:6:
floppy:x:7:
disk:x:8:
lp:x:9:
dialout:x:10:
audio:x:11:
video:x:12:
utmp:x:13:
usb:x:14:
cdrom:x:15:
adm:x:16:
messagebus:x:18:
input:x:24:
mail:x:34:
kvm:x:61:
uuidd:x:80:
wheel:x:97:
users:x:999:
nogroup:x:65534:
EOF

# Create /etc/hostname
echo "lfs" > /etc/hostname

# Create /etc/hosts
cat > /etc/hosts << "EOF"
127.0.0.1  localhost
127.0.1.1  lfs.localdomain lfs
::1        localhost ip6-localhost ip6-loopback
ff02::1    ip6-allnodes
ff02::2    ip6-allrouters
EOF

# Configure network interface
cat > /etc/systemd/network/10-eth-dhcp.network << "EOF"
[Match]
Name=eth0

[Network]
DHCP=ipv4

[DHCPv4]
UseDomains=true
EOF

# Create /etc/resolv.conf
cat > /etc/resolv.conf << "EOF"
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF

# Create /etc/inputrc
cat > /etc/inputrc << "EOF"
set horizontal-scroll-mode Off
set meta-flag On
set input-meta On
set convert-meta Off
set output-meta On
set bell-style none

"\eOd": backward-word
"\eOc": forward-word
"\e[1~": beginning-of-line
"\e[4~": end-of-line
"\e[5~": beginning-of-history
"\e[6~": end-of-history
"\e[3~": delete-char
"\e[2~": quoted-insert

set show-all-if-ambiguous On
set show-all-if-unmodified On
EOF

# Create /etc/shells
cat > /etc/shells << "EOF"
/bin/sh
/bin/bash
EOF

# Configure systemd
systemctl preset-all

# Create a test user
echo "Creating test user 'lfs'..."
useradd -m -G users,wheel -s /bin/bash lfs
echo "lfs:lfs" | chpasswd

# Set root password
echo "Setting root password..."
echo "root:root" | chpasswd

# Create /etc/fstab
cat > /etc/fstab << "EOF"
# file system  mount-point  type     options             dump  fsck
#                                                              order

/dev/sda2      /            ext4     defaults            1     1
/dev/sda1      /boot        ext4     defaults            1     2
proc           /proc        proc     nosuid,noexec,nodev 0     0
sysfs          /sys         sysfs    nosuid,noexec,nodev 0     0
devpts         /dev/pts     devpts   gid=5,mode=620      0     0
tmpfs          /run         tmpfs    defaults            0     0
devtmpfs       /dev         devtmpfs mode=0755,nosuid    0     0
tmpfs          /dev/shm     tmpfs    nosuid,nodev        0     0
EOF

# Configure locale
cat > /etc/locale.conf << "EOF"
LANG=en_US.UTF-8
EOF

# Configure console
cat > /etc/vconsole.conf << "EOF"
KEYMAP=us
FONT=lat9w-16
EOF

# Create systemd target
systemctl set-default multi-user.target

echo "✓ System configuration completed"
echo "Hostname: $(cat /etc/hostname)"
echo "Users configured: root, lfs"
echo "Network: DHCP enabled"