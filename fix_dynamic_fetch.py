#!/usr/bin/env python3

import re

# Read the current downloader.py
with open('src/build/downloader.py', 'r') as f:
    content = f.read()

# Fix the dynamic fetch URLs to use 12.4 instead of 12.0
content = re.sub(
    r'wget_url = "https://www\.linuxfromscratch\.org/lfs/downloads/12\.0/wget-list"',
    'wget_url = "https://www.linuxfromscratch.org/lfs/downloads/12.4/wget-list"',
    content
)

content = re.sub(
    r'md5_url = "https://www\.linuxfromscratch\.org/lfs/downloads/12\.0/md5sums"',
    'md5_url = "https://www.linuxfromscratch.org/lfs/downloads/12.4/md5sums"',
    content
)

# Write the fixed content
with open('src/build/downloader.py', 'w') as f:
    f.write(content)

print("✅ Fixed dynamic fetch URLs to use LFS 12.4")