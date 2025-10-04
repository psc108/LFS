#!/bin/bash
# LFS Package Download Script
# Downloads all required LFS packages

set -e

echo "=== LFS Package Download ==="

export LFS=/mnt/lfs
SOURCES_DIR="$LFS/sources"

# Verify LFS directory structure exists
echo "Verifying LFS directory structure..."
if [ ! -d "$LFS" ]; then
    echo "ERROR: LFS directory $LFS does not exist"
    echo "Please run the LFS directory setup from the installation guide:"
    echo "  sudo mkdir -p /mnt/lfs/sources"
    echo "  sudo chown -R lfs:lfs /mnt/lfs"
    exit 1
fi

if [ ! -d "$SOURCES_DIR" ]; then
    echo "Creating sources directory: $SOURCES_DIR"
    mkdir -p "$SOURCES_DIR" || {
        echo "ERROR: Could not create $SOURCES_DIR"
        echo "Please ensure LFS directory setup is complete (see installation guide)"
        exit 1
    }
fi

echo "Changing to sources directory: $SOURCES_DIR"
cd "$SOURCES_DIR"

echo "Downloading LFS packages to $SOURCES_DIR"

# LFS 12.4 required packages
LFS_PACKAGES=(
    "Python-3.13.7.tar.xz"
    "XML-Parser-2.47.tar.gz"
    "acl-2.3.2.tar.xz"
    "attr-2.5.2.tar.gz"
    "autoconf-2.72.tar.xz"
    "automake-1.18.1.tar.xz"
    "bash-5.3.tar.gz"
    "bc-7.0.3.tar.xz"
    "binutils-2.45.tar.xz"
    "bison-3.8.2.tar.xz"
    "bzip2-1.0.8.tar.gz"
    "coreutils-9.7.tar.xz"
    "dbus-1.16.2.tar.xz"
    "dejagnu-1.6.3.tar.gz"
    "diffutils-3.12.tar.xz"
    "e2fsprogs-1.47.3.tar.gz"
    "elfutils-0.193.tar.bz2"
    "expat-2.7.1.tar.xz"
    "expect5.45.4.tar.gz"
    "file-5.46.tar.gz"
    "findutils-4.10.0.tar.xz"
    "flex-2.6.4.tar.gz"
    "flit_core-3.12.0.tar.gz"
    "gawk-5.3.2.tar.xz"
    "gcc-15.2.0.tar.xz"
    "gdbm-1.26.tar.gz"
    "gettext-0.26.tar.xz"
    "glibc-2.42.tar.xz"
    "gmp-6.3.0.tar.xz"
    "gperf-3.3.tar.gz"
    "grep-3.12.tar.xz"
    "groff-1.23.0.tar.gz"
    "grub-2.12.tar.xz"
    "gzip-1.14.tar.xz"
    "iana-etc-20250807.tar.gz"
    "inetutils-2.6.tar.xz"
    "intltool-0.51.0.tar.gz"
    "iproute2-6.16.0.tar.xz"
    "jinja2-3.1.6.tar.gz"
    "kbd-2.8.0.tar.xz"
    "kmod-34.2.tar.xz"
    "less-679.tar.gz"
    "lfs-bootscripts-20240825.tar.xz"
    "libcap-2.76.tar.xz"
    "libffi-3.5.2.tar.gz"
    "libpipeline-1.5.8.tar.gz"
    "libtool-2.5.4.tar.xz"
    "libxcrypt-4.4.38.tar.xz"
    "linux-6.16.1.tar.xz"
    "lz4-1.10.0.tar.gz"
    "m4-1.4.20.tar.xz"
    "make-4.4.1.tar.gz"
    "man-db-2.13.1.tar.xz"
    "man-pages-6.15.tar.xz"
    "markupsafe-3.0.2.tar.gz"
    "meson-1.8.3.tar.gz"
    "mpc-1.3.1.tar.gz"
    "mpfr-4.2.2.tar.xz"
    "ncurses-6.5-20250809.tgz"
    "ninja-1.13.1.tar.gz"
    "openssl-3.5.2.tar.gz"
    "packaging-25.0.tar.gz"
    "patch-2.8.tar.xz"
    "perl-5.42.0.tar.xz"
    "pkgconf-2.5.1.tar.xz"
    "procps-ng-4.0.5.tar.xz"
    "psmisc-23.7.tar.xz"
    "readline-8.3.tar.gz"
    "sed-4.9.tar.xz"
    "setuptools-80.9.0.tar.gz"
    "shadow-4.18.0.tar.xz"
    "sysklogd-2.7.2.tar.gz"
    "systemd-257.8.tar.gz"
    "sysvinit-3.14.tar.xz"
    "tar-1.35.tar.xz"
    "tcl8.6.16-src.tar.gz"
    "texinfo-7.2.tar.xz"
    "tzdata2025b.tar.gz"
    "udev-lfs-20230818.tar.xz"
    "util-linux-2.41.1.tar.xz"
    "vim-9.1.1629.tar.gz"
    "wheel-0.46.1.tar.gz"
    "xz-5.8.1.tar.xz"
    "zlib-1.3.1.tar.gz"
    "zstd-1.5.7.tar.gz"
)

# First check if packages already exist and fix permissions if needed
echo "Checking existing packages in $SOURCES_DIR..."
EXISTING_COUNT=0
for package in "${LFS_PACKAGES[@]}"; do
    if [ -f "$package" ]; then
        EXISTING_COUNT=$((EXISTING_COUNT + 1))
        # Check if file is readable
        if [ ! -r "$package" ]; then
            echo "Warning: $package exists but is not readable (permission issue)"
        fi
    fi
done

if [ $EXISTING_COUNT -eq ${#LFS_PACKAGES[@]} ]; then
    echo "✓ All ${#LFS_PACKAGES[@]} LFS packages already exist in sources directory"
    PACKAGES_COPIED=$EXISTING_COUNT
else
    echo "Found $EXISTING_COUNT of ${#LFS_PACKAGES[@]} packages, copying missing packages..."
    
    # Copy packages from our repository sources
    # Try multiple possible repository locations
    REPO_LOCATIONS=(
        "/home/scottp/lfs_repositories/sources"
        "$HOME/lfs_repositories/sources"
        "$HOME/.lfs_build_system/sources"
        "./sources"
        "../sources"
    )
    
    PACKAGES_COPIED=$EXISTING_COUNT
    for REPO_SOURCES in "${REPO_LOCATIONS[@]}"; do
        if [ -d "$REPO_SOURCES" ]; then
            echo "Found repository sources at: $REPO_SOURCES"
            echo "Copying missing LFS 12.4 packages..."
            
            # Copy only the required LFS packages that don't exist
            for package in "${LFS_PACKAGES[@]}"; do
                if [ ! -f "$package" ] && [ -f "$REPO_SOURCES/$package" ]; then
                    if cp "$REPO_SOURCES/$package" . 2>/dev/null; then
                        echo "Copied $package"
                        PACKAGES_COPIED=$((PACKAGES_COPIED + 1))
                    else
                        echo "Warning: Could not copy $package (check permissions)"
                    fi
                fi
            done
            
            if [ $PACKAGES_COPIED -eq ${#LFS_PACKAGES[@]} ]; then
                echo "Successfully have all ${#LFS_PACKAGES[@]} required LFS packages"
                break
            fi
        fi
    done
fi

if [ $PACKAGES_COPIED -lt ${#LFS_PACKAGES[@]} ] && [ $EXISTING_COUNT -eq 0 ]; then
    echo "No cached packages found in repository locations"
    echo "Repository locations checked:"
    for loc in "${REPO_LOCATIONS[@]}"; do
        echo "  - $loc"
    done
fi

# Verify packages exist
PACKAGE_COUNT=$(ls -1 *.tar.* *.tgz 2>/dev/null | wc -l)
echo "Found $PACKAGE_COUNT packages in sources directory"

if [ $PACKAGES_COPIED -gt 0 ]; then
    echo "✓ Successfully copied $PACKAGES_COPIED of ${#LFS_PACKAGES[@]} required LFS packages from repository cache"
fi

# Check for missing packages
MISSING_PACKAGES=()
for package in "${LFS_PACKAGES[@]}"; do
    if [ ! -f "$package" ]; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -eq 0 ]; then
    echo "✓ All ${#LFS_PACKAGES[@]} LFS 12.4 packages are available for build"
else
    echo "⚠ Warning: ${#MISSING_PACKAGES[@]} packages missing:"
    for missing in "${MISSING_PACKAGES[@]}"; do
        echo "  - $missing"
    done
fi

# Create wget-list for missing packages if needed
if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo "Creating wget-list for missing packages..."
    {
        echo "# LFS 12.4 Package URLs - Generated for missing packages"
        echo "# Use Package Manager in GUI to download these packages"
        for missing in "${MISSING_PACKAGES[@]}"; do
            echo "# Missing: $missing"
        done
    } > wget-list 2>/dev/null || echo "Warning: Could not create wget-list file"
fi

echo "Sources directory prepared: $SOURCES_DIR"
echo "✓ Package download stage completed successfully"
exit 0