import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

class UserManager:
    def __init__(self, users_db: str = "users.json"):
        self.users_db = Path(users_db)
        self.users = self._load_users()
        self.sessions = {}
    
    def _load_users(self) -> Dict:
        """Load users from database"""
        if self.users_db.exists():
            try:
                with open(self.users_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        default_users = {
            'admin': {
                'password_hash': self._hash_password('admin123'),
                'role': 'admin',
                'email': 'admin@lfs.local',
                'created_at': datetime.now().isoformat(),
                'permissions': ['build', 'admin', 'view', 'delete']
            }
        }
        
        self._save_users(default_users)
        return default_users
    
    def _save_users(self, users: Dict = None):
        """Save users to database"""
        users_to_save = users or self.users
        with open(self.users_db, 'w') as f:
            json.dump(users_to_save, f, indent=2)
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = "lfs_salt"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def create_user(self, username: str, password: str, email: str, role: str = 'user') -> Dict:
        """Create new user"""
        if username in self.users:
            return {'success': False, 'error': 'User already exists'}
        
        permissions = {
            'admin': ['build', 'admin', 'view', 'delete', 'user_management'],
            'developer': ['build', 'view', 'delete'],
            'viewer': ['view'],
            'user': ['build', 'view']
        }
        
        self.users[username] = {
            'password_hash': self._hash_password(password),
            'role': role,
            'email': email,
            'created_at': datetime.now().isoformat(),
            'permissions': permissions.get(role, ['view']),
            'last_login': None
        }
        
        self._save_users()
        return {'success': True, 'message': f'User {username} created'}
    
    def authenticate(self, username: str, password: str) -> Dict:
        """Authenticate user"""
        if username not in self.users:
            return {'success': False, 'error': 'Invalid credentials'}
        
        user = self.users[username]
        if user['password_hash'] != self._hash_password(password):
            return {'success': False, 'error': 'Invalid credentials'}
        
        user['last_login'] = datetime.now().isoformat()
        self._save_users()
        
        return {
            'success': True,
            'user': {
                'username': username,
                'role': user['role'],
                'permissions': user['permissions']
            }
        }
    
    def list_users(self) -> List[Dict]:
        """List all users"""
        users_list = []
        for username, user_data in self.users.items():
            users_list.append({
                'username': username,
                'role': user_data['role'],
                'email': user_data['email'],
                'created_at': user_data['created_at'],
                'last_login': user_data.get('last_login')
            })
        return users_list