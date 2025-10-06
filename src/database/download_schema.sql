-- Download tracking tables for LFS source packages

CREATE TABLE IF NOT EXISTS lfs_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version VARCHAR(20) NOT NULL UNIQUE,
    release_date DATE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_version (version)
);

CREATE TABLE IF NOT EXISTS package_downloads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lfs_version VARCHAR(20) NOT NULL,
    package_name VARCHAR(255) NOT NULL,
    package_version VARCHAR(100),
    file_name VARCHAR(255) NOT NULL,
    download_url TEXT NOT NULL,
    mirror_url TEXT,
    file_size BIGINT,
    checksum_md5 VARCHAR(32),
    checksum_sha256 VARCHAR(64),
    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    download_duration_ms INT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    git_commit_hash VARCHAR(40),
    INDEX idx_lfs_version (lfs_version),
    INDEX idx_package_name (package_name),
    INDEX idx_download_date (download_date),
    FOREIGN KEY (lfs_version) REFERENCES lfs_versions(version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS source_repositories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lfs_version VARCHAR(20) NOT NULL,
    repo_path VARCHAR(500) NOT NULL,
    git_branch VARCHAR(100) NOT NULL,
    total_packages INT DEFAULT 0,
    downloaded_packages INT DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_lfs_version (lfs_version),
    FOREIGN KEY (lfs_version) REFERENCES lfs_versions(version) ON DELETE CASCADE
);

-- Insert default LFS 12.4 version
INSERT IGNORE INTO lfs_versions (version, release_date, description) 
VALUES ('12.4', '2024-09-01', 'Linux From Scratch version 12.4 - Stable release');

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_package_downloads_composite ON package_downloads(lfs_version, package_name, success);
CREATE INDEX IF NOT EXISTS idx_source_repos_version ON source_repositories(lfs_version);

-- Add trigger to update repository stats automatically
DELIMITER //
CREATE TRIGGER IF NOT EXISTS update_repo_stats_after_download
AFTER INSERT ON package_downloads
FOR EACH ROW
BEGIN
    IF NEW.success = TRUE THEN
        UPDATE source_repositories 
        SET downloaded_packages = (
            SELECT COUNT(*) FROM package_downloads 
            WHERE lfs_version = NEW.lfs_version AND success = TRUE
        ),
        total_size_bytes = (
            SELECT COALESCE(SUM(file_size), 0) FROM package_downloads 
            WHERE lfs_version = NEW.lfs_version AND success = TRUE
        ),
        last_updated = CURRENT_TIMESTAMP
        WHERE lfs_version = NEW.lfs_version;
    END IF;
END//
DELIMITER ;