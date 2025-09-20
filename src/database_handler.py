"""
DARKNEXT - Database Handler Module
Handles data storage and archiving functionality
"""

import json
import logging
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Optional

import pymongo
from pymongo import MongoClient


class DatabaseHandler:
    """Handles database operations for storing findings"""
    
    def __init__(self, config: Dict):
        """Initialize the database handler"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Database configuration
        db_config = config.get('database', {})
        self.db_type = db_config.get('type', 'mongodb')
        
        if self.db_type == 'mongodb':
            self._setup_mongodb()
        
        # Archive directory for raw HTML
        self.archive_dir = os.path.join(os.getcwd(), 'archive')
        os.makedirs(self.archive_dir, exist_ok=True)
        
    def _setup_mongodb(self):
        """Setup MongoDB connection"""
        try:
            db_config = self.config['database']
            
            # Build connection string
            if 'MONGODB_URI' in os.environ:
                connection_string = os.environ['MONGODB_URI']
            else:
                host = db_config.get('host', 'localhost')
                port = db_config.get('port', 27017)
                connection_string = f"mongodb://{host}:{port}/"
            
            # Connect to MongoDB
            self.client = MongoClient(connection_string)
            self.db = self.client[db_config.get('name', 'darknext_db')]
            self.collection = self.db[db_config.get('collection', 'dark_web_findings')]
            
            # Create indexes for better performance
            self._create_indexes()
            
            # Test connection
            self.client.admin.command('ping')
            self.logger.info("MongoDB connection established successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # Create indexes
            self.collection.create_index("url")
            self.collection.create_index("timestamp")
            self.collection.create_index("has_matches")
            self.collection.create_index([("keyword_matches.keyword", 1)])
            
            self.logger.info("Database indexes created successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to create indexes: {str(e)}")
    
    def save_finding(self, parsed_result: Dict) -> str:
        """Save a parsed result to the database"""
        try:
            # Add metadata
            finding = parsed_result.copy()
            finding['_id'] = self._generate_id(parsed_result['url'], parsed_result['timestamp'])
            finding['created_at'] = datetime.now()
            finding['updated_at'] = datetime.now()
            
            # Insert or update the document
            result = self.collection.replace_one(
                {'_id': finding['_id']},
                finding,
                upsert=True
            )
            
            if result.upserted_id:
                self.logger.info(f"New finding saved: {finding['url']}")
            else:
                self.logger.info(f"Finding updated: {finding['url']}")
            
            return finding['_id']
            
        except Exception as e:
            self.logger.error(f"Failed to save finding: {str(e)}")
            return None
    
    def save_raw_content(self, url: str, raw_html: str, timestamp: float) -> Optional[str]:
        """Save raw HTML content to archive directory"""
        try:
            if not self.config.get('content', {}).get('archive_raw_html', True):
                return None
            
            # Generate filename
            url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
            timestamp_str = datetime.fromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp_str}_{url_hash}.html"
            
            filepath = os.path.join(self.archive_dir, filename)
            
            # Save raw HTML
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(raw_html)
            
            self.logger.info(f"Raw content archived: {filename}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to archive raw content: {str(e)}")
            return None
    
    def get_findings(self, filters: Dict = None, limit: int = 100) -> List[Dict]:
        """Retrieve findings from database with optional filters"""
        try:
            query = filters or {}
            
            findings = list(self.collection.find(query).limit(limit).sort('timestamp', -1))
            
            # Convert ObjectId to string for JSON serialization
            for finding in findings:
                finding['_id'] = str(finding['_id'])
            
            return findings
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve findings: {str(e)}")
            return []
    
    def get_findings_with_matches(self, limit: int = 100) -> List[Dict]:
        """Get only findings that have keyword or entity matches"""
        return self.get_findings({'has_matches': True}, limit)
    
    def get_findings_by_keyword(self, keyword: str, limit: int = 100) -> List[Dict]:
        """Get findings containing a specific keyword"""
        return self.get_findings({'keyword_matches.keyword': keyword}, limit)
    
    def get_recent_findings(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """Get findings from the last N hours"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        return self.get_findings({'timestamp': {'$gte': cutoff_time}}, limit)
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        try:
            stats = {
                'total_findings': self.collection.count_documents({}),
                'findings_with_matches': self.collection.count_documents({'has_matches': True}),
                'unique_urls': len(self.collection.distinct('url')),
                'keyword_stats': {},
                'entity_stats': {},
                'recent_activity': {}
            }
            
            # Keyword statistics
            pipeline = [
                {'$unwind': '$keyword_matches'},
                {'$group': {
                    '_id': '$keyword_matches.keyword',
                    'count': {'$sum': 1},
                    'unique_urls': {'$addToSet': '$url'}
                }},
                {'$project': {
                    'keyword': '$_id',
                    'count': 1,
                    'unique_urls': {'$size': '$unique_urls'}
                }},
                {'$sort': {'count': -1}},
                {'$limit': 20}
            ]
            
            keyword_results = list(self.collection.aggregate(pipeline))
            stats['keyword_stats'] = {r['keyword']: {'count': r['count'], 'unique_urls': r['unique_urls']} 
                                    for r in keyword_results}
            
            # Recent activity (last 7 days)
            cutoff_times = [1, 24, 24*7]  # 1 hour, 1 day, 7 days
            for hours in cutoff_times:
                cutoff_time = datetime.now().timestamp() - (hours * 3600)
                count = self.collection.count_documents({'timestamp': {'$gte': cutoff_time}})
                stats['recent_activity'][f'last_{hours}_hours'] = count
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {str(e)}")
            return {}
    
    def cleanup_old_findings(self, days: int = 30) -> int:
        """Remove findings older than specified days"""
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
            
            result = self.collection.delete_many({'timestamp': {'$lt': cutoff_time}})
            deleted_count = result.deleted_count
            
            self.logger.info(f"Cleaned up {deleted_count} old findings (older than {days} days)")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old findings: {str(e)}")
            return 0
    
    def export_findings(self, filepath: str, filters: Dict = None) -> bool:
        """Export findings to JSON file"""
        try:
            findings = self.get_findings(filters, limit=0)  # Get all matching findings
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(findings, f, indent=2, default=str)
            
            self.logger.info(f"Exported {len(findings)} findings to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export findings: {str(e)}")
            return False
    
    def _generate_id(self, url: str, timestamp: float) -> str:
        """Generate a unique ID for a finding"""
        content = f"{url}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def close(self):
        """Close database connections"""
        try:
            if hasattr(self, 'client'):
                self.client.close()
                self.logger.info("Database connection closed")
        except Exception as e:
            self.logger.error(f"Error closing database connection: {str(e)}")


class FileBasedStorage:
    """Alternative file-based storage for when MongoDB is not available"""
    
    def __init__(self, config: Dict):
        """Initialize file-based storage"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create storage directory
        self.storage_dir = os.path.join(os.getcwd(), 'data')
        os.makedirs(self.storage_dir, exist_ok=True)
        
        self.findings_file = os.path.join(self.storage_dir, 'findings.jsonl')
        
    def save_finding(self, parsed_result: Dict) -> str:
        """Save finding to JSONL file"""
        try:
            finding = parsed_result.copy()
            finding['_id'] = self._generate_id(parsed_result['url'], parsed_result['timestamp'])
            finding['created_at'] = datetime.now().isoformat()
            
            # Append to JSONL file
            with open(self.findings_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(finding, default=str) + '\n')
            
            self.logger.info(f"Finding saved to file: {finding['url']}")
            return finding['_id']
            
        except Exception as e:
            self.logger.error(f"Failed to save finding to file: {str(e)}")
            return None
    
    def get_findings(self, limit: int = 100) -> List[Dict]:
        """Get findings from JSONL file"""
        findings = []
        try:
            if not os.path.exists(self.findings_file):
                return findings
            
            with open(self.findings_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        finding = json.loads(line.strip())
                        findings.append(finding)
                        
                        if len(findings) >= limit:
                            break
            
            # Sort by timestamp (newest first)
            findings.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            
            return findings
            
        except Exception as e:
            self.logger.error(f"Failed to read findings from file: {str(e)}")
            return findings
    
    def _generate_id(self, url: str, timestamp: float) -> str:
        """Generate a unique ID for a finding"""
        content = f"{url}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()