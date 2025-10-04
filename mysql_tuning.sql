-- MySQL configuration tuning for LFS Build System
-- Run this as MySQL root user to prevent connection timeouts

-- Increase connection timeout values
SET GLOBAL wait_timeout = 28800;
SET GLOBAL interactive_timeout = 28800;
SET GLOBAL net_read_timeout = 120;
SET GLOBAL net_write_timeout = 120;

-- Increase max connections
SET GLOBAL max_connections = 200;

-- Increase packet size for large documents
SET GLOBAL max_allowed_packet = 64*1024*1024;

-- Show current settings
SELECT 
    @@wait_timeout as wait_timeout,
    @@interactive_timeout as interactive_timeout,
    @@net_read_timeout as net_read_timeout,
    @@net_write_timeout as net_write_timeout,
    @@max_connections as max_connections,
    @@max_allowed_packet as max_allowed_packet;

-- To make these permanent, add to /etc/mysql/mysql.conf.d/mysqld.cnf:
-- [mysqld]
-- wait_timeout = 28800
-- interactive_timeout = 28800
-- net_read_timeout = 120
-- net_write_timeout = 120
-- max_connections = 200
-- max_allowed_packet = 64M