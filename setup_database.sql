-- MySQL setup script for LFS Build System
-- Run this script to create the database and user

CREATE DATABASE IF NOT EXISTS lfs_builds CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user (change password in production)
CREATE USER IF NOT EXISTS 'lfs_user'@'localhost' IDENTIFIED BY 'lfs_pass';
GRANT ALL PRIVILEGES ON lfs_builds.* TO 'lfs_user'@'localhost';
FLUSH PRIVILEGES;

USE lfs_builds;

-- The tables will be created automatically by the DatabaseManager
-- This script just sets up the database and user