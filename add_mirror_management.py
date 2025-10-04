#!/usr/bin/env python3

# Add user mirror management to downloader

import sys
import os

# Read the downloader.py file
with open('/home/scottp/IdeaProjects/LFS/src/build/downloader.py', 'r') as f:
    content = f.read()

# Add user mirror management methods after save_mirror_stats
addition = '''
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
        return user_mirrors.get(package_name, [])'''

# Insert after save_mirror_stats method
insert_point = content.find('    def record_mirror_success(self, url: str, download_time: float, file_size: int):')
if insert_point == -1:
    print("Could not find insertion point")
    sys.exit(1)

new_content = content[:insert_point] + addition + '\n    \n' + content[insert_point:]

# Update download_package method to use user mirrors
old_urls_section = '''        # Get all possible URLs with LFS Matrix as priority
        lfs_matrix_urls = self.get_lfs_matrix_urls(package["name"], filename)
        mirror_urls = self.get_mirror_urls(package["name"], filename)
        all_urls = lfs_matrix_urls + [package["url"]] + mirror_urls if mirror_urls else lfs_matrix_urls + [package["url"]]
        urls_to_try = self.sort_urls_by_performance(all_urls)'''

new_urls_section = '''        # Get all possible URLs with user mirrors as highest priority
        user_mirrors = self.get_user_mirrors(package["name"])
        lfs_matrix_urls = self.get_lfs_matrix_urls(package["name"], filename)
        mirror_urls = self.get_mirror_urls(package["name"], filename)
        all_urls = user_mirrors + lfs_matrix_urls + [package["url"]] + mirror_urls if mirror_urls else user_mirrors + lfs_matrix_urls + [package["url"]]
        urls_to_try = self.sort_urls_by_performance(all_urls)'''

new_content = new_content.replace(old_urls_section, new_urls_section)

# Write back to file
with open('/home/scottp/IdeaProjects/LFS/src/build/downloader.py', 'w') as f:
    f.write(new_content)

print("✅ Added user mirror management to downloader")