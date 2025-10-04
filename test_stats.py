#!/usr/bin/env python3

import sys
import os
sys.path.append('/home/scottp/IdeaProjects/LFS')

from src.database.db_manager import DatabaseManager
from src.repository.repo_manager import RepositoryManager
from src.build.downloader import LFSDownloader

def test_stats():
    print("Testing repository stats and cache detection...")
    
    # Initialize components
    db = DatabaseManager()
    repo = RepositoryManager(db)
    downloader = LFSDownloader(repo, db)
    
    # Test package list
    packages = downloader.get_package_list()
    print(f"📦 Total packages in list: {len(packages)}")
    
    # Test cached packages
    cached = downloader.get_cached_packages()
    print(f"📦 Cached packages found: {len(cached)}")
    
    if cached:
        print("Cached packages:")
        for pkg in cached[:5]:
            print(f"  - {pkg['package_name']} {pkg['version']}")
        if len(cached) > 5:
            print(f"  ... and {len(cached) - 5} more")
    
    # Test mirror stats
    print(f"📊 Mirror stats loaded: {len(downloader.mirror_stats)} domains")
    if downloader.mirror_stats:
        for domain, stats in list(downloader.mirror_stats.items())[:3]:
            grade = downloader.get_mirror_grade(domain)
            print(f"  - {domain}: grade {grade:.1f}, {stats['successes']} successes, {stats['failures']} failures")
    
    # Check sources directory
    sources_dir = repo.repo_path / "sources"
    if sources_dir.exists():
        files = list(sources_dir.iterdir())
        print(f"📁 Files in sources directory: {len(files)}")
        for f in files[:5]:
            if f.is_file():
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"  - {f.name} ({size_mb:.1f} MB)")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more")
    else:
        print("📁 Sources directory does not exist")

if __name__ == "__main__":
    test_stats()