# Linux From Scratch Build System

A native GUI build system for Linux From Scratch with MySQL backend, integrated version control, and comprehensive build documentation.

## Features

- **Native GUI**: PyQt6-based interface for RHEL 9/Amazon Linux 2023
- **MySQL Backend**: All build attempts logged to searchable database
- **Modular Architecture**: Separate, updateable build stages with rollback capability
- **Self-Documenting**: Automatic documentation of every build process
- **Git-Style Repository**: Built-in version control for build configurations
- **Searchable Documents**: Full-text search across all build logs and documents

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
sudo dnf install python3 python3-pip mysql-server git

# Start MySQL
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

### Setup

1. **Clone and install dependencies:**
```bash
git clone <repository>
cd LFS
pip3 install -r requirements.txt
```

2. **Setup MySQL database:**
```bash
sudo mysql < setup_database.sql
```

3. **Run the application:**
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
    rollback_command: bash scripts/cleanup_host.sh
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
3. **GUI Issues**: Verify PyQt6 installation
4. **Repository Errors**: Check git configuration and permissions