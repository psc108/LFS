#!/bin/bash
# MySQL installation script for RHEL 9+ and Amazon Linux 2023

set -e

# Detect distribution
if [ -f /etc/redhat-release ]; then
    if grep -q "Red Hat Enterprise Linux" /etc/redhat-release; then
        DISTRO="rhel"
        VERSION=$(grep -oE '[0-9]+' /etc/redhat-release | head -1)
    elif grep -q "Amazon Linux" /etc/redhat-release; then
        DISTRO="amzn"
        VERSION="2023"
    else
        echo "Unsupported distribution"
        exit 1
    fi
else
    echo "Not a supported RPM-based distribution"
    exit 1
fi

echo "Detected: $DISTRO $VERSION"

# Install MySQL repository
if [ "$DISTRO" = "rhel" ] && [ "$VERSION" -ge 9 ]; then
    sudo dnf install -y https://dev.mysql.com/get/mysql80-community-release-el9-1.noarch.rpm
elif [ "$DISTRO" = "amzn" ]; then
    sudo dnf install -y https://dev.mysql.com/get/mysql80-community-release-el9-1.noarch.rpm
fi

# Install MySQL server (skip GPG check for Oracle MySQL packages)
sudo dnf install -y --nogpgcheck mysql-community-server

# Start and enable MySQL
sudo systemctl start mysqld
sudo systemctl enable mysqld

# Get temporary root password
TEMP_PASSWORD=$(sudo grep 'temporary password' /var/log/mysqld.log | tail -1 | awk '{print $NF}')

echo "MySQL installed successfully"
echo "Temporary root password: $TEMP_PASSWORD"
echo "Run 'mysql_secure_installation' to secure your installation"
echo "Then run: sudo mysql < setup_database.sql"