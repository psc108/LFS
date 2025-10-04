# Linux From Scratch Build System

A native GUI build system for Linux From Scratch with MySQL backend, integrated version control, and comprehensive build documentation.

## Features

- **Native GUI**: PyQt5-based interface for RHEL 9/Amazon Linux 2023 with dropdown menu controls
- **MySQL Backend**: All build attempts logged to searchable database with document preservation
- **Complete LFS 12.4**: Full Linux From Scratch build automation with 10 stages
- **Modular Architecture**: Separate, updateable build stages with rollback capability
- **Self-Documenting**: Automatic documentation of every build process
- **Git-Style Repository**: Built-in version control for build configurations
- **Searchable Documents**: Full-text search across all build logs and documents
- **Removable Media Support**: USB/external drive detection with real-time space monitoring
- **Intelligent Downloads**: Dynamic package discovery with multi-mirror failover, global mirrors, and performance grading
- **Live Repository Updates**: Real-time visibility of downloaded packages with file management
- **Mirror Performance Tracking**: Automatic mirror grading and optimization with global and per-package mirror support
- **Package Management**: Comprehensive package manager with cache status and pre-download capabilities
- **Kernel Configuration**: Interactive GUI for configuring Linux kernel build parameters with context-sensitive help
- **Build Archiving**: Archive builds while preserving all historical documents and logs

## Architecture

### Core Components

1. **Database Layer** (`src/database/`)
   - MySQL integration with full-text search
   - Build logging and document storage
   - Searchable build history

2. **Build Engine** (`src/build/`)
   - Modular stage execution
   - Real-time logging and monitoring
   - Rollback capabilities
   - Event-driven architecture
   - Complete LFS 12.4 build scripts

3. **Repository Manager** (`src/repository/`)
   - Git-style version control
   - Build configuration management
   - Snapshot and restore functionality

4. **GUI Interface** (`src/gui/`)
   - Native Qt interface
   - Real-time build monitoring
   - Document browsing and search
   - Repository management

## Installation

### Prerequisites

```bash
# RHEL 9 / Amazon Linux 2023
sudo dnf install python3 python3-pip git
```

### Setup

1. **Clone and install dependencies:**
```bash
git clone <repository>
cd LFS
pip3 install -r requirements.txt
```

2. **Install MySQL:**
```bash
sudo ./src/database/install_mysql.sh
```

3. **Setup MySQL database:**
```bash
# First secure MySQL installation
sudo mysql_secure_installation

# Then setup database (enter root password when prompted)
sudo mysql -p < setup_database.sql
```

4. **Configure storage (optional):**
   - Use Settings to select storage locations
   - Choose removable media for builds requiring large storage
   - Monitor disk space usage in real-time

5. **Run the application:**
```bash
python3 main.py
```

## Usage

### Creating a Build Configuration

1. Click "New Build" in the GUI
2. Enter configuration name and YAML content
3. Configuration is automatically saved to the repository

### Starting a Build

1. Select a configuration from the repository
2. Click "Start Build"
3. Monitor progress in real-time
4. View logs and documents as they're generated

### Searching Builds

- Use the search box to find builds by ID or content
- Filter by status (running, success, failed, cancelled)
- Full-text search across all build documents

### Repository Management

- All configurations are version controlled
- Commit changes with descriptive messages
- Create branches for different build variants
- Restore previous configurations from snapshots

### Build Management

- **Intelligent Package Discovery**: Dynamic package detection from LFS Matrix, official LFS site, and hardcoded fallbacks
- **Smart Downloads**: Multi-mirror failover with global mirrors, automatic performance grading and mirror prioritization
- **Package Manager**: Pre-download packages, view cache status, export wget-list and md5sums
- **Live Repository View**: Real-time file browser showing cached packages with verification and file management
- **Cancel Operations**: Cancel running builds or downloads at any time
- **Cleanup Builds**: Clean up stuck or orphaned build processes
- **Build Actions Menu**: Organized dropdown menu for all build operations
- **Kernel Configuration**: Interactive kernel parameter configuration with tabbed interface and help system
- **Archive Management**: Archive completed builds while preserving all documents for historical reference

### Storage Management

- **Flexible Storage**: Support for internal drives, USB devices, and external storage
- **Removable Media Detection**: Automatic detection of USB drives, external HDDs, and SD cards
- **Real-time Space Monitoring**: Live disk usage information with capacity warnings
- **Storage Requirements**: Repository (~2GB), LFS Build (~15GB for complete build)
- **Multi-Device Support**: Use different storage devices for repository and build artifacts

### LFS Build Stages

Complete Linux From Scratch 12.4 build automation:

1. **Host System Preparation** - Verify host has required tools
2. **Partition Setup** - Create LFS partition and mount points  
3. **Package Downloads** - Download 85 core LFS source packages
4. **Toolchain Build** - Build cross-compilation tools (binutils, gcc, glibc)
5. **Temporary System** - Build temporary versions of core utilities
6. **Chroot Environment** - Enter isolated build environment
7. **Final System Build** - Build final versions of all packages
8. **System Configuration** - Configure boot, networking, users
9. **Kernel Build** - Compile and install Linux kernel with custom configuration
10. **Bootloader Setup** - Install GRUB bootloader

## Database Schema

### Tables

- **builds**: Main build records with status and timing
- **build_stages**: Individual stage execution logs
- **build_documents**: Searchable documents (logs, configs, outputs)
- **repo_snapshots**: Repository state snapshots

### Document Types

- `log`: Stage execution logs
- `config`: Build configurations
- `output`: Build outputs and artifacts
- `error`: Error messages and diagnostics
- `summary`: Build summaries and reports

## Modular Design

### Build Stages

Each build stage is independent with:
- Dependencies specification
- Rollback commands
- Individual logging
- Status tracking

### Stage Configuration Example

```yaml
stages:
  - name: prepare_host
    order: 1
    command: bash scripts/prepare_host.sh
    dependencies: []
    rollback_command: echo "Host preparation rollback"
  - name: build_toolchain
    order: 4
    command: bash scripts/build_toolchain.sh
    dependencies: [download_sources]
    rollback_command: rm -rf /mnt/lfs/tools/*
```

### Adding New Stages

1. Add stage to YAML configuration
2. Create corresponding script
3. Specify dependencies and rollback
4. System automatically integrates the stage

## Self-Documentation

The system automatically documents:
- Every command executed
- All output and error messages
- Build configurations used
- Timing and performance data
- Repository state at build time

## Rollback and Recovery

- Each stage can define rollback commands
- Repository snapshots for configuration recovery
- Database maintains complete audit trail
- Easy restoration to previous working states

## Development

### Adding New Features

The modular architecture allows easy extension:

1. **New Build Stages**: Add to YAML configuration
2. **GUI Components**: Extend Qt interface in `src/gui/`
3. **Database Features**: Extend `DatabaseManager` class
4. **Repository Features**: Extend `RepositoryManager` class

### Testing

```bash
# Run with test database
export LFS_DB_NAME=lfs_builds_test
python3 main.py
```

## Security Notes

- Change default MySQL credentials in production
- Restrict database access to build system user
- Use secure file permissions for build scripts
- Regular backup of build database and repository

## Troubleshooting

### Common Issues

1. **MySQL Connection**: Check credentials in `db_manager.py`
2. **Permission Errors**: Ensure build scripts are executable
3. **GUI Issues**: Verify PyQt5 installation
4. **Repository Errors**: Check git configuration and permissions
5. **Download Failures**: System automatically tries multiple mirrors with performance grading; check network connectivity and mirror statistics in Package Manager
6. **Storage Space**: Use Settings to monitor disk usage; LFS builds require 15+ GB free space
7. **Removable Media**: Ensure USB/external drives are properly mounted before selection

### Storage Requirements

- **Minimum System**: 20 GB free space for complete LFS build
- **Repository Storage**: 1-2 GB for configurations, logs, and documents
- **Build Artifacts**: 15+ GB for sources, toolchain, and final system
- **Recommended**: Use external storage (32+ GB) for build artifacts

### Kernel Configuration

- **Interactive GUI**: Tabbed interface for configuring kernel build parameters
- **Context-Sensitive Help**: Hover over any option for detailed explanations and recommendations
- **Organized Categories**: General, Hardware, Networking, Filesystems, and Advanced options
- **LFS Optimized**: Sensible defaults for Linux From Scratch builds
- **Custom Options**: Free-form text area for advanced CONFIG parameters
- **Import/Export**: Load and save kernel .config files
- **Persistent Settings**: Configuration saved between sessions

### Package Discovery & Downloads

- **Dynamic Package Discovery**: Automatically discovers available packages from multiple sources
- **LFS Matrix Integration**: Priority downloads from `http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/`
- **Global Mirror Support**: Add base URLs that work for all packages (e.g., `https://ftp.gnu.org/gnu/`)
- **Per-Package Mirrors**: Custom mirrors for specific packages with priority ordering
- **Mirror Performance Grading**: Automatic tracking of success rates and download speeds
- **Intelligent Failover**: Tries mirrors in order: User mirrors → LFS Matrix → Global mirrors → Original URLs
- **Repository Caching**: Downloaded packages cached locally to avoid re-downloading
- **Package Manager**: Complete interface for pre-downloading, status checking, and mirror management
- **Real-time Updates**: Live repository view shows cached packages with verification status
- **wget Fallback**: Automatic fallback to wget for problematic downloads

### Mirror Management

- **Global Mirrors**: Add base URLs tried for all packages (Package Manager → Manage Mirrors → Global Mirrors)
- **Per-Package Mirrors**: Add specific URLs for individual packages with custom priority
- **Performance Tracking**: System automatically grades mirrors based on success rate and speed
- **Mirror Statistics**: View detailed performance data and reset grades when needed
- **Automatic Prioritization**: Best-performing mirrors are tried first for future downloadsport**: Add base URLs that work for all packages (e.g., `https://ftp.gnu.org/gnu/`)
- **Per-Package Mirrors**: Custom mirrors for specific packages with priority ordering
- **Mirror Performance Grading**: Automatic tracking of success rates and download speeds
- **Intelligent Failover**: Tries mirrors in order: User mirrors → LFS Matrix → Global mirrors → Original URLs
- **Repository Caching**: Downloaded packages cached locally to avoid re-downloading
- **Package Manager**: Complete interface for pre-downloading, status checking, and mirror management
- **Real-time Updates**: Live repository view shows cached packages with verification status

### Mirror Management

- **Global Mirrors**: Add base URLs tried for all packages (Package Manager → Manage Mirrors → Global Mirrors)
- **Per-Package Mirrors**: Add specific URLs for individual packages with custom priority
- **Performance Tracking**: System automatically grades mirrors based on success rate and speed
- **Mirror Statistics**: View detailed performance data and reset grades when needed
- **Automatic Prioritization**: Best-performing mirrors are tried first for future downloadsmscratch.org when needed
- **Mirror Performance Grading**: Tracks download success rates and speeds, automatically prioritizes best mirrors
- **Repository File Browser**: Live view of cached packages with file management and checksum verification
- **Package Manager Dialog**: Complete package status overview with pre-download and export capabilities

## Changelog

### Latest Updates

- **Dynamic Package Discovery**: Intelligent package detection from LFS Matrix, official LFS site, and hardcoded fallbacks
- **Mirror Grading System**: Automatic performance tracking and prioritization of download mirrors based on success rates and speed
- **Live Repository Updates**: Real-time file browser showing cached packages with context menu for file operations
- **Package Manager Enhancement**: Complete package status overview with pre-download capabilities and export functions
- **LFS Matrix Integration**: Priority downloads from LFS Matrix mirror with automatic version discovery
- **Checksum Verification**: Built-in MD5 verification for downloaded packages with visual feedback
- **Complete LFS Implementation**: Full Linux From Scratch 12.0 build automation with 10 stages from host preparation to bootloader installation
- **LFS Build Scripts**: Comprehensive shell scripts for each build stage with proper error handling and rollback support
- **MySQL Installation Script**: Added automated MySQL installation script (`src/database/install_mysql.sh`) for RHEL 9+ and Amazon Linux 2023
- **GPG Key Fix**: Updated MySQL installation script to handle GPG verification issues with Oracle MySQL packages
- **Installation Order**: Fixed installation sequence - pip dependencies first, then MySQL installation
- **MySQL Setup**: Added mysql_secure_installation step and password authentication for database setup
- **Credentials Storage**: MySQL root password stored in `.mysql_credentials` file (excluded from git)
- **Document Database**: Comprehensive document management system with full-text search, timestamps, and failure/success tracking
- **PyQt Compatibility**: Switched from PyQt6 to PyQt5 for better RHEL 9 compatibility
- **Enhanced Error Handling**: Improved foreign key constraint handling and build record managementpatibility**: Switched from PyQt6 to PyQt5 for better RHEL 9 compatibility
- **LFS Source Downloader**: Automated download system for all LFS 12.0 packages with MD5 verification and repository integration
- **Build Cancellation**: Added ability to cancel running builds and downloads with proper cleanup
- **Cleanup Utilities**: Added cleanup functionality for stuck builds via GUI and command line
- **GUI Improvements**: Replaced button layout with organized dropdown menu system for better space utilization
- **Enhanced Downloads**: Multi-mirror failover system with browser-like headers to avoid server blocking
- **Document Preservation**: Archive system preserves all build documents and logs for historical analysis
- **Removable Media Support**: Auto-detection of USB drives and external storage with real-time capacity monitoring
- **Storage Management**: Enhanced settings with disk space information and removable media selection
- **Database Schema Updates**: Automatic schema migration to support archived builds without data loss