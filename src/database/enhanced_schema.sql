-- Enhanced Database Schema for LFS Build System
-- Advanced data collection and retention for analytics and ML

USE lfs_builds;

-- System Metrics Collection
CREATE TABLE IF NOT EXISTS system_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id VARCHAR(255),
    stage_name VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cpu_percent DECIMAL(5,2),
    memory_percent DECIMAL(5,2),
    memory_used_mb INT,
    disk_io_read_mb DECIMAL(10,2),
    disk_io_write_mb DECIMAL(10,2),
    network_bytes_sent BIGINT,
    network_bytes_recv BIGINT,
    load_average_1m DECIMAL(4,2),
    temperature_celsius DECIMAL(4,1),
    INDEX idx_build_stage (build_id, stage_name),
    INDEX idx_timestamp (timestamp)
);

-- Build Environment Tracking
CREATE TABLE IF NOT EXISTS build_environment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id VARCHAR(255) UNIQUE,
    host_os VARCHAR(100),
    host_kernel VARCHAR(100),
    host_arch VARCHAR(50),
    cpu_model VARCHAR(200),
    cpu_cores INT,
    total_memory_gb DECIMAL(6,2),
    disk_space_gb DECIMAL(10,2),
    python_version VARCHAR(50),
    gcc_version VARCHAR(50),
    make_version VARCHAR(50),
    environment_vars JSON,
    package_versions JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_build_id (build_id)
);

-- Performance Analytics
CREATE TABLE IF NOT EXISTS stage_performance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id VARCHAR(255),
    stage_name VARCHAR(100),
    stage_order INT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INT,
    cpu_time_seconds DECIMAL(10,2),
    peak_memory_mb INT,
    disk_read_mb DECIMAL(10,2),
    disk_write_mb DECIMAL(10,2),
    exit_code INT,
    warnings_count INT,
    errors_count INT,
    lines_processed INT,
    INDEX idx_build_stage (build_id, stage_name),
    INDEX idx_duration (duration_seconds),
    INDEX idx_stage_order (stage_order)
);

-- Mirror Performance Tracking
CREATE TABLE IF NOT EXISTS mirror_performance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mirror_url VARCHAR(500),
    package_name VARCHAR(100),
    download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_size_mb DECIMAL(10,2),
    download_speed_mbps DECIMAL(8,2),
    success BOOLEAN,
    error_message TEXT,
    response_time_ms INT,
    http_status_code INT,
    retry_count INT,
    INDEX idx_mirror_package (mirror_url(100), package_name),
    INDEX idx_success_time (success, download_time),
    INDEX idx_speed (download_speed_mbps)
);

-- Pattern Recognition Data
CREATE TABLE IF NOT EXISTS failure_patterns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pattern_name VARCHAR(200),
    pattern_type ENUM('error', 'warning', 'performance', 'environment'),
    regex_pattern TEXT,
    description TEXT,
    severity ENUM('low', 'medium', 'high', 'critical'),
    auto_fix_command TEXT,
    detection_count INT DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_pattern (pattern_name),
    INDEX idx_type_severity (pattern_type, severity)
);

-- Pattern Detection History
CREATE TABLE IF NOT EXISTS pattern_detections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id VARCHAR(255),
    stage_name VARCHAR(100),
    pattern_id INT,
    confidence_score DECIMAL(4,2),
    matched_text TEXT,
    context_before TEXT,
    context_after TEXT,
    auto_fix_applied BOOLEAN DEFAULT FALSE,
    fix_successful BOOLEAN,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pattern_id) REFERENCES failure_patterns(id),
    INDEX idx_build_pattern (build_id, pattern_id),
    INDEX idx_confidence (confidence_score),
    INDEX idx_detected_at (detected_at)
);

-- Predictive Analytics Storage
CREATE TABLE IF NOT EXISTS build_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id VARCHAR(255),
    prediction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    risk_score DECIMAL(5,2),
    success_probability DECIMAL(5,2),
    predicted_duration_minutes INT,
    risk_factors JSON,
    model_version VARCHAR(50),
    actual_success BOOLEAN,
    actual_duration_minutes INT,
    prediction_accuracy DECIMAL(5,2),
    INDEX idx_build_id (build_id),
    INDEX idx_risk_score (risk_score),
    INDEX idx_prediction_time (prediction_time)
);

-- ML Training Data
CREATE TABLE IF NOT EXISTS ml_training_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id VARCHAR(255),
    feature_vector JSON,
    target_success BOOLEAN,
    target_duration_minutes INT,
    stage_failures JSON,
    environment_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_for_training BOOLEAN DEFAULT FALSE,
    INDEX idx_build_id (build_id),
    INDEX idx_target_success (target_success),
    INDEX idx_environment (environment_hash)
);

-- Enhanced Audit Trail
CREATE TABLE IF NOT EXISTS user_actions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id VARCHAR(255),
    action_type ENUM('start_build', 'cancel_build', 'modify_config', 'apply_fix', 'archive_build'),
    action_details JSON,
    user_context JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_build_action (build_id, action_type),
    INDEX idx_timestamp (timestamp)
);

-- Configuration Change History
CREATE TABLE IF NOT EXISTS config_changes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id VARCHAR(255),
    change_type ENUM('create', 'modify', 'delete'),
    config_name VARCHAR(200),
    old_content TEXT,
    new_content TEXT,
    diff_summary TEXT,
    changed_by VARCHAR(100),
    change_reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_build_config (build_id, config_name),
    INDEX idx_change_type (change_type)
);

-- System State Snapshots
CREATE TABLE IF NOT EXISTS system_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id VARCHAR(255),
    snapshot_type ENUM('pre_build', 'post_stage', 'error_state', 'post_build'),
    stage_name VARCHAR(100),
    process_list JSON,
    mount_points JSON,
    disk_usage JSON,
    network_connections JSON,
    environment_vars JSON,
    file_permissions JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_build_type (build_id, snapshot_type),
    INDEX idx_stage (stage_name)
);

-- Recovery Actions Log
CREATE TABLE IF NOT EXISTS recovery_actions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id VARCHAR(255),
    failure_pattern_id INT,
    recovery_type ENUM('auto_fix', 'manual_fix', 'rollback', 'restart'),
    commands_executed JSON,
    success BOOLEAN,
    recovery_time_seconds INT,
    side_effects TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (failure_pattern_id) REFERENCES failure_patterns(id),
    INDEX idx_build_recovery (build_id, recovery_type),
    INDEX idx_success (success)
);

-- Build Correlation Analysis
CREATE TABLE IF NOT EXISTS build_correlations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id_1 VARCHAR(255),
    build_id_2 VARCHAR(255),
    correlation_type ENUM('similar_config', 'similar_environment', 'similar_failure', 'similar_performance'),
    correlation_score DECIMAL(4,2),
    correlation_factors JSON,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_builds (build_id_1, build_id_2),
    INDEX idx_correlation_type (correlation_type),
    INDEX idx_score (correlation_score)
);

-- Performance Baselines
CREATE TABLE IF NOT EXISTS performance_baselines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stage_name VARCHAR(100),
    environment_type VARCHAR(100),
    baseline_duration_seconds INT,
    baseline_memory_mb INT,
    baseline_cpu_percent DECIMAL(5,2),
    sample_size INT,
    confidence_interval DECIMAL(5,2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_stage_env (stage_name, environment_type),
    INDEX idx_stage (stage_name)
);

-- Community Pattern Sharing
CREATE TABLE IF NOT EXISTS community_patterns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pattern_hash VARCHAR(64) UNIQUE,
    pattern_data JSON,
    submission_count INT DEFAULT 1,
    success_reports INT DEFAULT 0,
    failure_reports INT DEFAULT 0,
    community_rating DECIMAL(3,2) DEFAULT 0.0,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_hash (pattern_hash),
    INDEX idx_rating (community_rating)
);

-- Create indexes for existing tables
CREATE INDEX idx_builds_status ON builds(status);
CREATE INDEX idx_builds_start_time ON builds(start_time);
CREATE INDEX idx_builds_duration ON builds(duration_seconds);
CREATE INDEX idx_documents_build_type ON build_documents(build_id, document_type);
CREATE INDEX idx_documents_created ON build_documents(created_at);
CREATE INDEX idx_stages_build_order ON build_stages(build_id, stage_order);

-- Create full-text indexes for enhanced search
ALTER TABLE build_documents ADD FULLTEXT(title, content);
ALTER TABLE failure_patterns ADD FULLTEXT(pattern_name, description);

-- Insert default failure patterns
INSERT IGNORE INTO failure_patterns (pattern_name, pattern_type, regex_pattern, description, severity, auto_fix_command) VALUES
('Permission Denied', 'error', 'Permission denied|permission denied', 'File or directory permission issues', 'high', 'sudo chown -R lfs:lfs /mnt/lfs && sudo chmod -R 755 /mnt/lfs'),
('Missing Package', 'error', 'No such file or directory.*\\.tar\\.|cannot find.*\\.tar\\.', 'Source package file not found', 'high', 'cd /mnt/lfs/sources && wget -c'),
('Compilation Error', 'error', 'error:|Error:|ERROR:', 'General compilation errors', 'medium', 'make clean && make'),
('Out of Space', 'error', 'No space left on device', 'Insufficient disk space', 'critical', 'df -h && du -sh /mnt/lfs/*'),
('Network Timeout', 'error', 'Connection timed out|Network is unreachable', 'Network connectivity issues', 'medium', 'ping -c 3 google.com'),
('Missing Dependencies', 'error', 'command not found|No such file or directory.*bin/', 'Required tools or dependencies missing', 'high', 'which gcc make tar gzip'),
('Memory Exhausted', 'error', 'virtual memory exhausted|Cannot allocate memory', 'Insufficient memory for compilation', 'high', 'free -h && sync && echo 3 > /proc/sys/vm/drop_caches'),
('Makeinfo Missing', 'warning', 'WARNING.*makeinfo.*missing', 'Makeinfo tool not available', 'low', 'sudo dnf install texinfo'),
('Slow Performance', 'performance', '', 'Build stage taking longer than baseline', 'medium', 'top -b -n 1 | head -20'),
('High CPU Usage', 'performance', '', 'CPU usage above 95% for extended period', 'low', 'nice -n 10');