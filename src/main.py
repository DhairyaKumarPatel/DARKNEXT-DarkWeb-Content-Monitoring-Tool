"""
DARKNEXT - Main Application
Orchestrates all components for dark web content monitoring
"""

import argparse
import logging
import os
import sys
import time
import signal
from datetime import datetime
from typing import Dict, List

import yaml
from dotenv import load_dotenv

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from tor_crawler import TorCrawler, AsyncTorCrawler
from content_parser import ContentParser
from database_handler import DatabaseHandler, FileBasedStorage
from alert_system import AlertSystem


class DarkNext:
    """Main DARKNEXT application class"""
    
    def __init__(self, config_path: str = None):
        """Initialize the DARKNEXT application"""
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.crawler = None
        self.parser = None
        self.database = None
        self.alert_system = None
        
        # Runtime flags
        self.running = False
        self.setup_signal_handlers()
        
        self.logger.info("DARKNEXT initialized successfully")
    
    def _load_config(self, config_path: str = None) -> Dict:
        """Load configuration from YAML file"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Override with environment variables if present
            self._override_config_with_env(config)
            
            return config
            
        except FileNotFoundError:
            print(f"Configuration file not found: {config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing configuration file: {str(e)}")
            sys.exit(1)
    
    def _override_config_with_env(self, config: Dict):
        """Override configuration with environment variables"""
        # Tor settings
        if 'TOR_PROXY_HOST' in os.environ:
            config['tor']['proxy_host'] = os.environ['TOR_PROXY_HOST']
        if 'TOR_PROXY_PORT' in os.environ:
            config['tor']['proxy_port'] = int(os.environ['TOR_PROXY_PORT'])
        
        # MongoDB settings
        if 'MONGODB_URI' in os.environ:
            # Parse MongoDB URI (basic parsing)
            uri = os.environ['MONGODB_URI']
            if '://' in uri:
                config['database']['host'] = uri  # Use full URI
        
        # Telegram settings
        if 'TELEGRAM_BOT_TOKEN' in os.environ:
            config['alerts']['telegram']['bot_token'] = os.environ['TELEGRAM_BOT_TOKEN']
        if 'TELEGRAM_CHAT_ID' in os.environ:
            config['alerts']['telegram']['chat_id'] = os.environ['TELEGRAM_CHAT_ID']
        
        # Email settings
        if 'EMAIL_USERNAME' in os.environ:
            config['alerts']['email']['username'] = os.environ['EMAIL_USERNAME']
        if 'EMAIL_PASSWORD' in os.environ:
            config['alerts']['email']['password'] = os.environ['EMAIL_PASSWORD']
        if 'EMAIL_RECIPIENT' in os.environ:
            config['alerts']['email']['recipient'] = os.environ['EMAIL_RECIPIENT']
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config.get('logging', {})
        
        level = getattr(logging, log_config.get('level', 'INFO').upper())
        format_str = log_config.get('format', '[%(asctime)s] %(levelname)s - %(name)s: %(message)s')
        
        # Create logger
        logging.basicConfig(
            level=level,
            format=format_str,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add file handler if enabled
        if log_config.get('file_enabled', True):
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, f"darknext_{datetime.now().strftime('%Y%m%d')}.log")
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(format_str, datefmt='%Y-%m-%d %H:%M:%S')
            file_handler.setFormatter(file_formatter)
            
            # Add to root logger
            logging.getLogger().addHandler(file_handler)
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def initialize_components(self):
        """Initialize all application components"""
        self.logger.info("Initializing components...")
        
        try:
            # Initialize crawler
            self.crawler = TorCrawler(self.config)
            
            # Test Tor connection
            if not self.crawler.test_tor_connection():
                self.logger.error("Tor connection test failed. Please ensure Tor is running.")
                return False
            
            # Initialize parser
            keywords_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'keywords.txt')
            self.parser = ContentParser(self.config, keywords_file)
            
            # Initialize database
            try:
                self.database = DatabaseHandler(self.config)
            except Exception as e:
                self.logger.warning(f"MongoDB not available, using file-based storage: {str(e)}")
                self.database = FileBasedStorage(self.config)
            
            # Initialize alert system
            self.alert_system = AlertSystem(self.config)
            
            self.logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {str(e)}")
            return False
    
    def run_single_scan(self, urls_file: str = None) -> bool:
        """Run a single scan of configured URLs"""
        self.logger.info("Starting single scan...")
        
        if urls_file is None:
            urls_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'onion_urls.txt')
        
        try:
            # Crawl URLs
            crawl_results = self.crawler.crawl_urls_from_file(urls_file)
            
            if not crawl_results:
                self.logger.warning("No content was crawled")
                return False
            
            self.logger.info(f"Crawled {len(crawl_results)} pages")
            
            # Process each result
            alerts_sent = 0
            findings_saved = 0
            
            for page_data in crawl_results:
                # Parse content
                parsed_result = self.parser.parse_content(page_data)
                
                # Save to database
                finding_id = self.database.save_finding(parsed_result)
                if finding_id:
                    findings_saved += 1
                
                # Archive raw content if configured
                if self.config.get('content', {}).get('archive_raw_html', True):
                    raw_html = page_data.get('raw_html', '')
                    if raw_html:
                        self.database.save_raw_content(
                            page_data['url'],
                            raw_html,
                            page_data['timestamp']
                        )
                
                # Send alert if matches found
                if parsed_result.get('has_matches', False):
                    if self.alert_system.send_alert(parsed_result):
                        alerts_sent += 1
                        self.logger.info(f"Alert sent for: {parsed_result['url']}")
            
            # Log summary
            self.logger.info(f"Scan completed: {findings_saved} findings saved, {alerts_sent} alerts sent")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error during scan: {str(e)}")
            return False
    
    def run_continuous_monitoring(self, urls_file: str = None, interval: int = 3600):
        """Run continuous monitoring with specified interval"""
        self.logger.info(f"Starting continuous monitoring (interval: {interval}s)")
        
        self.running = True
        scan_count = 0
        
        while self.running:
            try:
                scan_count += 1
                self.logger.info(f"Starting scan #{scan_count}")
                
                # Run scan
                self.run_single_scan(urls_file)
                
                # Wait for next scan
                self.logger.info(f"Scan #{scan_count} completed. Next scan in {interval} seconds.")
                
                # Sleep with interruption checking
                for _ in range(interval):
                    if not self.running:
                        break
                    time.sleep(1)
                
            except KeyboardInterrupt:
                self.logger.info("Monitoring interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Error in continuous monitoring: {str(e)}")
                # Wait before retrying
                time.sleep(60)
        
        self.logger.info("Continuous monitoring stopped")
    
    def show_statistics(self):
        """Display current statistics"""
        try:
            stats = self.database.get_statistics()
            
            print("\n" + "="*50)
            print("DARKNEXT STATISTICS")
            print("="*50)
            
            print(f"Total findings: {stats.get('total_findings', 0)}")
            print(f"Findings with matches: {stats.get('findings_with_matches', 0)}")
            print(f"Unique URLs: {stats.get('unique_urls', 0)}")
            
            # Recent activity
            recent = stats.get('recent_activity', {})
            if recent:
                print(f"\nRecent Activity:")
                print(f"  Last hour: {recent.get('last_1_hours', 0)}")
                print(f"  Last 24 hours: {recent.get('last_24_hours', 0)}")
                print(f"  Last 7 days: {recent.get('last_168_hours', 0)}")
            
            # Top keywords
            keyword_stats = stats.get('keyword_stats', {})
            if keyword_stats:
                print(f"\nTop Keywords:")
                for keyword, kstats in list(keyword_stats.items())[:10]:
                    print(f"  {keyword}: {kstats['count']} matches on {kstats['unique_urls']} URLs")
            
            print("="*50)
            
        except Exception as e:
            self.logger.error(f"Error retrieving statistics: {str(e)}")
    
    def test_components(self):
        """Test all components"""
        print("\n" + "="*50)
        print("TESTING DARKNEXT COMPONENTS")
        print("="*50)
        
        # Test Tor connection
        print("Testing Tor connection...")
        if self.crawler.test_tor_connection():
            print("✓ Tor connection: OK")
        else:
            print("✗ Tor connection: FAILED")
        
        # Test database
        print("Testing database connection...")
        try:
            if hasattr(self.database, 'collection'):
                # MongoDB test
                self.database.collection.find_one()
                print("✓ MongoDB connection: OK")
            else:
                # File storage test
                print("✓ File storage: OK")
        except Exception as e:
            print(f"✗ Database connection: FAILED - {str(e)}")
        
        # Test alerts
        print("Testing alert systems...")
        alert_results = self.alert_system.test_alerts()
        for method, success in alert_results.items():
            status = "OK" if success else "FAILED"
            print(f"{'✓' if success else '✗'} {method.title()} alerts: {status}")
        
        print("="*50)
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up resources...")
        
        if self.crawler:
            self.crawler.close()
        
        if self.database and hasattr(self.database, 'close'):
            self.database.close()
        
        self.logger.info("Cleanup completed")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='DARKNEXT - Dark Web Content Monitor')
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--urls', '-u', help='Path to URLs file')
    parser.add_argument('--mode', '-m', choices=['single', 'continuous', 'test', 'stats'], 
                       default='single', help='Operation mode')
    parser.add_argument('--interval', '-i', type=int, default=3600, 
                       help='Monitoring interval in seconds (for continuous mode)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    try:
        # Initialize application
        app = DarkNext(config_path=args.config)
        
        # Set verbose logging if requested
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Initialize components
        if not app.initialize_components():
            print("Failed to initialize components. Exiting.")
            sys.exit(1)
        
        # Run based on mode
        if args.mode == 'test':
            app.test_components()
        elif args.mode == 'stats':
            app.show_statistics()
        elif args.mode == 'single':
            success = app.run_single_scan(args.urls)
            sys.exit(0 if success else 1)
        elif args.mode == 'continuous':
            app.run_continuous_monitoring(args.urls, args.interval)
        
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)
    finally:
        if 'app' in locals():
            app.cleanup()


if __name__ == '__main__':
    main()