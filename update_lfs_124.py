#!/usr/bin/env python3

# Update to LFS 12.4 package list and correct URL

import sys
import os

# Read the downloader.py file
with open('/home/scottp/IdeaProjects/LFS/src/build/downloader.py', 'r') as f:
    content = f.read()

# Update LFS version and base URL
content = content.replace('self.lfs_version = "12.0"', 'self.lfs_version = "12.4"')
content = content.replace('self.base_url = "https://www.linuxfromscratch.org/lfs/downloads/12.0/"', 'self.base_url = "https://www.linuxfromscratch.org/lfs/downloads/12.4/"')

# Update LFS Matrix URL
old_lfs_matrix = 'base_url = "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4"'
new_lfs_matrix = 'base_url = "http://ftp.lfs-matrix.net/pub/lfs/lfs-packages/12.4"'

# Find and replace the hardcoded package list
old_packages_start = 'print("📋 Using fallback hardcoded package list")\n        # Fallback to hardcoded LFS 12.0 packages\n        packages = ['
old_packages_end = '        ]\n        return packages'

# New LFS 12.4 package list based on the provided data
new_packages = '''print("📋 Using fallback hardcoded package list")
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
        return packages'''

# Find the old package list and replace it
start_idx = content.find(old_packages_start)
if start_idx == -1:
    print("Could not find package list start")
    sys.exit(1)

end_idx = content.find(old_packages_end, start_idx)
if end_idx == -1:
    print("Could not find package list end")
    sys.exit(1)

# Replace the entire package list section
new_content = content[:start_idx] + new_packages + '\n        ' + content[end_idx:]

# Write back to file
with open('/home/scottp/IdeaProjects/LFS/src/build/downloader.py', 'w') as f:
    f.write(new_content)

print("✅ Updated to LFS 12.4 package list with correct URLs")