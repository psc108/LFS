#!/usr/bin/env python3

# Read the current downloader.py
with open('src/build/downloader.py', 'r') as f:
    content = f.read()

# Add wget fallback method after the download_package method
wget_method = '''
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
'''

# Insert the wget method before the verify_checksum method
content = content.replace(
    '    def verify_checksum(self, filepath: Path, expected_md5: str) -> bool:',
    wget_method + '\n    def verify_checksum(self, filepath: Path, expected_md5: str) -> bool:'
)

# Update the download_package method to use wget as final fallback
old_failure_section = '''        # All mirrors failed
        if build_id:
            self.db.add_document(
                build_id, 'error', f'All Downloads Failed: {package["name"]}',
                f"Failed to download {package['name']} from all {len(urls_to_try)} sources\\nLast error: {last_error}\\nURLs tried: {', '.join(urls_to_try)}",
                {'package': package['name'], 'urls_tried': urls_to_try, 'total_attempts': len(urls_to_try)}
            )
        
        return False, f"Failed to download {package['name']} from all {len(urls_to_try)} sources. Last error: {last_error}"'''

new_failure_section = '''        # Try wget as final fallback on first URL
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
                            f"Successfully downloaded {package['name']} {package['version']} using wget fallback\\nURL: {urls_to_try[0]}\\nSize: {filepath.stat().st_size} bytes\\nAdded to repository cache",
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
                f"Failed to download {package['name']} from all {len(urls_to_try)} sources and wget fallback\\nLast error: {last_error}\\nURLs tried: {', '.join(urls_to_try)}",
                {'package': package['name'], 'urls_tried': urls_to_try, 'total_attempts': len(urls_to_try), 'wget_attempted': True}
            )
        
        return False, f"Failed to download {package['name']} from all {len(urls_to_try)} sources and wget fallback. Last error: {last_error}"'''

content = content.replace(old_failure_section, new_failure_section)

# Write the updated content
with open('src/build/downloader.py', 'w') as f:
    f.write(content)

print("✅ Added wget fallback to downloader")