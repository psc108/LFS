-- Next Build Reports Database Schema
-- Stores comprehensive build analysis reports with full output preservation

CREATE TABLE IF NOT EXISTS next_build_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    build_id INT,
    report_title VARCHAR(255) NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_version VARCHAR(50) DEFAULT '1.0',
    
    -- Comprehensive analysis data
    total_builds_analyzed INT DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0.00,
    avg_build_duration INT DEFAULT 0,
    
    -- Full analysis output (preserved completely)
    full_analysis_output LONGTEXT,
    failure_patterns_json TEXT,
    recommendations_json TEXT,
    next_build_advice_json TEXT,
    
    -- Report metadata
    report_size_bytes INT DEFAULT 0,
    export_count INT DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_build_id (build_id),
    INDEX idx_generated_at (generated_at),
    INDEX idx_success_rate (success_rate),
    FULLTEXT(full_analysis_output, report_title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table for tracking report access and usage
CREATE TABLE IF NOT EXISTS report_access_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_id INT,
    access_type ENUM('view', 'export', 'print', 'copy') NOT NULL,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_context VARCHAR(255),
    
    FOREIGN KEY (report_id) REFERENCES next_build_reports(id) ON DELETE CASCADE,
    INDEX idx_report_access (report_id, accessed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Update trigger to maintain report metadata
DELIMITER //
CREATE TRIGGER update_report_access 
    BEFORE UPDATE ON next_build_reports
    FOR EACH ROW
BEGIN
    SET NEW.last_accessed = CURRENT_TIMESTAMP;
END//
DELIMITER ;