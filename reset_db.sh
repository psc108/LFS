#!/bin/bash
# Reset LFS Database Script

echo "🔄 Resetting LFS Build Database..."

# Get MySQL root password from credentials file
ROOT_PASSWORD=""
if [ -f ".mysql_credentials" ]; then
    ROOT_PASSWORD=$(grep "MySQL Root Password:" .mysql_credentials | cut -d':' -f2- | sed 's/^ *//' | sed 's/&quot;/"/g')
fi

if [ -z "$ROOT_PASSWORD" ]; then
    echo "❌ MySQL root password not found in .mysql_credentials"
    echo "Please enter MySQL root password:"
    read -s ROOT_PASSWORD
fi

# Reset database
mysql -u root -p"$ROOT_PASSWORD" < reset_database.sql

if [ $? -eq 0 ]; then
    echo "✅ Database reset successfully"
    echo "📊 New database schema created with proper column sizes"
else
    echo "❌ Database reset failed"
    exit 1
fi