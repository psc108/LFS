import smtplib
import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

class NotificationSystem:
    def __init__(self, config_file: str = None):
        self.config_file = Path(config_file or "notification_config.json")
        self.config = self._load_config()
        self.notification_history = []
    
    def _load_config(self) -> Dict:
        """Load notification configuration"""
        default_config = {
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'from_address': '',
                'recipients': []
            },
            'slack': {
                'enabled': False,
                'webhook_url': '',
                'channel': '#builds',
                'username': 'LFS Build System'
            },
            'discord': {
                'enabled': False,
                'webhook_url': ''
            },
            'teams': {
                'enabled': False,
                'webhook_url': ''
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                print(f"Error loading notification config: {e}")
        
        return default_config
    
    def save_config(self):
        """Save notification configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving notification config: {e}")
    
    def send_build_notification(self, event_type: str, build_data: Dict):
        """Send notification for build events"""
        try:
            message = self._format_build_message(event_type, build_data)
            
            if self.config['email']['enabled']:
                self._send_email_notification(message, event_type, build_data)
            
            if self.config['slack']['enabled']:
                self._send_slack_notification(message, event_type, build_data)
            
            if self.config['discord']['enabled']:
                self._send_discord_notification(message, event_type, build_data)
            
            if self.config['teams']['enabled']:
                self._send_teams_notification(message, event_type, build_data)
            
            # Store notification history
            self.notification_history.append({
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'build_id': build_data.get('build_id'),
                'message': message['text']
            })
            
        except Exception as e:
            print(f"Notification error: {e}")
    
    def _format_build_message(self, event_type: str, build_data: Dict) -> Dict:
        """Format build notification message"""
        build_id = build_data.get('build_id', 'Unknown')
        config_name = build_data.get('config_name', 'Unknown')
        status = build_data.get('status', 'Unknown')
        
        emoji_map = {
            'build_started': '🚀',
            'build_completed': '✅',
            'build_failed': '❌',
            'build_cancelled': '⏹️',
            'stage_completed': '📋',
            'stage_failed': '⚠️'
        }
        
        emoji = emoji_map.get(event_type, '📢')
        
        if event_type == 'build_started':
            title = f"{emoji} Build Started"
            text = f"LFS build {build_id} ({config_name}) has started"
        elif event_type == 'build_completed':
            duration = build_data.get('duration', 'Unknown')
            title = f"{emoji} Build Completed Successfully"
            text = f"LFS build {build_id} ({config_name}) completed successfully in {duration}"
        elif event_type == 'build_failed':
            error = build_data.get('error', 'Unknown error')
            title = f"{emoji} Build Failed"
            text = f"LFS build {build_id} ({config_name}) failed: {error}"
        elif event_type == 'build_cancelled':
            title = f"{emoji} Build Cancelled"
            text = f"LFS build {build_id} ({config_name}) was cancelled"
        elif event_type == 'stage_completed':
            stage = build_data.get('stage_name', 'Unknown')
            title = f"{emoji} Stage Completed"
            text = f"Stage '{stage}' completed in build {build_id}"
        elif event_type == 'stage_failed':
            stage = build_data.get('stage_name', 'Unknown')
            error = build_data.get('error', 'Unknown error')
            title = f"{emoji} Stage Failed"
            text = f"Stage '{stage}' failed in build {build_id}: {error}"
        else:
            title = f"{emoji} Build Event"
            text = f"Build {build_id} event: {event_type}"
        
        return {
            'title': title,
            'text': text,
            'color': self._get_color_for_event(event_type)
        }
    
    def _get_color_for_event(self, event_type: str) -> str:
        """Get color code for event type"""
        color_map = {
            'build_started': '#36a64f',      # Green
            'build_completed': '#36a64f',    # Green
            'build_failed': '#ff0000',       # Red
            'build_cancelled': '#ffaa00',    # Orange
            'stage_completed': '#36a64f',    # Green
            'stage_failed': '#ff0000'        # Red
        }
        return color_map.get(event_type, '#808080')  # Gray default
    
    def _send_email_notification(self, message: Dict, event_type: str, build_data: Dict):
        """Send email notification"""
        try:
            email_config = self.config['email']
            
            msg = MIMEMultipart()
            msg['From'] = email_config['from_address']
            msg['To'] = ', '.join(email_config['recipients'])
            msg['Subject'] = f"LFS Build System - {message['title']}"
            
            body = f"""
{message['text']}

Build Details:
- Build ID: {build_data.get('build_id', 'N/A')}
- Configuration: {build_data.get('config_name', 'N/A')}
- Status: {build_data.get('status', 'N/A')}
- Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This is an automated message from the LFS Build System.
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            print(f"Email notification error: {e}")
    
    def _send_slack_notification(self, message: Dict, event_type: str, build_data: Dict):
        """Send Slack notification"""
        try:
            slack_config = self.config['slack']
            
            payload = {
                'channel': slack_config['channel'],
                'username': slack_config['username'],
                'attachments': [{
                    'color': message['color'],
                    'title': message['title'],
                    'text': message['text'],
                    'fields': [
                        {'title': 'Build ID', 'value': build_data.get('build_id', 'N/A'), 'short': True},
                        {'title': 'Configuration', 'value': build_data.get('config_name', 'N/A'), 'short': True},
                        {'title': 'Status', 'value': build_data.get('status', 'N/A'), 'short': True},
                        {'title': 'Timestamp', 'value': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'short': True}
                    ]
                }]
            }
            
            response = requests.post(slack_config['webhook_url'], json=payload, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            print(f"Slack notification error: {e}")
    
    def _send_discord_notification(self, message: Dict, event_type: str, build_data: Dict):
        """Send Discord notification"""
        try:
            discord_config = self.config['discord']
            
            embed = {
                'title': message['title'],
                'description': message['text'],
                'color': int(message['color'].replace('#', ''), 16),
                'fields': [
                    {'name': 'Build ID', 'value': build_data.get('build_id', 'N/A'), 'inline': True},
                    {'name': 'Configuration', 'value': build_data.get('config_name', 'N/A'), 'inline': True},
                    {'name': 'Status', 'value': build_data.get('status', 'N/A'), 'inline': True}
                ],
                'timestamp': datetime.now().isoformat()
            }
            
            payload = {'embeds': [embed]}
            
            response = requests.post(discord_config['webhook_url'], json=payload, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            print(f"Discord notification error: {e}")
    
    def _send_teams_notification(self, message: Dict, event_type: str, build_data: Dict):
        """Send Microsoft Teams notification"""
        try:
            teams_config = self.config['teams']
            
            payload = {
                '@type': 'MessageCard',
                '@context': 'http://schema.org/extensions',
                'themeColor': message['color'],
                'summary': message['title'],
                'sections': [{
                    'activityTitle': message['title'],
                    'activitySubtitle': message['text'],
                    'facts': [
                        {'name': 'Build ID', 'value': build_data.get('build_id', 'N/A')},
                        {'name': 'Configuration', 'value': build_data.get('config_name', 'N/A')},
                        {'name': 'Status', 'value': build_data.get('status', 'N/A')},
                        {'name': 'Timestamp', 'value': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    ]
                }]
            }
            
            response = requests.post(teams_config['webhook_url'], json=payload, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            print(f"Teams notification error: {e}")
    
    def test_notifications(self) -> Dict:
        """Test all enabled notification channels"""
        test_results = {}
        
        test_data = {
            'build_id': 'test-123',
            'config_name': 'Test Configuration',
            'status': 'testing'
        }
        
        try:
            if self.config['email']['enabled']:
                self._send_email_notification(
                    {'title': 'Test Notification', 'text': 'This is a test notification', 'color': '#36a64f'},
                    'test', test_data
                )
                test_results['email'] = 'success'
        except Exception as e:
            test_results['email'] = f'failed: {e}'
        
        try:
            if self.config['slack']['enabled']:
                self._send_slack_notification(
                    {'title': 'Test Notification', 'text': 'This is a test notification', 'color': '#36a64f'},
                    'test', test_data
                )
                test_results['slack'] = 'success'
        except Exception as e:
            test_results['slack'] = f'failed: {e}'
        
        try:
            if self.config['discord']['enabled']:
                self._send_discord_notification(
                    {'title': 'Test Notification', 'text': 'This is a test notification', 'color': '#36a64f'},
                    'test', test_data
                )
                test_results['discord'] = 'success'
        except Exception as e:
            test_results['discord'] = f'failed: {e}'
        
        try:
            if self.config['teams']['enabled']:
                self._send_teams_notification(
                    {'title': 'Test Notification', 'text': 'This is a test notification', 'color': '#36a64f'},
                    'test', test_data
                )
                test_results['teams'] = 'success'
        except Exception as e:
            test_results['teams'] = f'failed: {e}'
        
        return test_results
    
    def start_notification_service(self, service_config: dict) -> str:
        """Start notification service and return service ID"""
        import uuid
        service_id = f"notify-{uuid.uuid4().hex[:8]}"
        
        try:
            # Update configuration
            self.config.update(service_config)
            self.save_config()
            
            # Test all enabled services
            test_results = self.test_notifications()
            
            print(f"Notification service {service_id} started with results: {test_results}")
            
            return service_id
            
        except Exception as e:
            raise Exception(f"Failed to start notification service: {str(e)}")