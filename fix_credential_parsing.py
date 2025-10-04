#!/usr/bin/env python3

# Read the current db_manager.py
with open('src/database/db_manager.py', 'r') as f:
    content = f.read()

# Replace the credential loading with proper parsing
old_creds = '''            # Load credentials - use root user temporarily
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

new_creds = '''            # Load credentials from .mysql_credentials file
            creds_file = Path('.mysql_credentials')
            root_password = None
            lfs_password = None
            
            if creds_file.exists():
                with open(creds_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('MySQL Root Password:'):
                            root_password = line.split(':', 1)[1].strip()
                        elif line.startswith('Password:'):
                            lfs_password = line.split(':', 1)[1].strip()
            
            # Try lfs_user first, fallback to root
            if lfs_password:
                config = {
                    'user': 'lfs_user',
                    'password': lfs_password,'''

content = content.replace(old_creds, new_creds)

# Add fallback logic after the config
old_pool_init = '''                'host': 'localhost',
                'database': 'lfs_builds',
                'pool_name': 'lfs_pool',
                'pool_size': 5,
                'pool_reset_session': True,
                'autocommit': True,
                'charset': 'utf8mb4',
                'use_unicode': True,
                'connect_timeout': 10,
                'sql_mode': 'TRADITIONAL'
            }
            
            self.pool = pooling.MySQLConnectionPool(**config)
            print("✅ MySQL connection pool initialized")'''

new_pool_init = '''                    'host': 'localhost',
                    'database': 'lfs_builds',
                    'pool_name': 'lfs_pool',
                    'pool_size': 5,
                    'pool_reset_session': True,
                    'autocommit': True,
                    'charset': 'utf8mb4',
                    'use_unicode': True,
                    'connect_timeout': 10,
                    'sql_mode': 'TRADITIONAL'
                }
                
                try:
                    self.pool = pooling.MySQLConnectionPool(**config)
                    print("✅ MySQL connection pool initialized with lfs_user")
                except Exception as e:
                    print(f"Failed with lfs_user: {e}")
                    # Fallback to root user
                    if root_password:
                        config['user'] = 'root'
                        config['password'] = root_password
                        self.pool = pooling.MySQLConnectionPool(**config)
                        print("✅ MySQL connection pool initialized with root user")
                    else:
                        raise Exception("No valid MySQL credentials found")
            else:
                # No lfs_password, try root directly
                if root_password:
                    config = {
                        'user': 'root',
                        'password': root_password,
                        'host': 'localhost',
                        'database': 'lfs_builds',
                        'pool_name': 'lfs_pool',
                        'pool_size': 5,
                        'pool_reset_session': True,
                        'autocommit': True,
                        'charset': 'utf8mb4',
                        'use_unicode': True,
                        'connect_timeout': 10,
                        'sql_mode': 'TRADITIONAL'
                    }
                    self.pool = pooling.MySQLConnectionPool(**config)
                    print("✅ MySQL connection pool initialized with root user")
                else:
                    raise Exception("No MySQL credentials found in .mysql_credentials")'''

content = content.replace(old_pool_init, new_pool_init)

# Write the updated content
with open('src/database/db_manager.py', 'w') as f:
    f.write(content)

print("✅ Fixed credential parsing to handle the .mysql_credentials file format")