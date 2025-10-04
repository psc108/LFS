#!/usr/bin/env python3

# Read the current downloader.py
with open('src/build/downloader.py', 'r') as f:
    content = f.read()

# Add global mirror methods after the user mirror methods
global_mirror_methods = '''
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
'''

# Insert the global mirror methods before the reset_mirror_grade method
content = content.replace(
    '    def reset_mirror_grade(self, domain: str):',
    global_mirror_methods + '\n    def reset_mirror_grade(self, domain: str):'
)

# Update the download_package method to use global mirrors
old_urls_line = '        all_urls = user_mirrors + lfs_matrix_urls + [package["url"]] + mirror_urls if mirror_urls else user_mirrors + lfs_matrix_urls + [package["url"]]'
new_urls_line = '''        global_mirror_urls = self.get_global_mirror_urls(filename)
        all_urls = user_mirrors + lfs_matrix_urls + global_mirror_urls + [package["url"]] + mirror_urls if mirror_urls else user_mirrors + lfs_matrix_urls + global_mirror_urls + [package["url"]]'''

content = content.replace(old_urls_line, new_urls_line)

# Write the updated content
with open('src/build/downloader.py', 'w') as f:
    f.write(content)

print("✅ Added global mirror support to downloader")