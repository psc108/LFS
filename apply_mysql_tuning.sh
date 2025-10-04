#!/bin/bash

echo "Applying MySQL tuning for LFS Build System..."
echo "This will prevent connection timeouts during long builds."
echo ""
echo "Please enter your MySQL root password when prompted:"

mysql -u root -p << 'EOF'
-- MySQL configuration tuning for LFS Build System
SET GLOBAL wait_timeout = 28800;
SET GLOBAL interactive_timeout = 28800;
SET GLOBAL net_read_timeout = 120;
SET GLOBAL net_write_timeout = 120;
SET GLOBAL max_connections = 200;
SET GLOBAL max_allowed_packet = 67108864;

SELECT 'MySQL tuning applied successfully!' as status;

SELECT 
    @@wait_timeout as wait_timeout,
    @@interactive_timeout as interactive_timeout,
    @@net_read_timeout as net_read_timeout,
    @@net_write_timeout as net_write_timeout,
    @@max_connections as max_connections,
    @@max_allowed_packet as max_allowed_packet;
EOF

echo ""
echo "✅ MySQL tuning applied!"
echo "Note: These settings are temporary. To make them permanent,"
echo "add the following to /etc/mysql/mysql.conf.d/mysqld.cnf:"
echo ""
echo "[mysqld]"
echo "wait_timeout = 28800"
echo "interactive_timeout = 28800" 
echo "net_read_timeout = 120"
echo "net_write_timeout = 120"
echo "max_connections = 200"
echo "max_allowed_packet = 64M"