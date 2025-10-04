import requests
import hashlib
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple
import re
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

class LFSDownloader(QObject):
    package_cached = pyqtSignal(str, dict)  # package_name, package_info
    def __init__(self, repo_manager, db_manager):
        super().__init__()
        self.repo = repo_manager
        self.db = db_manager
        self.lfs_version = "12.4"
        self.base_url = "https://www.linuxfromscratch.org/lfs/downloads/12.4/"
        self.mirror_stats = self.load_mirror_stats()
        print(f"📊 Loaded mirror stats for {len(self.mirror_stats)} domains")
        
    def get_mirror_urls(self, package_name: str, filename: str) -> List[str]:
        """Get multiple mirror URLs for a package"""
        mirrors = {
            "binutils": [
                "https://sourceware.org/pub/binutils/releases/binutils-2.41.tar.xz",
                "https://ftp.gnu.org/gnu/binutils/binutils-2.41.tar.xz",
                "https://mirrors.kernel.org/gnu/binutils/binutils-2.41.tar.xz"
            ],
            "gcc": [
                "https://ftp.gnu.org/gnu/gcc/gcc-13.2.0/gcc-13.2.0.tar.xz",
                "https://mirrors.kernel.org/gnu/gcc/gcc-13.2.0/gcc-13.2.0.tar.xz",
                "https://gcc.gnu.org/releases/gcc-13.2.0/gcc-13.2.0.tar.xz"
            ],
            "linux": [
                "https://www.kernel.org/pub/linux/kernel/v6.x/linux-6.4.12.tar.xz",
                "https://mirrors.edge.kernel.org/pub/linux/kernel/v6.x/linux-6.4.12.tar.xz",
                "https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.4.12.tar.xz"
            ],
            "glibc": [
                "https://ftp.gnu.org/gnu/glibc/glibc-2.38.tar.xz",
                "https://mirrors.kernel.org/gnu/glibc/glibc-2.38.tar.xz",
                "https://ftpmirror.gnu.org/glibc/glibc-2.38.tar.xz"
            ],
            "Python": [
                "https://www.python.org/ftp/python/3.11.4/Python-3.11.4.tar.xz",
                "https://python.org/ftp/python/3.11.4/Python-3.11.4.tar.xz"
            ],
            "openssl": [
                "https://www.openssl.org/source/openssl-3.1.2.tar.gz",
                "https://github.com/openssl/openssl/archive/OpenSSL_1_1_1w.tar.gz"
            ],
            "vim": [
                "https://anduin.linuxfromscratch.org/LFS/vim-9.0.1677.tar.xz",
                "https://github.com/vim/vim/archive/v9.0.1677.tar.gz"
            ]
        }
        
        # Return specific mirrors if available, otherwise generate generic mirrors
        if package_name in mirrors:
            return mirrors[package_name]
        
        # Generic GNU mirrors for GNU packages
        gnu_packages = ['gmp', 'mpfr', 'mpc', 'sed', 'grep', 'bash', 'make', 'gawk', 'tar', 'gzip', 
                       'bison', 'gettext', 'autoconf', 'automake', 'libtool', 'texinfo', 'groff']
        if any(gnu_pkg in package_name.lower() for gnu_pkg in gnu_packages):
            pkg_name = package_name.lower()
            return [
                f"https://ftp.gnu.org/gnu/{pkg_name}/{filename}",
                f"https://mirrors.kernel.org/gnu/{pkg_name}/{filename}",
                f"https://ftpmirror.gnu.org/{pkg_name}/{filename}",
                f"https://mirror.us-midwest-1.nexcess.net/gnu/{pkg_name}/{filename}"
            ]
        
        # For packages not in specific mirrors, return empty list to use original URL only
        return []
        
        # Fallback to original URL
        return []
    
    def get_package_list(self) -> List[Dict]:
        """Get LFS package list - try dynamic fetch first, fallback to hardcoded"""
        # Try to fetch latest package list from LFS website
        dynamic_packages = self.fetch_dynamic_package_list()
        if dynamic_packages:
            print(f"📋 Using dynamic package list ({len(dynamic_packages)} packages)")
            return dynamic_packages
        
        print("📋 Using fallback hardcoded package list")
        # Fallback to hardcoded LFS 12.4 packages
        packages = [
            {"name": "Python", "version": "3.13.7", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/Python-3.13.7.tar.xz", "md5": "unknown"},
            {"name": "XML-Parser", "version": "2.47", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/XML-Parser-2.47.tar.gz", "md5": "unknown"},
            {"name": "acl", "version": "2.3.2", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/acl-2.3.2.tar.xz", "md5": "unknown"},
            {"name": "attr", "version": "2.5.2", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/attr-2.5.2.tar.gz", "md5": "unknown"},
            {"name": "autoconf", "version": "2.72", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/autoconf-2.72.tar.xz", "md5": "unknown"},
            {"name": "automake", "version": "1.18.1", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/automake-1.18.1.tar.xz", "md5": "unknown"},
            {"name": "bash", "version": "5.3", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/bash-5.3.tar.gz", "md5": "unknown"},
            {"name": "bc", "version": "7.0.3", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/bc-7.0.3.tar.xz", "md5": "unknown"},
            {"name": "binutils", "version": "2.45", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/binutils-2.45.tar.xz", "md5": "unknown"},
            {"name": "bison", "version": "3.8.2", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/bison-3.8.2.tar.xz", "md5": "unknown"},
            {"name": "bzip2", "version": "1.0.8", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/bzip2-1.0.8.tar.gz", "md5": "unknown"},
            {"name": "coreutils", "version": "9.7", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/coreutils-9.7.tar.xz", "md5": "unknown"},
            {"name": "dbus", "version": "1.16.2", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/dbus-1.16.2.tar.xz", "md5": "unknown"},
            {"name": "dejagnu", "version": "1.6.3", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/dejagnu-1.6.3.tar.gz", "md5": "unknown"},
            {"name": "diffutils", "version": "3.12", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/diffutils-3.12.tar.xz", "md5": "unknown"},
            {"name": "e2fsprogs", "version": "1.47.3", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/e2fsprogs-1.47.3.tar.gz", "md5": "unknown"},
            {"name": "elfutils", "version": "0.193", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/elfutils-0.193.tar.bz2", "md5": "unknown"},
            {"name": "expat", "version": "2.7.1", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/expat-2.7.1.tar.xz", "md5": "unknown"},
            {"name": "expect", "version": "5.45.4", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/expect5.45.4.tar.gz", "md5": "unknown"},
            {"name": "file", "version": "5.46", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/file-5.46.tar.gz", "md5": "unknown"},
            {"name": "findutils", "version": "4.10.0", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/findutils-4.10.0.tar.xz", "md5": "unknown"},
            {"name": "flex", "version": "2.6.4", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/flex-2.6.4.tar.gz", "md5": "unknown"},
            {"name": "flit_core", "version": "3.12.0", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/flit_core-3.12.0.tar.gz", "md5": "unknown"},
            {"name": "gawk", "version": "5.3.2", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/gawk-5.3.2.tar.xz", "md5": "unknown"},
            {"name": "gcc", "version": "15.2.0", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/gcc-15.2.0.tar.xz", "md5": "unknown"},
            {"name": "gdbm", "version": "1.26", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/gdbm-1.26.tar.gz", "md5": "unknown"},
            {"name": "gettext", "version": "0.26", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/gettext-0.26.tar.xz", "md5": "unknown"},
            {"name": "glibc", "version": "2.42", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/glibc-2.42.tar.xz", "md5": "unknown"},
            {"name": "gmp", "version": "6.3.0", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/gmp-6.3.0.tar.xz", "md5": "unknown"},
            {"name": "gperf", "version": "3.3", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/gperf-3.3.tar.gz", "md5": "unknown"},
            {"name": "grep", "version": "3.12", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/grep-3.12.tar.xz", "md5": "unknown"},
            {"name": "groff", "version": "1.23.0", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/groff-1.23.0.tar.gz", "md5": "unknown"},
            {"name": "grub", "version": "2.12", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/grub-2.12.tar.xz", "md5": "unknown"},
            {"name": "gzip", "version": "1.14", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/gzip-1.14.tar.xz", "md5": "unknown"},
            {"name": "iana-etc", "version": "20250807", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/iana-etc-20250807.tar.gz", "md5": "unknown"},
            {"name": "inetutils", "version": "2.6", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/inetutils-2.6.tar.xz", "md5": "unknown"},
            {"name": "intltool", "version": "0.51.0", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/intltool-0.51.0.tar.gz", "md5": "unknown"},
            {"name": "iproute2", "version": "6.16.0", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/iproute2-6.16.0.tar.xz", "md5": "unknown"},
            {"name": "jinja2", "version": "3.1.6", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/jinja2-3.1.6.tar.gz", "md5": "unknown"},
            {"name": "kbd", "version": "2.8.0", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/kbd-2.8.0.tar.xz", "md5": "unknown"},
            {"name": "kmod", "version": "34.2", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/kmod-34.2.tar.xz", "md5": "unknown"},
            {"name": "less", "version": "679", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/less-679.tar.gz", "md5": "unknown"},
            {"name": "lfs-bootscripts", "version": "20240825", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/lfs-bootscripts-20240825.tar.xz", "md5": "unknown"},
            {"name": "libcap", "version": "2.76", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/libcap-2.76.tar.xz", "md5": "unknown"},
            {"name": "libffi", "version": "3.5.2", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/libffi-3.5.2.tar.gz", "md5": "unknown"},
            {"name": "libpipeline", "version": "1.5.8", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/libpipeline-1.5.8.tar.gz", "md5": "unknown"},
            {"name": "libtool", "version": "2.5.4", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/libtool-2.5.4.tar.xz", "md5": "unknown"},
            {"name": "libxcrypt", "version": "4.4.38", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/libxcrypt-4.4.38.tar.xz", "md5": "unknown"},
            {"name": "linux", "version": "6.16.1", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/linux-6.16.1.tar.xz", "md5": "unknown"},
            {"name": "lz4", "version": "1.10.0", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/lz4-1.10.0.tar.gz", "md5": "unknown"},
            {"name": "m4", "version": "1.4.20", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/m4-1.4.20.tar.xz", "md5": "unknown"},
            {"name": "make", "version": "4.4.1", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/make-4.4.1.tar.gz", "md5": "unknown"},
            {"name": "man-db", "version": "2.13.1", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/man-db-2.13.1.tar.xz", "md5": "unknown"},
            {"name": "man-pages", "version": "6.15", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/man-pages-6.15.tar.xz", "md5": "unknown"},
            {"name": "markupsafe", "version": "3.0.2", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/markupsafe-3.0.2.tar.gz", "md5": "unknown"},
            {"name": "meson", "version": "1.8.3", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/meson-1.8.3.tar.gz", "md5": "unknown"},
            {"name": "mpc", "version": "1.3.1", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/mpc-1.3.1.tar.gz", "md5": "unknown"},
            {"name": "mpfr", "version": "4.2.2", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/mpfr-4.2.2.tar.xz", "md5": "unknown"},
            {"name": "ncurses", "version": "6.5-20250809", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/ncurses-6.5-20250809.tgz", "md5": "unknown"},
            {"name": "ninja", "version": "1.13.1", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/ninja-1.13.1.tar.gz", "md5": "unknown"},
            {"name": "openssl", "version": "3.5.2", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/openssl-3.5.2.tar.gz", "md5": "unknown"},
            {"name": "packaging", "version": "25.0", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/packaging-25.0.tar.gz", "md5": "unknown"},
            {"name": "patch", "version": "2.8", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/patch-2.8.tar.xz", "md5": "unknown"},
            {"name": "perl", "version": "5.42.0", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/perl-5.42.0.tar.xz", "md5": "unknown"},
            {"name": "pkgconf", "version": "2.5.1", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/pkgconf-2.5.1.tar.xz", "md5": "unknown"},
            {"name": "procps-ng", "version": "4.0.5", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/procps-ng-4.0.5.tar.xz", "md5": "unknown"},
            {"name": "psmisc", "version": "23.7", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/psmisc-23.7.tar.xz", "md5": "unknown"},
            {"name": "readline", "version": "8.3", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/readline-8.3.tar.gz", "md5": "unknown"},
            {"name": "sed", "version": "4.9", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/sed-4.9.tar.xz", "md5": "unknown"},
            {"name": "setuptools", "version": "80.9.0", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/setuptools-80.9.0.tar.gz", "md5": "unknown"},
            {"name": "shadow", "version": "4.18.0", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/shadow-4.18.0.tar.xz", "md5": "unknown"},
            {"name": "sysklogd", "version": "2.7.2", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/sysklogd-2.7.2.tar.gz", "md5": "unknown"},
            {"name": "systemd", "version": "257.8", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/systemd-257.8.tar.gz", "md5": "unknown"},
            {"name": "sysvinit", "version": "3.14", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/sysvinit-3.14.tar.xz", "md5": "unknown"},
            {"name": "tar", "version": "1.35", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/tar-1.35.tar.xz", "md5": "unknown"},
            {"name": "tcl", "version": "8.6.16", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/tcl8.6.16-src.tar.gz", "md5": "unknown"},
            {"name": "texinfo", "version": "7.2", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/texinfo-7.2.tar.xz", "md5": "unknown"},
            {"name": "tzdata", "version": "2025b", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/tzdata2025b.tar.gz", "md5": "unknown"},
            {"name": "udev-lfs", "version": "20230818", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/udev-lfs-20230818.tar.xz", "md5": "unknown"},
            {"name": "util-linux", "version": "2.41.1", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/util-linux-2.41.1.tar.xz", "md5": "unknown"},
            {"name": "vim", "version": "9.1.1629", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/vim-9.1.1629.tar.gz", "md5": "unknown"},
            {"name": "wheel", "version": "0.46.1", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/wheel-0.46.1.tar.gz", "md5": "unknown"},
            {"name": "xz", "version": "5.8.1", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/xz-5.8.1.tar.xz", "md5": "unknown"},
            {"name": "zlib", "version": "1.3.1", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/zlib-1.3.1.tar.gz", "md5": "unknown"},
            {"name": "zstd", "version": "1.5.7", "url": "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4/zstd-1.5.7.tar.gz", "md5": "unknown"}
        ]
        return packages
    def fetch_dynamic_package_list(self) -> List[Dict]:
        """Fetch current LFS package list from official website - DISABLED"""
        return []  # Force use of hardcoded list
        
    def fetch_dynamic_package_list_disabled(self) -> List[Dict]:
        """Fetch current LFS package list from official website"""
        try:
            # Try to fetch from LFS wget-list and md5sums
            wget_url = "https://www.linuxfromscratch.org/lfs/downloads/12.0/wget-list"
            md5_url = "https://www.linuxfromscratch.org/lfs/downloads/12.0/md5sums"
            
            wget_response = requests.get(wget_url, timeout=15)
            md5_response = requests.get(md5_url, timeout=15)
            
            if wget_response.status_code == 200 and md5_response.status_code == 200:
                return self.parse_lfs_lists(wget_response.text, md5_response.text)
                
        except Exception as e:
            print(f"Could not fetch dynamic package list: {e}")
        
        return []
    
    def parse_lfs_lists(self, wget_content: str, md5_content: str) -> List[Dict]:
        """Parse wget-list and md5sums to create package list"""
        packages = []
        
        # Parse URLs from wget-list
        urls = [line.strip() for line in wget_content.strip().split('\n') if line.strip()]
        
        # Parse MD5 checksums
        md5_map = {}
        for line in md5_content.strip().split('\n'):
            if line.strip():
                parts = line.strip().split()
                if len(parts) >= 2:
                    md5_hash = parts[0]
                    filename = parts[1]
                    md5_map[filename] = md5_hash
        
        # Create package entries
        for url in urls:
            filename = url.split('/')[-1]
            
            # Extract package name and version
            name_match = re.match(r'^([a-zA-Z][a-zA-Z0-9_-]*?)-([0-9].*?)\.(tar\.|tgz)', filename)
            if name_match:
                name = name_match.group(1)
                version = name_match.group(2)
            else:
                # Fallback parsing
                base_name = filename.split('.tar')[0]
                parts = base_name.split('-')
                if len(parts) >= 2:
                    name = '-'.join(parts[:-1])
                    version = parts[-1]
                else:
                    name = base_name
                    version = "unknown"
            
            md5_hash = md5_map.get(filename, "unknown")
            
            packages.append({
                "name": name,
                "version": version,
                "url": url,
                "md5": md5_hash
            })
        
        return packages
    
    def download_package(self, package: Dict, build_id: str = None) -> Tuple[bool, str]:
        """Download a single package with verification and mirror failover"""
        sources_dir = self.repo.repo_path / "sources"
        sources_dir.mkdir(exist_ok=True)
        
        filename = package["url"].split("/")[-1]
        filepath = sources_dir / filename
        
        # First check repository cache
        if filepath.exists():
            if self.verify_checksum(filepath, package["md5"]):
                if build_id:
                    self.db.add_document(
                        build_id, 'log', f'Cache Hit: {filename}',
                        f"Found {package['name']} {package['version']} in repository cache\nPath: {filepath}\nSize: {filepath.stat().st_size} bytes\nSkipped download from internet",
                        {'package': package['name'], 'version': package['version'], 'cached': True}
                    )
                return True, f"Package {filename} found in repository cache and verified"
            else:
                # Remove corrupted cached file
                filepath.unlink()
                if build_id:
                    self.db.add_document(
                        build_id, 'log', f'Cache Miss: {filename}',
                        f"Cached file {filename} failed checksum verification - removed and will re-download",
                        {'package': package['name'], 'corrupted_cache': True}
                    )
        
        # Get all possible URLs with user mirrors as highest priority
        user_mirrors = self.get_user_mirrors(package["name"])
        lfs_matrix_urls = self.get_lfs_matrix_urls(package["name"], filename)
        mirror_urls = self.get_mirror_urls(package["name"], filename)
        global_mirror_urls = self.get_global_mirror_urls(filename)
        all_urls = user_mirrors + lfs_matrix_urls + global_mirror_urls + [package["url"]] + mirror_urls if mirror_urls else user_mirrors + lfs_matrix_urls + global_mirror_urls + [package["url"]]
        urls_to_try = self.sort_urls_by_performance(all_urls)
        
        last_error = ""
        for i, url in enumerate(urls_to_try):
            try:
                print(f"Downloading {package['name']} from {url} (attempt {i+1}/{len(urls_to_try)})")
                
                if build_id:
                    self.db.add_document(
                        build_id, 'log', f'Download Attempt {i+1}: {package["name"]}',
                        f"Attempting to download {package['name']} {package['version']}\nURL: {url}\nExpected MD5: {package['md5']}\nTarget file: {filepath}",
                        {'package': package['name'], 'version': package['version'], 'url': url, 'attempt': i+1}
                    )
                
                # Download with browser-like headers to avoid blocking
                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
                
                session = requests.Session()
                session.headers.update(headers)
                
                start_time = time.time()
                response = session.get(url, stream=True, timeout=60, allow_redirects=True)
                response.raise_for_status()
                download_time = time.time() - start_time
                
                print(f"📊 Downloaded from {url.split('/')[2]} in {download_time:.1f}s")
                
                # Download to temporary file first
                temp_filepath = filepath.with_suffix('.tmp')
                with open(temp_filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Verify checksum before moving to final location
                if self.verify_checksum(temp_filepath, package["md5"]):
                    temp_filepath.rename(filepath)
                    
                    # Record successful download for mirror grading
                    self.record_mirror_success(url, download_time, filepath.stat().st_size)
                    
                    # Add to repository for future use
                    cache_info = self.add_to_repository_cache(filepath, package)
                    
                    # Emit signal for live repository updates
                    if cache_info:
                        self.package_cached.emit(package['name'], cache_info)
                    
                    if build_id:
                        self.db.add_document(
                            build_id, 'log', f'Downloaded: {filename}',
                            f"Successfully downloaded {package['name']} {package['version']}\nURL: {url}\nSize: {filepath.stat().st_size} bytes\nDownload time: {download_time:.1f}s\nAttempt: {i+1}/{len(urls_to_try)}\nAdded to repository cache for future builds",
                            {'package': package['name'], 'version': package['version'], 'successful_url': url, 'download_time': download_time, 'cached': True}
                        )
                    return True, f"Successfully downloaded {filename} from mirror {i+1} and cached"
                else:
                    temp_filepath.unlink()
                    last_error = f"Checksum verification failed for {filename} from {url}"
                    continue
                    
            except Exception as e:
                last_error = f"Failed to download {package['name']} from {url}: {str(e)}"
                print(f"❌ Download failed from {url.split('/')[2]}: {e}")
                # Record failed attempt for mirror grading
                self.record_mirror_failure(url)
                print(f"📊 Mirror {url.split('/')[2]} failure recorded (grade: {self.get_mirror_grade(url.split('/')[2]):.1f})")
                # Small delay before trying next mirror
                time.sleep(2)
                continue
        
        # Try wget as final fallback on first URL
        print(f"🔄 Trying wget fallback for {package['name']}")
        if urls_to_try:
            temp_filepath = filepath.with_suffix('.wget.tmp')
            if self.download_with_wget(urls_to_try[0], temp_filepath):
                # Verify checksum
                if self.verify_checksum(temp_filepath, package["md5"]):
                    temp_filepath.rename(filepath)
                    
                    # Add to repository cache
                    cache_info = self.add_to_repository_cache(filepath, package)
                    if cache_info:
                        self.package_cached.emit(package['name'], cache_info)
                    
                    if build_id:
                        self.db.add_document(
                            build_id, 'log', f'Downloaded via wget: {filename}',
                            f"Successfully downloaded {package['name']} {package['version']} using wget fallback\nURL: {urls_to_try[0]}\nSize: {filepath.stat().st_size} bytes\nAdded to repository cache",
                            {'package': package['name'], 'version': package['version'], 'method': 'wget', 'cached': True}
                        )
                    return True, f"Successfully downloaded {filename} via wget fallback"
                else:
                    temp_filepath.unlink()
                    last_error = f"wget download failed checksum verification"
        
        # All methods failed
        if build_id:
            self.db.add_document(
                build_id, 'error', f'All Downloads Failed: {package["name"]}',
                f"Failed to download {package['name']} from all {len(urls_to_try)} sources and wget fallback\nLast error: {last_error}\nURLs tried: {', '.join(urls_to_try)}",
                {'package': package['name'], 'urls_tried': urls_to_try, 'total_attempts': len(urls_to_try), 'wget_attempted': True}
            )
        
        return False, f"Failed to download {package['name']} from all {len(urls_to_try)} sources and wget fallback. Last error: {last_error}"
    

    def download_with_wget(self, url: str, filepath: Path) -> bool:
        """Download using wget as fallback"""
        try:
            import subprocess
            
            # Use wget with retry and timeout options
            cmd = [
                'wget',
                '--tries=3',
                '--timeout=60',
                '--no-check-certificate',  # Some mirrors have cert issues
                '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                '-O', str(filepath),
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and filepath.exists():
                print(f"✅ wget successfully downloaded {filepath.name}")
                return True
            else:
                print(f"❌ wget failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ wget error: {e}")
            return False

    def verify_checksum(self, filepath: Path, expected_md5: str) -> bool:
        """Verify MD5 checksum of downloaded file"""
        try:
            if expected_md5 == "unknown":
                print(f"⚠ Skipping checksum verification for {filepath.name} (unknown MD5)")
                return True
                
            hash_md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            
            actual_md5 = hash_md5.hexdigest()
            if actual_md5 == expected_md5:
                print(f"✅ Checksum verified for {filepath.name}")
                return True
            else:
                print(f"❌ Checksum mismatch for {filepath.name}:")
                print(f"   Expected: {expected_md5}")
                print(f"   Actual:   {actual_md5}")
                return False
        except Exception as e:
            print(f"❌ Checksum verification error for {filepath.name}: {e}")
            return False
    
    def get_file_md5(self, filepath: Path) -> str:
        """Get MD5 checksum of file"""
        try:
            hash_md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return "unknown"
    
    def download_all_packages(self, build_id: str = None) -> Dict:
        """Download all LFS packages"""
        packages = self.get_package_list()
        results = {"success": [], "failed": [], "cached": []}
        
        # Log cache status
        cached_packages = self.get_cached_packages()
        if build_id and cached_packages:
            cache_summary = "\n".join([f"- {pkg['package_name']} {pkg['version']}" for pkg in cached_packages])
            self.db.add_document(
                build_id, 'log', 'Repository Cache Status',
                f"Found {len(cached_packages)} packages in repository cache:\n{cache_summary}",
                {'cached_count': len(cached_packages)}
            )
        
        for package in packages:
            success, message = self.download_package(package, build_id)
            if success:
                if "cache" in message.lower():
                    results["cached"].append({"package": package["name"], "message": message})
                else:
                    results["success"].append({"package": package["name"], "message": message})
            else:
                results["failed"].append({"package": package["name"], "error": message})
                if build_id:
                    self.db.add_document(
                        build_id, 'error', f'Download Failed: {package["name"]}',
                        message, {'package': package['name']}
                    )
        
        # Create wget-list for manual downloads if needed
        self.create_wget_list()
        
        if build_id:
            cached_count = len(results['cached'])
            download_count = len(results['success'])
            failed_count = len(results['failed'])
            
            summary = f"Package acquisition complete: {cached_count} from cache, {download_count} downloaded, {failed_count} failed"
            
            summary_content = summary
            if results['cached']:
                summary_content += f"\n\nFrom repository cache ({cached_count}):\n" + "\n".join([r["package"] for r in results["cached"]])
            if results['success']:
                summary_content += f"\n\nNewly downloaded ({download_count}):\n" + "\n".join([r["package"] for r in results["success"]])
            if results['failed']:
                summary_content += f"\n\nFailed downloads ({failed_count}):\n" + "\n".join([r["package"] for r in results["failed"]])
            
            self.db.add_document(
                build_id, 'summary', 'Package Acquisition Summary',
                summary_content,
                {'total_packages': len(packages), 'cached': cached_count, 'downloaded': download_count, 'failed': failed_count}
            )
        
        return results
    
    def create_wget_list(self):
        """Create wget-list file for manual downloads"""
        packages = self.get_package_list()
        wget_list_path = self.repo.repo_path / "sources" / "wget-list"
        
        with open(wget_list_path, 'w') as f:
            for package in packages:
                f.write(f"{package['url']}\n")
    
    def create_md5sums_file(self):
        """Create md5sums file for verification"""
        packages = self.get_package_list()
        md5sums_path = self.repo.repo_path / "sources" / "md5sums"
        
        with open(md5sums_path, 'w') as f:
            for package in packages:
                filename = package["url"].split("/")[-1]
                f.write(f"{package['md5']}  {filename}\n")
    
    def get_download_status(self) -> Dict:
        """Get status of downloaded packages"""
        packages = self.get_package_list()
        sources_dir = self.repo.repo_path / "sources"
        
        status = {"downloaded": [], "missing": [], "corrupted": []}
        
        for package in packages:
            filename = package["url"].split("/")[-1]
            filepath = sources_dir / filename
            
            if filepath.exists():
                if self.verify_checksum(filepath, package["md5"]):
                    status["downloaded"].append(package["name"])
                else:
                    status["corrupted"].append(package["name"])
            else:
                status["missing"].append(package["name"])
        
        return status
    
    def add_to_repository_cache(self, filepath: Path, package: Dict):
        """Add successfully downloaded file to repository cache"""
        try:
            # File is already in sources directory, just ensure it's tracked
            cache_info_file = filepath.parent / f"{filepath.name}.info"
            
            cache_info = {
                'package_name': package['name'],
                'version': package['version'],
                'url': package['url'],
                'md5': package['md5'],
                'downloaded_at': datetime.now().isoformat(),
                'file_size': filepath.stat().st_size
            }
            
            import json
            with open(cache_info_file, 'w') as f:
                json.dump(cache_info, f, indent=2)
                
            print(f"📦 Cached {package['name']} in repository for future builds")
            return cache_info
            
        except Exception as e:
            print(f"Warning: Could not cache package info: {e}")
            return None
    
    def get_cached_packages(self) -> List[Dict]:
        """Get list of packages available in repository cache"""
        sources_dir = self.repo.repo_path / "sources"
        cached_packages = []
        
        if not sources_dir.exists():
            return cached_packages
        
        # First, load packages with .info files
        for info_file in sources_dir.glob("*.info"):
            try:
                import json
                with open(info_file, 'r') as f:
                    cache_info = json.load(f)
                
                # Verify the actual file still exists and is valid
                package_file = info_file.with_suffix('')  # Remove .info extension
                if package_file.exists():
                    if self.verify_checksum(package_file, cache_info['md5']):
                        cached_packages.append(cache_info)
                    else:
                        # Remove corrupted cache
                        package_file.unlink()
                        info_file.unlink()
                        
            except Exception as e:
                print(f"Warning: Could not read cache info {info_file}: {e}")
        
        # Also check for files without .info (manual downloads or old cached files)
        if sources_dir.exists():
            all_packages = self.get_package_list()
            for file_path in sources_dir.iterdir():
                if file_path.is_file() and not file_path.name.endswith('.info'):
                    # Check if this file matches any required package
                    for pkg in all_packages:
                        expected_filename = pkg['url'].split('/')[-1]
                        if file_path.name == expected_filename:
                            # Verify checksum if possible
                            if self.verify_checksum(file_path, pkg['md5']):
                                # Check if already in cached_packages
                                already_cached = any(c['package_name'] == pkg['name'] for c in cached_packages)
                                if not already_cached:
                                    cache_info = {
                                        'package_name': pkg['name'],
                                        'version': pkg['version'],
                                        'url': pkg['url'],
                                        'md5': pkg['md5'],
                                        'downloaded_at': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                                        'file_size': file_path.stat().st_size
                                    }
                                    cached_packages.append(cache_info)
                                    # Create .info file for future reference
                                    try:
                                        info_file = file_path.with_suffix(file_path.suffix + '.info')
                                        with open(info_file, 'w') as f:
                                            json.dump(cache_info, f, indent=2)
                                    except:
                                        pass
                            break
        
        return cached_packages
    
    def load_mirror_stats(self) -> Dict:
        """Load mirror performance statistics"""
        stats_file = self.repo.repo_path / "mirror_stats.json"
        if stats_file.exists():
            try:
                import json
                with open(stats_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_mirror_stats(self):
        """Save mirror performance statistics"""
        stats_file = self.repo.repo_path / "mirror_stats.json"
        try:
            import json
            with open(stats_file, 'w') as f:
                json.dump(self.mirror_stats, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save mirror stats: {e}")
    

    def load_user_mirrors(self) -> Dict:
        """Load user-defined mirror priorities"""
        mirrors_file = self.repo.repo_path / "user_mirrors.json"
        if mirrors_file.exists():
            try:
                import json
                with open(mirrors_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_user_mirrors(self, user_mirrors: Dict):
        """Save user-defined mirror priorities"""
        mirrors_file = self.repo.repo_path / "user_mirrors.json"
        try:
            import json
            with open(mirrors_file, 'w') as f:
                json.dump(user_mirrors, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save user mirrors: {e}")
    
    def add_user_mirror(self, package_name: str, mirror_url: str, priority: int = 1):
        """Add user-defined mirror for a package"""
        user_mirrors = self.load_user_mirrors()
        if package_name not in user_mirrors:
            user_mirrors[package_name] = []
        
        # Insert at priority position
        user_mirrors[package_name].insert(priority - 1, mirror_url)
        self.save_user_mirrors(user_mirrors)
        print(f"Added user mirror for {package_name}: {mirror_url} (priority {priority})")
    
    def get_user_mirrors(self, package_name: str) -> List[str]:
        """Get user-defined mirrors for a package"""
        user_mirrors = self.load_user_mirrors()
        return user_mirrors.get(package_name, [])
    


    def load_global_mirrors(self) -> List[str]:
        """Load global mirrors that are tried for all packages"""
        mirrors_file = self.repo.repo_path / "global_mirrors.json"
        if mirrors_file.exists():
            try:
                import json
                with open(mirrors_file, 'r') as f:
                    data = json.load(f)
                    return data.get('mirrors', [])
            except:
                pass
        return []
    
    def save_global_mirrors(self, mirrors: List[str]):
        """Save global mirrors"""
        mirrors_file = self.repo.repo_path / "global_mirrors.json"
        try:
            import json
            with open(mirrors_file, 'w') as f:
                json.dump({'mirrors': mirrors}, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save global mirrors: {e}")
    
    def add_global_mirror(self, base_url: str):
        """Add a global mirror base URL"""
        mirrors = self.load_global_mirrors()
        if base_url not in mirrors:
            mirrors.append(base_url)
            self.save_global_mirrors(mirrors)
            print(f"Added global mirror: {base_url}")
    
    def get_global_mirror_urls(self, filename: str) -> List[str]:
        """Generate URLs from global mirrors for a filename"""
        global_mirrors = self.load_global_mirrors()
        urls = []
        for mirror in global_mirrors:
            # Ensure mirror ends with /
            if not mirror.endswith('/'):
                mirror += '/'
            urls.append(f"{mirror}{filename}")
        return urls

    def reset_mirror_grade(self, domain: str):
        """Reset mirror grade statistics"""
        if domain in self.mirror_stats:
            del self.mirror_stats[domain]
            self.save_mirror_stats()
            print(f"Reset grade for mirror: {domain}")
    
    def record_mirror_success(self, url: str, download_time: float, file_size: int):
        """Record successful download for mirror grading"""
        domain = url.split('/')[2]  # Extract domain
        if domain not in self.mirror_stats:
            self.mirror_stats[domain] = {'successes': 0, 'failures': 0, 'avg_speed': 0, 'total_bytes': 0}
        
        stats = self.mirror_stats[domain]
        speed = file_size / download_time if download_time > 0 else 0
        
        # Update running average speed
        total_downloads = stats['successes'] + 1
        stats['avg_speed'] = ((stats['avg_speed'] * stats['successes']) + speed) / total_downloads
        stats['successes'] += 1
        stats['total_bytes'] += file_size
        
        self.save_mirror_stats()
        print(f"📊 Mirror {domain}: {speed/1024/1024:.1f} MB/s (grade: {self.get_mirror_grade(domain):.1f})")
    
    def record_mirror_failure(self, url: str):
        """Record failed download for mirror grading"""
        domain = url.split('/')[2]
        if domain not in self.mirror_stats:
            self.mirror_stats[domain] = {'successes': 0, 'failures': 0, 'avg_speed': 0, 'total_bytes': 0}
        
        self.mirror_stats[domain]['failures'] += 1
        self.save_mirror_stats()
    
    def get_mirror_grade(self, domain: str) -> float:
        """Calculate mirror grade (0-100) based on success rate and speed"""
        if domain not in self.mirror_stats:
            return 50.0  # Neutral grade for unknown mirrors
        
        stats = self.mirror_stats[domain]
        total_attempts = stats['successes'] + stats['failures']
        if total_attempts == 0:
            return 50.0
        
        success_rate = stats['successes'] / total_attempts
        speed_score = min(stats['avg_speed'] / (1024 * 1024), 10) / 10  # Normalize to 0-1 (10 MB/s = max)
        
        # Grade: 70% success rate + 30% speed
        grade = (success_rate * 70) + (speed_score * 30)
        return grade
    
    def sort_urls_by_performance(self, urls: List[str]) -> List[str]:
        """Sort URLs by mirror performance grade (best first)"""
        def get_url_grade(url):
            domain = url.split('/')[2]
            return self.get_mirror_grade(domain)
        
        return sorted(urls, key=get_url_grade, reverse=True)
    
    def get_lfs_matrix_urls(self, package_name: str, filename: str) -> List[str]:
        """Get LFS Matrix URLs, trying dynamic discovery first"""
        base_url = "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4"
        urls = []
        
        # Try to discover actual files on LFS Matrix
        discovered_urls = self.discover_lfs_matrix_files(package_name, base_url)
        if discovered_urls:
            urls.extend(discovered_urls)
        
        # Fallback to exact filename
        urls.append(f"{base_url}/{filename}")
        
        return urls
    
    def discover_lfs_matrix_files(self, package_name: str, base_url: str) -> List[str]:
        """Dynamically discover available files for a package on LFS Matrix"""
        try:
            # Try to get directory listing
            response = requests.get(base_url, timeout=10)
            if response.status_code == 200:
                content = response.text
                
                # Look for files matching the package name
                import re
                base_name = package_name.lower()
                # Match package files (e.g., binutils-2.45.tar.xz)
                pattern = rf'{re.escape(base_name)}-[\d\.]+\.tar\.[xzgb2]+'
                matches = re.findall(pattern, content, re.IGNORECASE)
                
                if matches:
                    # Sort by version (newest first)
                    matches.sort(reverse=True)
                    return [f"{base_url}/{match}" for match in matches[:3]]  # Top 3 versions
                    
        except Exception as e:
            print(f"Could not discover LFS Matrix files for {package_name}: {e}")
        
        return []
        
        for info_file in sources_dir.glob("*.info"):
            try:
                import json
                with open(info_file, 'r') as f:
                    cache_info = json.load(f)
                
                # Verify the actual file still exists and is valid
                package_file = info_file.with_suffix('')  # Remove .info extension
                if package_file.exists():
                    if self.verify_checksum(package_file, cache_info['md5']):
                        cached_packages.append(cache_info)
                    else:
                        # Remove corrupted cache
                        package_file.unlink()
                        info_file.unlink()
                        
            except Exception as e:
                print(f"Warning: Could not read cache info {info_file}: {e}")
        
        # Also check for files without .info (manual downloads or old cached files)
        if sources_dir.exists():
            all_packages = self.get_package_list()
            for file_path in sources_dir.iterdir():
                if file_path.is_file() and not file_path.name.endswith('.info'):
                    # Check if this file matches any required package
                    for pkg in all_packages:
                        expected_filename = pkg['url'].split('/')[-1]
                        if file_path.name == expected_filename:
                            # Verify checksum if possible
                            if self.verify_checksum(file_path, pkg['md5']):
                                # Check if already in cached_packages
                                already_cached = any(c['package_name'] == pkg['name'] for c in cached_packages)
                                if not already_cached:
                                    cache_info = {
                                        'package_name': pkg['name'],
                                        'version': pkg['version'],
                                        'url': pkg['url'],
                                        'md5': pkg['md5'],
                                        'downloaded_at': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                                        'file_size': file_path.stat().st_size
                                    }
                                    cached_packages.append(cache_info)
                                    # Create .info file for future reference
                                    try:
                                        info_file = file_path.with_suffix(file_path.suffix + '.info')
                                        with open(info_file, 'w') as f:
                                            json.dump(cache_info, f, indent=2)
                                    except:
                                        pass
                            break
        
        return cached_packages