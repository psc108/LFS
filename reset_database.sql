-- Reset LFS Build Database
-- Drops and recreates database with proper schema

DROP DATABASE IF EXISTS lfs_builds;
CREATE DATABASE lfs_builds CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE lfs_builds;

-- Main builds table
CREATE TABLE builds (
    build_id VARCHAR(255) PRIMARY KEY,
    config_name VARCHAR(255),
    status ENUM('running', 'success', 'failed', 'cancelled') DEFAULT 'running',
    total_stages INT DEFAULT 0,
    completed_stages INT DEFAULT 0,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP NULL,
    duration_seconds INT NULL,
    INDEX idx_status (status),
    INDEX idx_start_time (start_time)
);

-- Build stages table
CREATE TABLE build_stages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id VARCHAR(255),
    stage_name VARCHAR(100),
    stage_order INT,
    status ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending',
    start_time TIMESTAMP NULL,
    end_time TIMESTAMP NULL,
    output_log LONGTEXT,
    FOREIGN KEY (build_id) REFERENCES builds(build_id) ON DELETE CASCADE,
    INDEX idx_build_stage (build_id, stage_order)
);

-- Build documents table with proper document_type size
CREATE TABLE build_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id VARCHAR(255),
    document_type VARCHAR(20),  -- Increased size for document types
    title VARCHAR(500),
    content LONGTEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (build_id) REFERENCES builds(build_id) ON DELETE CASCADE,
    INDEX idx_build_type (build_id, document_type),
    INDEX idx_created (created_at),
    FULLTEXT(title, content)
);

-- Repository snapshots
CREATE TABLE repo_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id VARCHAR(255),
    snapshot_type ENUM('pre_build', 'post_build', 'error_state') DEFAULT 'pre_build',
    git_commit_hash VARCHAR(40),
    git_branch VARCHAR(100),
    config_files JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (build_id) REFERENCES builds(build_id) ON DELETE CASCADE,
    INDEX idx_build_snapshot (build_id, snapshot_type)
);

-- Next build reports
CREATE TABLE next_build_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id INT,
    report_title VARCHAR(255) NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_version VARCHAR(50) DEFAULT '1.0',
    total_builds_analyzed INT DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0.00,
    avg_build_duration INT DEFAULT 0,
    full_analysis_output LONGTEXT,
    failure_patterns_json TEXT,
    recommendations_json TEXT,
    next_build_advice_json TEXT,
    report_size_bytes INT DEFAULT 0,
    export_count INT DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_build_id (build_id),
    INDEX idx_generated_at (generated_at),
    INDEX idx_success_rate (success_rate),
    FULLTEXT(full_analysis_output, report_title)
);

-- Report access log
CREATE TABLE report_access_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_id INT,
    access_type ENUM('view', 'export', 'print', 'copy') NOT NULL,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_context VARCHAR(255),
    FOREIGN KEY (report_id) REFERENCES next_build_reports(id) ON DELETE CASCADE,
    INDEX idx_report_access (report_id, accessed_at)
);

GRANT ALL PRIVILEGES ON lfs_builds.* TO 'root'@'localhost';
FLUSH PRIVILEGES;