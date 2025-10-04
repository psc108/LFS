#!/usr/bin/env python3

# Read the current downloader.py
with open('src/build/downloader.py', 'r') as f:
    content = f.read()

# Disable dynamic fetch by making it always return empty list
content = content.replace(
    'def fetch_dynamic_package_list(self) -> List[Dict]:',
    'def fetch_dynamic_package_list(self) -> List[Dict]:\n        """Fetch current LFS package list from official website - DISABLED"""\n        return []  # Force use of hardcoded list\n        \n    def fetch_dynamic_package_list_disabled(self) -> List[Dict]:'
)

# Write the fixed content
with open('src/build/downloader.py', 'w') as f:
    f.write(content)

print("✅ Disabled dynamic fetch - will use hardcoded LFS 12.4 list only")