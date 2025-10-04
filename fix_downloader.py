#!/usr/bin/env python3

# Fix the malformed downloader.py file

import sys
import os

# Read the current broken file
with open('/home/scottp/IdeaProjects/LFS/src/build/downloader.py', 'r') as f:
    content = f.read()

# Find the problematic section and fix it
# Remove the duplicate lines and fix indentation
lines = content.split('\n')

# Find where the problem starts (around line 179)
fixed_lines = []
skip_until_method = False

for i, line in enumerate(lines):
    # Skip the malformed section
    if '                ]' in line and 'return packages' in lines[i+1] if i+1 < len(lines) else False:
        skip_until_method = True
        continue
    
    if skip_until_method and line.strip().startswith('def '):
        skip_until_method = False
    
    if not skip_until_method:
        fixed_lines.append(line)

# Write the fixed content
with open('/home/scottp/IdeaProjects/LFS/src/build/downloader.py', 'w') as f:
    f.write('\n'.join(fixed_lines))

print("✅ Fixed downloader.py syntax errors")