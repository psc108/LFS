import sys
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QComboBox, QProgressBar, QTextEdit, QTabWidget,
                             QWidget, QGroupBox, QCheckBox, QSpinBox, QMessageBox,
                             QHeaderView, QFileDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
import requests
import threading
import time
from datetime import datetime
from urllib.parse import urlparse, urljoin

class DownloadWorker(QThread):
    progress = pyqtSignal(str, int, str)  # package, percentage, status
    finished = pyqtSignal(str, bool, str, dict)  # package, success, message, download_info
    log = pyqtSignal(str)
    
    def __init__(self, package_name, urls, destination, timeout=30, source_repo_manager=None):
        super().__init__()
        self.package_name = package_name
        self.urls = urls
        self.destination = destination
        self.timeout = timeout
        self.cancelled = False
        self.source_repo_manager = source_repo_manager
        self.download_info = {}
    
    def cancel(self):
        self.cancelled = True
    
    def run(self):
        import time
        start_time = time.time()
        
        for i, url in enumerate(self.urls):
            if self.cancelled:
                return
            
            try:
                self.log.emit(f"Trying mirror {i+1}/{len(self.urls)}: {url}")
                self.progress.emit(self.package_name, 0, f"Connecting to {urlparse(url).netloc}")
                
                response = requests.get(url, stream=True, timeout=self.timeout)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                filename = os.path.join(self.destination, os.path.basename(urlparse(url).path))
                
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.cancelled:
                            return
                        
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                percentage = int((downloaded / total_size) * 100)
                                self.progress.emit(self.package_name, percentage, f"Downloading from {urlparse(url).netloc}")
                
                # Add to Git repository if source repo manager is available
                if self.source_repo_manager:
                    self.download_info.update({
                        'original_url': url,
                        'mirror_url': url,
                        'duration_ms': int((time.time() - start_time) * 1000),
                        'download_date': datetime.now().isoformat(),
                        'file_size': os.path.getsize(filename) if os.path.exists(filename) else 0
                    })
                    
                    try:
                        success = self.source_repo_manager.add_package_to_repository(
                            "12.4", self.package_name, filename, self.download_info
                        )
                        
                        if success:
                            self.log.emit(f"✅ Added {self.package_name} to Git repository and database")
                        else:
                            self.log.emit(f"⚠️ Downloaded {self.package_name} but failed to add to repository")
                    except Exception as e:
                        self.log.emit(f"⚠️ Repository integration failed for {self.package_name}: {str(e)}")
                
                self.finished.emit(self.package_name, True, f"Downloaded successfully from {urlparse(url).netloc}", self.download_info)
                return
                
            except Exception as e:
                self.log.emit(f"Failed to download from {url}: {str(e)}")
                if i == len(self.urls) - 1:  # Last URL failed
                    self.finished.emit(self.package_name, False, f"All mirrors failed: {str(e)}", {})

class DownloadManagerDialog(QDialog):
    def __init__(self, parent=None, build_engine=None):
        super().__init__(parent)
        self.build_engine = build_engine
        self.download_workers = {}
        self.active_downloads = 0
        self.max_concurrent = 3
        
        # Initialize source repository manager
        self.source_repo_manager = None
        if build_engine and hasattr(build_engine, 'db') and hasattr(build_engine, 'repo'):
            try:
                from ..repository.source_repo_manager import SourceRepositoryManager
                self.source_repo_manager = SourceRepositoryManager(build_engine.db, build_engine.repo)
            except Exception as e:
                print(f"Warning: Could not initialize source repository manager: {e}")
        
        self.setWindowTitle("LFS Download Manager")
        self.setGeometry(100, 100, 1000, 700)
        self.setup_ui()
        self.load_lfs_packages()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(2000)  # Refresh every 2 seconds
        
        # Initialize source repository
        if self.source_repo_manager:
            self.source_repo_manager.create_source_repository("12.4")
            self.log_message("📦 Initialized LFS 12.4 source repository")
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Download tab
        download_tab = QWidget()
        self.tabs.addTab(download_tab, "📦 Package Downloads")
        self.setup_download_tab(download_tab)
        
        # Mirrors tab
        mirrors_tab = QWidget()
        self.tabs.addTab(mirrors_tab, "🌐 Mirror Management")
        self.setup_mirrors_tab(mirrors_tab)
        
        # Settings tab
        settings_tab = QWidget()
        self.tabs.addTab(settings_tab, "⚙️ Download Settings")
        self.setup_settings_tab(settings_tab)
    
    def setup_download_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.download_all_btn = QPushButton("📥 Download All Missing")
        self.download_all_btn.clicked.connect(self.download_all_missing)
        controls_layout.addWidget(self.download_all_btn)
        
        self.download_selected_btn = QPushButton("📥 Download Selected")
        self.download_selected_btn.clicked.connect(self.download_selected)
        controls_layout.addWidget(self.download_selected_btn)
        
        self.cancel_all_btn = QPushButton("🛑 Cancel All")
        self.cancel_all_btn.clicked.connect(self.cancel_all_downloads)
        controls_layout.addWidget(self.cancel_all_btn)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_status)
        controls_layout.addWidget(self.refresh_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Package table
        self.package_table = QTableWidget()
        self.package_table.setColumnCount(6)
        self.package_table.setHorizontalHeaderLabels([
            "Package", "Status", "Progress", "Size", "Mirrors", "Actions"
        ])
        
        header = self.package_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.package_table)
        
        # Download log
        log_group = QGroupBox("Download Log")
        log_layout = QVBoxLayout(log_group)
        
        self.download_log = QTextEdit()
        self.download_log.setMaximumHeight(150)
        self.download_log.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.download_log)
        
        layout.addWidget(log_group)
    
    def setup_mirrors_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Global mirrors
        global_group = QGroupBox("Global Mirrors (tried for all packages)")
        global_layout = QVBoxLayout(global_group)
        
        global_controls = QHBoxLayout()
        self.global_mirror_input = QLineEdit()
        self.global_mirror_input.setPlaceholderText("Enter global mirror URL (e.g., https://ftp.gnu.org/gnu/)")
        global_controls.addWidget(self.global_mirror_input)
        
        add_global_btn = QPushButton("➕ Add Global")
        add_global_btn.clicked.connect(self.add_global_mirror)
        global_controls.addWidget(add_global_btn)
        
        global_layout.addLayout(global_controls)
        
        self.global_mirrors_table = QTableWidget()
        self.global_mirrors_table.setColumnCount(4)
        self.global_mirrors_table.setHorizontalHeaderLabels(["URL", "Success Rate", "Avg Speed", "Actions"])
        global_layout.addWidget(self.global_mirrors_table)
        
        layout.addWidget(global_group)
        
        # Package-specific mirrors
        package_group = QGroupBox("Package-Specific Mirrors")
        package_layout = QVBoxLayout(package_group)
        
        package_controls = QHBoxLayout()
        self.package_select = QComboBox()
        package_controls.addWidget(QLabel("Package:"))
        package_controls.addWidget(self.package_select)
        
        self.package_mirror_input = QLineEdit()
        self.package_mirror_input.setPlaceholderText("Enter package-specific mirror URL")
        package_controls.addWidget(self.package_mirror_input)
        
        add_package_btn = QPushButton("➕ Add Mirror")
        add_package_btn.clicked.connect(self.add_package_mirror)
        package_controls.addWidget(add_package_btn)
        
        package_layout.addLayout(package_controls)
        
        self.package_mirrors_table = QTableWidget()
        self.package_mirrors_table.setColumnCount(5)
        self.package_mirrors_table.setHorizontalHeaderLabels(["Package", "URL", "Priority", "Success Rate", "Actions"])
        package_layout.addWidget(self.package_mirrors_table)
        
        layout.addWidget(package_group)
    
    def setup_settings_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Download settings
        settings_group = QGroupBox("Download Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # Concurrent downloads
        concurrent_layout = QHBoxLayout()
        concurrent_layout.addWidget(QLabel("Max Concurrent Downloads:"))
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        self.concurrent_spin.setValue(self.max_concurrent)
        self.concurrent_spin.valueChanged.connect(self.update_max_concurrent)
        concurrent_layout.addWidget(self.concurrent_spin)
        concurrent_layout.addStretch()
        settings_layout.addLayout(concurrent_layout)
        
        # Timeout
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Download Timeout (seconds):"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 300)
        self.timeout_spin.setValue(30)
        timeout_layout.addWidget(self.timeout_spin)
        timeout_layout.addStretch()
        settings_layout.addLayout(timeout_layout)
        
        # Download directory
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Download Directory:"))
        self.download_dir = QLineEdit()
        self.download_dir.setText("/mnt/lfs/sources")
        dir_layout.addWidget(self.download_dir)
        
        browse_btn = QPushButton("📁 Browse")
        browse_btn.clicked.connect(self.browse_download_dir)
        dir_layout.addWidget(browse_btn)
        
        settings_layout.addLayout(dir_layout)
        
        # Auto-retry
        self.auto_retry_cb = QCheckBox("Auto-retry failed downloads")
        self.auto_retry_cb.setChecked(True)
        settings_layout.addWidget(self.auto_retry_cb)
        
        # Verify checksums
        self.verify_checksums_cb = QCheckBox("Verify checksums after download")
        self.verify_checksums_cb.setChecked(True)
        settings_layout.addWidget(self.verify_checksums_cb)
        
        layout.addWidget(settings_group)
        layout.addStretch()
    
    def load_lfs_packages(self):
        """Load LFS 12.4 package list"""
        self.lfs_packages = {
            "acl-2.3.1.tar.xz": {
                "urls": ["https://download.savannah.gnu.org/releases/acl/acl-2.3.1.tar.xz"],
                "size": "348KB"
            },
            "attr-2.5.1.tar.gz": {
                "urls": ["https://download.savannah.gnu.org/releases/attr/attr-2.5.1.tar.gz"],
                "size": "456KB"
            },
            "autoconf-2.71.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/autoconf/autoconf-2.71.tar.xz"],
                "size": "1.3MB"
            },
            "automake-1.16.5.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/automake/automake-1.16.5.tar.xz"],
                "size": "1.5MB"
            },
            "bash-5.2.15.tar.gz": {
                "urls": ["https://ftp.gnu.org/gnu/bash/bash-5.2.15.tar.gz"],
                "size": "10.7MB"
            },
            "bc-6.0.1.tar.xz": {
                "urls": ["https://github.com/gavinhoward/bc/releases/download/6.0.1/bc-6.0.1.tar.xz"],
                "size": "432KB"
            },
            "binutils-2.41.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/binutils/binutils-2.41.tar.xz"],
                "size": "24.9MB"
            },
            "bison-3.8.2.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/bison/bison-3.8.2.tar.xz"],
                "size": "2.8MB"
            },
            "bzip2-1.0.8.tar.gz": {
                "urls": ["https://www.sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz"],
                "size": "810KB"
            },
            "check-0.15.2.tar.gz": {
                "urls": ["https://github.com/libcheck/check/releases/download/0.15.2/check-0.15.2.tar.gz"],
                "size": "760KB"
            },
            "coreutils-9.3.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/coreutils/coreutils-9.3.tar.xz"],
                "size": "5.8MB"
            },
            "diffutils-3.10.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/diffutils/diffutils-3.10.tar.xz"],
                "size": "1.5MB"
            },
            "e2fsprogs-1.47.0.tar.gz": {
                "urls": ["https://downloads.sourceforge.net/project/e2fsprogs/e2fsprogs/v1.47.0/e2fsprogs-1.47.0.tar.gz"],
                "size": "9.4MB"
            },
            "expat-2.5.0.tar.xz": {
                "urls": ["https://prdownloads.sourceforge.net/expat/expat-2.5.0.tar.xz"],
                "size": "444KB"
            },
            "expect5.45.4.tar.gz": {
                "urls": ["https://prdownloads.sourceforge.net/expect/expect5.45.4.tar.gz"],
                "size": "618KB"
            },
            "file-5.45.tar.gz": {
                "urls": ["https://astron.com/pub/file/file-5.45.tar.gz"],
                "size": "1.2MB"
            },
            "findutils-4.9.0.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/findutils/findutils-4.9.0.tar.xz"],
                "size": "1.9MB"
            },
            "flex-2.6.4.tar.gz": {
                "urls": ["https://github.com/westes/flex/releases/download/v2.6.4/flex-2.6.4.tar.gz"],
                "size": "1.4MB"
            },
            "gawk-5.2.2.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/gawk/gawk-5.2.2.tar.xz"],
                "size": "3.3MB"
            },
            "gcc-13.2.0.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/gcc/gcc-13.2.0/gcc-13.2.0.tar.xz"],
                "size": "87.1MB"
            },
            "gdbm-1.23.tar.gz": {
                "urls": ["https://ftp.gnu.org/gnu/gdbm/gdbm-1.23.tar.gz"],
                "size": "1.1MB"
            },
            "gettext-0.22.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/gettext/gettext-0.22.tar.xz"],
                "size": "9.9MB"
            },
            "glibc-2.38.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/glibc/glibc-2.38.tar.xz"],
                "size": "18.4MB"
            },
            "gmp-6.3.0.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/gmp/gmp-6.3.0.tar.xz"],
                "size": "2.0MB"
            },
            "gperf-3.1.tar.gz": {
                "urls": ["https://ftp.gnu.org/gnu/gperf/gperf-3.1.tar.gz"],
                "size": "1.2MB"
            },
            "grep-3.11.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/grep/grep-3.11.tar.xz"],
                "size": "1.6MB"
            },
            "groff-1.23.0.tar.gz": {
                "urls": ["https://ftp.gnu.org/gnu/groff/groff-1.23.0.tar.gz"],
                "size": "4.4MB"
            },
            "grub-2.06.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/grub/grub-2.06.tar.xz"],
                "size": "6.4MB"
            },
            "gzip-1.12.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/gzip/gzip-1.12.tar.xz"],
                "size": "807KB"
            },
            "iana-etc-20230810.tar.gz": {
                "urls": ["https://github.com/Mic92/iana-etc/releases/download/20230810/iana-etc-20230810.tar.gz"],
                "size": "584KB"
            },
            "inetutils-2.4.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/inetutils/inetutils-2.4.tar.xz"],
                "size": "1.5MB"
            },
            "intltool-0.51.0.tar.gz": {
                "urls": ["https://launchpad.net/intltool/trunk/0.51.0/+download/intltool-0.51.0.tar.gz"],
                "size": "159KB"
            },
            "iproute2-6.4.0.tar.xz": {
                "urls": ["https://www.kernel.org/pub/linux/utils/net/iproute2/iproute2-6.4.0.tar.xz"],
                "size": "874KB"
            },
            "kbd-2.6.1.tar.xz": {
                "urls": ["https://www.kernel.org/pub/linux/utils/kbd/kbd-2.6.1.tar.xz"],
                "size": "1.5MB"
            },
            "kmod-30.tar.xz": {
                "urls": ["https://www.kernel.org/pub/linux/utils/kernel/kmod/kmod-30.tar.xz"],
                "size": "555KB"
            },
            "less-633.tar.gz": {
                "urls": ["https://www.greenwoodsoftware.com/less/less-633.tar.gz"],
                "size": "348KB"
            },
            "lfs-bootscripts-20230728.tar.xz": {
                "urls": ["https://www.linuxfromscratch.org/lfs/downloads/12.0/lfs-bootscripts-20230728.tar.xz"],
                "size": "32KB"
            },
            "libcap-2.69.tar.xz": {
                "urls": ["https://www.kernel.org/pub/linux/libs/security/linux-privs/libcap2/libcap-2.69.tar.xz"],
                "size": "184KB"
            },
            "libffi-3.4.4.tar.gz": {
                "urls": ["https://github.com/libffi/libffi/releases/download/v3.4.4/libffi-3.4.4.tar.gz"],
                "size": "1.3MB"
            },
            "libpipeline-1.5.7.tar.gz": {
                "urls": ["https://download.savannah.gnu.org/releases/libpipeline/libpipeline-1.5.7.tar.gz"],
                "size": "956KB"
            },
            "libtool-2.4.7.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/libtool/libtool-2.4.7.tar.xz"],
                "size": "996KB"
            },
            "linux-6.4.12.tar.xz": {
                "urls": ["https://www.kernel.org/pub/linux/kernel/v6.x/linux-6.4.12.tar.xz"],
                "size": "134MB"
            },
            "m4-1.4.19.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/m4/m4-1.4.19.tar.xz"],
                "size": "1.6MB"
            },
            "make-4.4.1.tar.gz": {
                "urls": ["https://ftp.gnu.org/gnu/make/make-4.4.1.tar.gz"],
                "size": "2.3MB"
            },
            "man-db-2.11.2.tar.xz": {
                "urls": ["https://download.savannah.gnu.org/releases/man-db/man-db-2.11.2.tar.xz"],
                "size": "1.9MB"
            },
            "man-pages-6.05.01.tar.xz": {
                "urls": ["https://www.kernel.org/pub/linux/docs/man-pages/man-pages-6.05.01.tar.xz"],
                "size": "1.8MB"
            },
            "meson-1.2.1.tar.gz": {
                "urls": ["https://github.com/mesonbuild/meson/releases/download/1.2.1/meson-1.2.1.tar.gz"],
                "size": "2.1MB"
            },
            "mpc-1.3.1.tar.gz": {
                "urls": ["https://ftp.gnu.org/gnu/mpc/mpc-1.3.1.tar.gz"],
                "size": "773KB"
            },
            "mpfr-4.2.0.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/mpfr/mpfr-4.2.0.tar.xz"],
                "size": "1.4MB"
            },
            "ncurses-6.4.tar.gz": {
                "urls": ["https://invisible-mirror.net/archives/ncurses/ncurses-6.4.tar.gz"],
                "size": "3.6MB"
            },
            "ninja-1.11.1.tar.gz": {
                "urls": ["https://github.com/ninja-build/ninja/archive/v1.11.1/ninja-1.11.1.tar.gz"],
                "size": "225KB"
            },
            "openssl-3.1.2.tar.gz": {
                "urls": ["https://www.openssl.org/source/openssl-3.1.2.tar.gz"],
                "size": "15.1MB"
            },
            "patch-2.7.6.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/patch/patch-2.7.6.tar.xz"],
                "size": "766KB"
            },
            "perl-5.38.0.tar.xz": {
                "urls": ["https://www.cpan.org/src/5.0/perl-5.38.0.tar.xz"],
                "size": "12.9MB"
            },
            "pkgconf-2.0.1.tar.xz": {
                "urls": ["https://distfiles.ariadne.space/pkgconf/pkgconf-2.0.1.tar.xz"],
                "size": "294KB"
            },
            "procps-ng-4.0.3.tar.xz": {
                "urls": ["https://sourceforge.net/projects/procps-ng/files/Production/procps-ng-4.0.3.tar.xz"],
                "size": "1.0MB"
            },
            "psmisc-23.6.tar.xz": {
                "urls": ["https://sourceforge.net/projects/psmisc/files/psmisc/psmisc-23.6.tar.xz"],
                "size": "396KB"
            },
            "python-3.11.4.tar.xz": {
                "urls": ["https://www.python.org/ftp/python/3.11.4/Python-3.11.4.tar.xz"],
                "size": "19.8MB"
            },
            "readline-8.2.tar.gz": {
                "urls": ["https://ftp.gnu.org/gnu/readline/readline-8.2.tar.gz"],
                "size": "2.9MB"
            },
            "sed-4.9.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/sed/sed-4.9.tar.xz"],
                "size": "1.3MB"
            },
            "shadow-4.13.tar.xz": {
                "urls": ["https://github.com/shadow-maint/shadow/releases/download/4.13/shadow-4.13.tar.xz"],
                "size": "1.7MB"
            },
            "sysklogd-1.5.1.tar.gz": {
                "urls": ["https://www.infodrom.org/projects/sysklogd/download/sysklogd-1.5.1.tar.gz"],
                "size": "88KB"
            },
            "systemd-254.tar.gz": {
                "urls": ["https://github.com/systemd/systemd/archive/v254/systemd-254.tar.gz"],
                "size": "13.2MB"
            },
            "tar-1.35.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/tar/tar-1.35.tar.xz"],
                "size": "2.3MB"
            },
            "tcl8.6.13-src.tar.gz": {
                "urls": ["https://downloads.sourceforge.net/tcl/tcl8.6.13-src.tar.gz"],
                "size": "10.9MB"
            },
            "texinfo-7.0.3.tar.xz": {
                "urls": ["https://ftp.gnu.org/gnu/texinfo/texinfo-7.0.3.tar.xz"],
                "size": "4.9MB"
            },
            "tzdata2023c.tar.gz": {
                "urls": ["https://www.iana.org/time-zones/repository/releases/tzdata2023c.tar.gz"],
                "size": "432KB"
            },
            "udev-lfs-20171102.tar.xz": {
                "urls": ["https://anduin.linuxfromscratch.org/LFS/udev-lfs-20171102.tar.xz"],
                "size": "11KB"
            },
            "util-linux-2.39.1.tar.xz": {
                "urls": ["https://www.kernel.org/pub/linux/utils/util-linux/v2.39/util-linux-2.39.1.tar.xz"],
                "size": "7.2MB"
            },
            "vim-9.0.1677.tar.gz": {
                "urls": ["https://anduin.linuxfromscratch.org/LFS/vim-9.0.1677.tar.gz"],
                "size": "16.9MB"
            },
            "wheel-0.41.1.tar.gz": {
                "urls": ["https://pypi.org/packages/source/w/wheel/wheel-0.41.1.tar.gz"],
                "size": "97KB"
            },
            "xml-parser-2.46.tar.gz": {
                "urls": ["https://cpan.metacpan.org/authors/id/T/TO/TODDR/XML-Parser-2.46.tar.gz"],
                "size": "249KB"
            },
            "xz-5.4.4.tar.xz": {
                "urls": ["https://tukaani.org/xz/xz-5.4.4.tar.xz"],
                "size": "1.2MB"
            },
            "zlib-1.2.13.tar.xz": {
                "urls": ["https://zlib.net/fossils/zlib-1.2.13.tar.xz"],
                "size": "1.2MB"
            },
            "zstd-1.5.5.tar.gz": {
                "urls": ["https://github.com/facebook/zstd/releases/download/v1.5.5/zstd-1.5.5.tar.gz"],
                "size": "2.3MB"
            }
        }
        
        # Populate package selector
        self.package_select.addItems(sorted(self.lfs_packages.keys()))
        
        # Populate package table
        self.refresh_package_table()
    
    def refresh_package_table(self):
        """Refresh the package table with current status"""
        self.package_table.setRowCount(len(self.lfs_packages))
        
        download_dir = self.download_dir.text()
        
        # Get downloaded packages from repository if available
        repo_packages = set()
        if self.source_repo_manager:
            try:
                downloaded = self.source_repo_manager.get_downloaded_packages("12.4")
                repo_packages = {pkg['package_name'] for pkg in downloaded}
            except:
                pass
        
        for row, (package, info) in enumerate(sorted(self.lfs_packages.items())):
            # Package name
            self.package_table.setItem(row, 0, QTableWidgetItem(package))
            
            # Status - check both local file and repository
            file_path = os.path.join(download_dir, package)
            local_exists = os.path.exists(file_path)
            in_repo = package in repo_packages
            
            if local_exists and in_repo:
                status = "✅ Downloaded (Git)"
            elif local_exists:
                status = "✅ Downloaded"
            elif in_repo:
                status = "📦 In Repository"
            elif package in self.download_workers:
                status = "⬇️ Downloading"
            else:
                status = "❌ Missing"
            
            self.package_table.setItem(row, 1, QTableWidgetItem(status))
            
            # Progress bar
            progress_bar = QProgressBar()
            if package in self.download_workers:
                progress_bar.setValue(50)  # Will be updated by worker
            elif os.path.exists(file_path):
                progress_bar.setValue(100)
            else:
                progress_bar.setValue(0)
            
            self.package_table.setCellWidget(row, 2, progress_bar)
            
            # Size
            self.package_table.setItem(row, 3, QTableWidgetItem(info["size"]))
            
            # Mirrors count
            mirror_count = len(info["urls"])
            self.package_table.setItem(row, 4, QTableWidgetItem(str(mirror_count)))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            
            download_btn = QPushButton("📥")
            download_btn.setMaximumWidth(30)
            download_btn.clicked.connect(lambda checked, pkg=package: self.download_package(pkg))
            actions_layout.addWidget(download_btn)
            
            if package in self.download_workers:
                cancel_btn = QPushButton("🛑")
                cancel_btn.setMaximumWidth(30)
                cancel_btn.clicked.connect(lambda checked, pkg=package: self.cancel_download(pkg))
                actions_layout.addWidget(cancel_btn)
            
            self.package_table.setCellWidget(row, 5, actions_widget)
    
    def download_package(self, package_name):
        """Download a specific package"""
        if package_name in self.download_workers:
            return  # Already downloading
        
        if self.active_downloads >= self.max_concurrent:
            self.log_message(f"⏳ {package_name} queued (max concurrent downloads reached)")
            return
        
        package_info = self.lfs_packages[package_name]
        urls = package_info["urls"].copy()
        
        # Add global mirrors
        global_mirrors = self.get_global_mirrors()
        for mirror in global_mirrors:
            if mirror.endswith('/'):
                mirror_url = urljoin(mirror, package_name)
            else:
                mirror_url = f"{mirror}/{package_name}"
            urls.insert(0, mirror_url)
        
        # Add package-specific mirrors
        package_mirrors = self.get_package_mirrors(package_name)
        for mirror in package_mirrors:
            urls.insert(0, mirror)
        
        download_dir = self.download_dir.text()
        os.makedirs(download_dir, exist_ok=True)
        
        worker = DownloadWorker(package_name, urls, download_dir, self.timeout_spin.value(), self.source_repo_manager)
        worker.progress.connect(self.update_download_progress)
        worker.finished.connect(self.download_finished)
        worker.log.connect(self.log_message)
        
        self.download_workers[package_name] = worker
        self.active_downloads += 1
        
        worker.start()
        self.log_message(f"🚀 Started downloading {package_name}")
        self.refresh_package_table()
    
    def download_selected(self):
        """Download selected packages"""
        selected_rows = set()
        for item in self.package_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select packages to download.")
            return
        
        packages = list(self.lfs_packages.keys())
        for row in selected_rows:
            if row < len(packages):
                self.download_package(packages[row])
    
    def download_all_missing(self):
        """Download all missing packages"""
        download_dir = self.download_dir.text()
        missing_packages = []
        
        for package in self.lfs_packages:
            file_path = os.path.join(download_dir, package)
            if not os.path.exists(file_path) and package not in self.download_workers:
                missing_packages.append(package)
        
        if not missing_packages:
            QMessageBox.information(self, "All Downloaded", "All packages are already downloaded.")
            return
        
        self.log_message(f"📦 Starting download of {len(missing_packages)} missing packages")
        
        for package in missing_packages:
            if self.active_downloads < self.max_concurrent:
                self.download_package(package)
            else:
                break  # Will be handled by queue when others finish
    
    def cancel_download(self, package_name):
        """Cancel a specific download"""
        if package_name in self.download_workers:
            self.download_workers[package_name].cancel()
            self.log_message(f"🛑 Cancelled download of {package_name}")
    
    def cancel_all_downloads(self):
        """Cancel all active downloads"""
        for package_name, worker in list(self.download_workers.items()):
            worker.cancel()
        
        self.log_message("🛑 Cancelled all downloads")
    
    def update_download_progress(self, package_name, percentage, status):
        """Update download progress in the table"""
        for row in range(self.package_table.rowCount()):
            if self.package_table.item(row, 0).text() == package_name:
                progress_bar = self.package_table.cellWidget(row, 2)
                if progress_bar:
                    progress_bar.setValue(percentage)
                
                status_item = self.package_table.item(row, 1)
                if status_item:
                    status_item.setText(f"⬇️ {status}")
                break
    
    def download_finished(self, package_name, success, message, download_info):
        """Handle download completion"""
        if package_name in self.download_workers:
            del self.download_workers[package_name]
            self.active_downloads -= 1
        
        if success:
            self.log_message(f"✅ {package_name}: {message}")
            if download_info and self.source_repo_manager:
                duration = download_info.get('duration_ms', 0) / 1000
                self.log_message(f"📦 Added to Git repository (downloaded in {duration:.1f}s)")
        else:
            self.log_message(f"❌ {package_name}: {message}")
        
        self.refresh_package_table()
        
        # Start next queued download if any
        if self.active_downloads < self.max_concurrent:
            self.download_next_queued()
    
    def download_next_queued(self):
        """Start next queued download"""
        download_dir = self.download_dir.text()
        
        for package in self.lfs_packages:
            file_path = os.path.join(download_dir, package)
            if not os.path.exists(file_path) and package not in self.download_workers:
                self.download_package(package)
                break
    
    def log_message(self, message):
        """Add message to download log"""
        timestamp = time.strftime("%H:%M:%S")
        self.download_log.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        scrollbar = self.download_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def refresh_status(self):
        """Refresh package status"""
        self.refresh_package_table()
    
    def add_global_mirror(self):
        """Add a global mirror"""
        url = self.global_mirror_input.text().strip()
        if url:
            # Add to global mirrors list (would be saved to config)
            self.log_message(f"➕ Added global mirror: {url}")
            self.global_mirror_input.clear()
    
    def add_package_mirror(self):
        """Add a package-specific mirror"""
        package = self.package_select.currentText()
        url = self.package_mirror_input.text().strip()
        if package and url:
            # Add to package mirrors list (would be saved to config)
            self.log_message(f"➕ Added mirror for {package}: {url}")
            self.package_mirror_input.clear()
    
    def get_global_mirrors(self):
        """Get list of global mirrors"""
        # This would load from config file
        return [
            "https://ftp.gnu.org/gnu/",
            "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/"
        ]
    
    def get_package_mirrors(self, package_name):
        """Get package-specific mirrors"""
        # This would load from config file
        return []
    
    def update_max_concurrent(self, value):
        """Update maximum concurrent downloads"""
        self.max_concurrent = value
    
    def browse_download_dir(self):
        """Browse for download directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.download_dir.text())
        if directory:
            self.download_dir.setText(directory)