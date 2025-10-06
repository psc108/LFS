#!/bin/bash
# Install LFS build dependencies for RHEL 9/Amazon Linux 2023

echo "Installing LFS build dependencies..."

sudo dnf install -y \
    automake autoconf libtool make gcc gcc-c++ \
    binutils glibc-devel kernel-headers \
    bison flex texinfo patch diffutils findutils \
    gawk sed grep coreutils bash tar gzip bzip2 xz \
    which file

echo "Verifying critical tools..."
which missing || echo "WARNING: missing command not found"
which autoconf || echo "WARNING: autoconf not found"
which automake || echo "WARNING: automake not found"

echo "Build dependencies installation complete!"