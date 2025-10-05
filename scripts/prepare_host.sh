#!/bin/bash
# LFS Host System Preparation Script
# Verifies host has required tools for LFS build

set -e

echo "=== LFS Host System Preparation ==="

# Install missing dependencies first (texinfo not available in RHEL 9+)
echo "Installing required host dependencies..."
sudo dnf install -y glibc-devel kernel-headers binutils-devel gcc-c++ 2>/dev/null || {
    echo "⚠ Could not install some packages automatically"
    echo "Please install manually: sudo dnf install glibc-devel kernel-headers binutils-devel gcc-c++"
}
echo "ℹ Note: makeinfo/texinfo not available in RHEL 9+ - using MAKEINFO=missing (standard LFS approach)"

# Check for required tools - use actual command names, not package names
REQUIRED_TOOLS=(
    "bash" "ld" "bison" "ls" "diff" "find" "gawk"
    "gcc" "grep" "gzip" "m4" "make" "patch" "perl" "python3" "sed" "tar" "xz"
)

# Optional tools (warn but don't fail)
OPTIONAL_TOOLS=("texinfo" "makeinfo")

MISSING_TOOLS=()
MISSING_OPTIONAL=()

echo "Checking required tools..."
for tool in "${REQUIRED_TOOLS[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
        MISSING_TOOLS+=("$tool")
        echo "MISSING: $tool"
    else
        echo "OK: $tool"
    fi
done

echo "Checking optional tools..."
for tool in "${OPTIONAL_TOOLS[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
        MISSING_OPTIONAL+=("$tool")
        echo "OPTIONAL: $tool (missing but not required for basic build)"
    else
        echo "OK: $tool"
    fi
done

# Check versions
echo -e "\nChecking tool versions..."

# Bash version
bash --version | head -n1

# Binutils version
ld --version | head -n1

# Bison version
bison --version | head -n1

# GCC version
gcc --version | head -n1

# Make version
make --version | head -n1

# Python version
python3 --version

# Check for /bin/sh -> bash
echo -e "\nChecking /bin/sh link..."
if [ -L /bin/sh ]; then
    echo "/bin/sh -> $(readlink /bin/sh)"
else
    echo "/bin/sh is not a symbolic link"
fi

# Check kernel version
echo -e "\nKernel version:"
uname -r

# Check available disk space
echo -e "\nDisk space check:"
df -h /

# Set LFS environment variable
export LFS=/mnt/lfs
echo -e "\nLFS variable set to: $LFS"

# Create LFS user if not exists
if ! id lfs &>/dev/null; then
    echo "Creating LFS user..."
    sudo groupadd lfs
    sudo useradd -s /bin/bash -g lfs -m -k /dev/null lfs
    sudo passwd lfs
else
    echo "LFS user already exists"
fi

# Fix MySQL database permissions
echo -e "\nFixing MySQL database permissions..."
if [ -f ~/.mysql_credentials ]; then
    MYSQL_ROOT_PASS=$(grep "MySQL Root Password:" ~/.mysql_credentials | cut -d' ' -f4-)
    echo "Using MySQL root password from credentials file"
    mysql -u root -p"$MYSQL_ROOT_PASS" -e "DROP USER IF EXISTS 'lfs_user'@'localhost';" 2>/dev/null || true
    mysql -u root -p"$MYSQL_ROOT_PASS" -e "CREATE USER 'lfs_user'@'localhost' IDENTIFIED BY 'lfs_pass';"
    mysql -u root -p"$MYSQL_ROOT_PASS" -e "GRANT ALL PRIVILEGES ON lfs_builds.* TO 'lfs_user'@'localhost';"
    mysql -u root -p"$MYSQL_ROOT_PASS" -e "FLUSH PRIVILEGES;"
    echo "✓ MySQL user permissions fixed"
else
    echo "⚠ MySQL credentials file not found - skipping database user setup"
    echo "Please run: sudo mysql -p < src/database/setup_database.sql"
fi

if [ ${#MISSING_TOOLS[@]} -eq 0 ]; then
    echo -e "\n✓ Host system preparation completed successfully"
    echo "All required tools are available"
    
    if [ ${#MISSING_OPTIONAL[@]} -gt 0 ]; then
        echo "⚠ Optional tools missing: ${MISSING_OPTIONAL[*]}"
        echo "These are not required for basic LFS build but may be needed for documentation"
    fi
else
    echo -e "\n✗ Host system preparation failed"
    echo "Missing required tools: ${MISSING_TOOLS[*]}"
    echo "Install missing tools before proceeding"
    
    if [ ${#MISSING_OPTIONAL[@]} -gt 0 ]; then
        echo "Also missing optional tools: ${MISSING_OPTIONAL[*]}"
    fi
    
    exit 1
fi