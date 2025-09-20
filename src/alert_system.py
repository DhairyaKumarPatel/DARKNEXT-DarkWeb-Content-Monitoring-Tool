"""
DARKNEXT - Alert System Module
Handles sending alerts via Telegram, email, or file notifications
"""

import json
import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.getLogger(__name__).warning("python-telegram-bot not available, Telegram alerts disabled")


class AlertSystem:
    """Handles various alert mechanisms for new findings"""
    
    def __init__(self, config: Dict):
        """Initialize the alert system"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.alerts_enabled = config.get('alerts', {}).get('enabled', True)
        self.alert_methods = config.get('alerts', {}).get('methods', [])
        
        if not self.alerts_enabled:
            self.logger.info("Alerts are disabled")
            return
        
        # Initialize alert methods
        self._setup_telegram()
        self._setup_email()
        self._setup_file_alerts()
        
    def _setup_telegram(self):
        """Setup Telegram bot for alerts"""
        if 'telegram' not in self.alert_methods or not TELEGRAM_AVAILABLE:
            self.telegram_bot = None
            return
            
        try:
            telegram_config = self.config.get('alerts', {}).get('telegram', {})
            bot_token = os.environ.get('TELEGRAM_BOT_TOKEN') or telegram_config.get('bot_token')
            self.chat_id = os.environ.get('TELEGRAM_CHAT_ID') or telegram_config.get('chat_id')
            
            if bot_token and self.chat_id:
                self.telegram_bot = Bot(token=bot_token)
                self.logger.info("Telegram bot initialized successfully")
            else:
                self.logger.warning("Telegram bot token or chat ID not configured")
                self.telegram_bot = None
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram bot: {str(e)}")
            self.telegram_bot = None
    
    def _setup_email(self):
        """Setup email configuration for alerts"""
        if 'email' not in self.alert_methods:
            self.email_config = None
            return
            
        try:
            email_config = self.config.get('alerts', {}).get('email', {})
            
            self.email_config = {
                'smtp_server': email_config.get('smtp_server', 'smtp.gmail.com'),
                'smtp_port': email_config.get('smtp_port', 587),
                'username': os.environ.get('EMAIL_USERNAME') or email_config.get('username'),
                'password': os.environ.get('EMAIL_PASSWORD') or email_config.get('password'),
                'recipient': os.environ.get('EMAIL_RECIPIENT') or email_config.get('recipient')
            }
            
            if not all([self.email_config['username'], self.email_config['password'], self.email_config['recipient']]):
                self.logger.warning("Email configuration incomplete")
                self.email_config = None
            else:
                self.logger.info("Email alerts configured successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to setup email configuration: {str(e)}")
            self.email_config = None
    
    def _setup_file_alerts(self):
        """Setup file-based alerts"""
        if 'file' in self.alert_methods:
            self.alerts_dir = os.path.join(os.getcwd(), 'alerts')
            os.makedirs(self.alerts_dir, exist_ok=True)
            self.logger.info("File alerts configured successfully")
    
    def send_alert(self, finding: Dict) -> bool:
        """Send alert for a new finding using configured methods"""
        if not self.alerts_enabled or not finding.get('has_matches', False):
            return False
        
        success = False
        
        # Send Telegram alert
        if 'telegram' in self.alert_methods and self.telegram_bot:
            if self._send_telegram_alert(finding):
                success = True
        
        # Send email alert
        if 'email' in self.alert_methods and self.email_config:
            if self._send_email_alert(finding):
                success = True
        
        # Save file alert
        if 'file' in self.alert_methods:
            if self._save_file_alert(finding):
                success = True
        
        return success
    
    def _send_telegram_alert(self, finding: Dict) -> bool:
        """Send alert via Telegram"""
        try:
            message = self._format_telegram_message(finding)
            
            # Send message
            self.telegram_bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            self.logger.info(f"Telegram alert sent for: {finding['url']}")
            return True
            
        except TelegramError as e:
            self.logger.error(f"Failed to send Telegram alert: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending Telegram alert: {str(e)}")
            return False
    
    def _send_email_alert(self, finding: Dict) -> bool:
        """Send alert via email"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_config['username']
            msg['To'] = self.email_config['recipient']
            msg['Subject'] = f"DARKNEXT Alert - New Finding on {finding.get('url', 'Unknown')}"
            
            # Create HTML body
            body = self._format_email_message(finding)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(msg)
            
            self.logger.info(f"Email alert sent for: {finding['url']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {str(e)}")
            return False
    
    def _save_file_alert(self, finding: Dict) -> bool:
        """Save alert to file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"alert_{timestamp}.json"
            filepath = os.path.join(self.alerts_dir, filename)
            
            alert_data = {
                'timestamp': datetime.now().isoformat(),
                'finding': finding,
                'alert_type': 'new_finding'
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(alert_data, f, indent=2, default=str)
            
            self.logger.info(f"File alert saved: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save file alert: {str(e)}")
            return False
    
    def _format_telegram_message(self, finding: Dict) -> str:
        """Format finding data for Telegram message"""
        url = finding.get('url', 'Unknown')
        title = finding.get('title', 'No Title')
        timestamp = datetime.fromtimestamp(finding.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')
        
        message = f"🚨 <b>DARKNEXT Alert</b>\n\n"
        message += f"🌐 <b>URL:</b> <code>{url}</code>\n"
        message += f"📄 <b>Title:</b> {title}\n"
        message += f"⏰ <b>Time:</b> {timestamp}\n\n"
        
        # Add keyword matches
        keyword_matches = finding.get('keyword_matches', [])
        if keyword_matches:
            message += f"🔍 <b>Keywords Found:</b>\n"
            keywords = list(set([match['keyword'] for match in keyword_matches[:5]]))  # Limit to 5
            for keyword in keywords:
                message += f"  • {keyword}\n"
            if len(keyword_matches) > 5:
                message += f"  • ... and {len(keyword_matches) - 5} more\n"
            message += "\n"
        
        # Add entities
        entities = finding.get('entities', {})
        if entities:
            message += f"🎯 <b>Entities Found:</b>\n"
            for entity_type, entity_list in entities.items():
                if entity_list:
                    count = len(entity_list)
                    entity_name = entity_type.replace('_', ' ').title()
                    message += f"  • {entity_name}: {count}\n"
            message += "\n"
        
        # Add content snippet
        snippet = finding.get('content_snippet', '')
        if snippet:
            snippet_preview = snippet[:200] + ("..." if len(snippet) > 200 else "")
            message += f"📝 <b>Content Preview:</b>\n<code>{snippet_preview}</code>\n"
        
        return message
    
    def _format_email_message(self, finding: Dict) -> str:
        """Format finding data for email message"""
        url = finding.get('url', 'Unknown')
        title = finding.get('title', 'No Title')
        timestamp = datetime.fromtimestamp(finding.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')
        
        html = f"""
        <html>
        <head></head>
        <body>
            <h2 style="color: #d73527;">🚨 DARKNEXT Alert - New Finding</h2>
            
            <table style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px; background-color: #f2f2f2;"><strong>URL:</strong></td>
                    <td style="border: 1px solid #ddd; padding: 8px;"><code>{url}</code></td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px; background-color: #f2f2f2;"><strong>Title:</strong></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{title}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px; background-color: #f2f2f2;"><strong>Timestamp:</strong></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{timestamp}</td>
                </tr>
            </table>
            
        """
        
        # Add keyword matches
        keyword_matches = finding.get('keyword_matches', [])
        if keyword_matches:
            html += f"""
            <h3 style="color: #2c5aa0;">🔍 Keywords Found:</h3>
            <ul>
            """
            keywords = list(set([match['keyword'] for match in keyword_matches[:10]]))
            for keyword in keywords:
                html += f"<li><strong>{keyword}</strong></li>"
            if len(keyword_matches) > 10:
                html += f"<li>... and {len(keyword_matches) - 10} more</li>"
            html += "</ul>"
        
        # Add entities
        entities = finding.get('entities', {})
        if entities:
            html += f"""
            <h3 style="color: #2c5aa0;">🎯 Entities Found:</h3>
            <ul>
            """
            for entity_type, entity_list in entities.items():
                if entity_list:
                    count = len(entity_list)
                    entity_name = entity_type.replace('_', ' ').title()
                    html += f"<li><strong>{entity_name}:</strong> {count}</li>"
            html += "</ul>"
        
        # Add content snippet
        snippet = finding.get('content_snippet', '')
        if snippet:
            snippet_preview = snippet[:500] + ("..." if len(snippet) > 500 else "")
            html += f"""
            <h3 style="color: #2c5aa0;">📝 Content Preview:</h3>
            <div style="background-color: #f5f5f5; padding: 10px; border-left: 4px solid #2c5aa0; font-family: monospace;">
                {snippet_preview}
            </div>
            """
        
        html += """
            <hr style="margin: 20px 0;">
            <p style="color: #666; font-size: 12px;">
                This alert was generated by DARKNEXT - Dark Web Content Monitor<br>
                Please handle this information responsibly and in accordance with applicable laws.
            </p>
        </body>
        </html>
        """
        
        return html
    
    def send_summary_alert(self, statistics: Dict, timeframe: str = "daily") -> bool:
        """Send summary alert with statistics"""
        if not self.alerts_enabled:
            return False
        
        try:
            summary_data = {
                'type': 'summary',
                'timeframe': timeframe,
                'timestamp': datetime.now().isoformat(),
                'statistics': statistics
            }
            
            success = False
            
            # Send via configured methods
            if 'telegram' in self.alert_methods and self.telegram_bot:
                message = self._format_summary_telegram(statistics, timeframe)
                try:
                    self.telegram_bot.send_message(
                        chat_id=self.chat_id,
                        text=message,
                        parse_mode='HTML'
                    )
                    success = True
                except Exception as e:
                    self.logger.error(f"Failed to send Telegram summary: {str(e)}")
            
            # Save file summary
            if 'file' in self.alert_methods:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"summary_{timeframe}_{timestamp}.json"
                filepath = os.path.join(self.alerts_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(summary_data, f, indent=2, default=str)
                success = True
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send summary alert: {str(e)}")
            return False
    
    def _format_summary_telegram(self, statistics: Dict, timeframe: str) -> str:
        """Format statistics summary for Telegram"""
        message = f"📊 <b>DARKNEXT {timeframe.title()} Summary</b>\n\n"
        
        total = statistics.get('total_findings', 0)
        matches = statistics.get('findings_with_matches', 0)
        unique_urls = statistics.get('unique_urls', 0)
        
        message += f"📈 <b>Activity:</b>\n"
        message += f"  • Total findings: {total}\n"
        message += f"  • Findings with matches: {matches}\n"
        message += f"  • Unique URLs: {unique_urls}\n\n"
        
        # Top keywords
        keyword_stats = statistics.get('keyword_stats', {})
        if keyword_stats:
            message += f"🔍 <b>Top Keywords:</b>\n"
            for keyword, stats in list(keyword_stats.items())[:5]:
                count = stats['count']
                message += f"  • {keyword}: {count}\n"
            message += "\n"
        
        # Recent activity
        recent = statistics.get('recent_activity', {})
        if recent:
            message += f"⏰ <b>Recent Activity:</b>\n"
            message += f"  • Last hour: {recent.get('last_1_hours', 0)}\n"
            message += f"  • Last 24 hours: {recent.get('last_24_hours', 0)}\n"
            message += f"  • Last 7 days: {recent.get('last_168_hours', 0)}\n"
        
        return message
    
    def test_alerts(self) -> Dict[str, bool]:
        """Test all configured alert methods"""
        results = {}
        
        test_finding = {
            'url': 'http://test.onion',
            'title': 'Test Finding',
            'timestamp': datetime.now().timestamp(),
            'has_matches': True,
            'keyword_matches': [{'keyword': 'test', 'context': 'This is a test alert'}],
            'entities': {'emails': ['test@example.com']},
            'content_snippet': 'This is a test content snippet for alert testing.'
        }
        
        if 'telegram' in self.alert_methods:
            results['telegram'] = self._send_telegram_alert(test_finding)
        
        if 'email' in self.alert_methods:
            results['email'] = self._send_email_alert(test_finding)
        
        if 'file' in self.alert_methods:
            results['file'] = self._save_file_alert(test_finding)
        
        return results