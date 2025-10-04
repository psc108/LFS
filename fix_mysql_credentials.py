#!/usr/bin/env python3

# Read the current db_manager.py
with open('src/database/db_manager.py', 'r') as f:
    content = f.read()

# Replace the credential loading with root user temporarily
old_creds = '''            # Load credentials
            creds_file = Path('.mysql_credentials')
            if creds_file.exists():
                with open(creds_file, 'r') as f:
                    password = f.read().strip()
            else:
                password = 'lfs_password'  # Default
            
            # Create connection pool
            config = {
                'user': 'lfs_user',
                'password': password,'''

new_creds = '''            # Load credentials - use root user temporarily
            creds_file = Path('.mysql_credentials')
            if creds_file.exists():
                with open(creds_file, 'r') as f:
                    password = f.read().strip()
            else:
                password = 'your_mysql_root_password'  # Will be prompted
            
            # Create connection pool - use root user
            config = {
                'user': 'root',
                'password': password,'''

content = content.replace(old_creds, new_creds)

# Write the updated content
with open('src/database/db_manager.py', 'w') as f:
    f.write(content)

print("✅ Updated to use MySQL root user - please update .mysql_credentials with your root password")