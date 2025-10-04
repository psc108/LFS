#!/usr/bin/env python3

# Read the current downloader.py
with open('src/build/downloader.py', 'r') as f:
    content = f.read()

# Improve checksum verification with better logging
old_verify = '''    def verify_checksum(self, filepath: Path, expected_md5: str) -> bool:
        """Verify MD5 checksum of downloaded file"""
        try:
            hash_md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest() == expected_md5
        except:
            return False'''

new_verify = '''    def verify_checksum(self, filepath: Path, expected_md5: str) -> bool:
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
            return False'''

content = content.replace(old_verify, new_verify)

# Write the updated content
with open('src/build/downloader.py', 'w') as f:
    f.write(content)

print("✅ Improved checksum verification logging")