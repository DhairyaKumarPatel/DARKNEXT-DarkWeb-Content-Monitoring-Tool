"""
DARKNEXT - Utility Functions
Common utilities for the DARKNEXT project
"""

import hashlib
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


def create_safe_filename(url: str, max_length: int = 100) -> str:
    """Create a safe filename from a URL"""
    # Remove protocol and make safe for filesystem
    parsed = urlparse(url)
    domain = parsed.netloc or 'unknown'
    path = parsed.path.replace('/', '_')
    
    # Remove unsafe characters
    safe_chars = re.sub(r'[^\w\-_.]', '_', f"{domain}{path}")
    
    # Truncate if too long
    if len(safe_chars) > max_length:
        safe_chars = safe_chars[:max_length]
    
    # Add timestamp for uniqueness
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return f"{timestamp}_{safe_chars}"


def hash_content(content: str, algorithm: str = 'sha256') -> str:
    """Generate hash of content"""
    hasher = getattr(hashlib, algorithm)()
    hasher.update(content.encode('utf-8'))
    return hasher.hexdigest()


def validate_onion_url(url: str) -> bool:
    """Validate if URL is a properly formatted .onion URL"""
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Check .onion domain
        if not parsed.netloc.endswith('.onion'):
            return False
        
        # Check .onion domain format (basic validation)
        domain = parsed.netloc.replace('.onion', '')
        
        # v2 onion: 16 characters, base32
        # v3 onion: 56 characters, base32
        if len(domain) not in [16, 56]:
            return False
        
        # Check if it's valid base32
        import base64
        try:
            base64.b32decode(domain.upper() + '======')  # Add padding
            return True
        except:
            return False
            
    except Exception:
        return False


def format_bytes(bytes_count: int) -> str:
    """Format byte count into human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


def sanitize_text(text: str, max_length: int = None) -> str:
    """Sanitize text for safe display/storage"""
    # Remove control characters except newlines and tabs
    sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    
    # Normalize whitespace
    sanitized = ' '.join(sanitized.split())
    
    # Truncate if necessary
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized


def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return ''


def is_tor_running(proxy_host: str = '127.0.0.1', proxy_port: int = 9050) -> bool:
    """Check if Tor is running on specified host and port"""
    import socket
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            result = sock.connect_ex((proxy_host, proxy_port))
            return result == 0
    except:
        return False


def load_wordlist(filepath: str, comment_char: str = '#') -> List[str]:
    """Load wordlist from file, ignoring comments and empty lines"""
    words = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith(comment_char):
                    words.append(line.lower())
        return words
    except FileNotFoundError:
        return []


def get_file_age(filepath: str) -> Optional[float]:
    """Get age of file in seconds"""
    try:
        mtime = os.path.getmtime(filepath)
        return time.time() - mtime
    except:
        return None


def ensure_directory(dirpath: str) -> bool:
    """Ensure directory exists, create if not"""
    try:
        os.makedirs(dirpath, exist_ok=True)
        return True
    except:
        return False


def clean_html(html_content: str) -> str:
    """Basic HTML cleaning - remove scripts, styles, and other unwanted content"""
    # This is a basic implementation - for production use, consider using a proper HTML sanitizer
    import re
    
    # Remove script and style elements
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove HTML comments
    html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
    
    # Remove other unwanted tags
    unwanted_tags = ['noscript', 'iframe', 'embed', 'object', 'applet']
    for tag in unwanted_tags:
        pattern = f'<{tag}[^>]*>.*?</{tag}>'
        html_content = re.sub(pattern, '', html_content, flags=re.IGNORECASE | re.DOTALL)
    
    return html_content


def rate_limit_delay(last_request_time: float, min_delay: float) -> None:
    """Add delay to respect rate limiting"""
    elapsed = time.time() - last_request_time
    if elapsed < min_delay:
        time.sleep(min_delay - elapsed)


class RateLimiter:
    """Simple rate limiter for requests"""
    
    def __init__(self, max_requests: int, time_window: int):
        """Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def can_make_request(self) -> bool:
        """Check if request can be made"""
        now = time.time()
        
        # Remove old requests outside time window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        
        return len(self.requests) < self.max_requests
    
    def make_request(self) -> bool:
        """Record a request if allowed"""
        if self.can_make_request():
            self.requests.append(time.time())
            return True
        return False
    
    def time_until_next_request(self) -> float:
        """Get time until next request is allowed"""
        if self.can_make_request():
            return 0.0
        
        oldest_request = min(self.requests)
        return self.time_window - (time.time() - oldest_request)


def generate_report_data(findings: List[Dict]) -> Dict[str, Any]:
    """Generate report data from findings"""
    if not findings:
        return {'error': 'No findings provided'}
    
    # Basic statistics
    total_findings = len(findings)
    findings_with_matches = sum(1 for f in findings if f.get('has_matches', False))
    
    # Collect all URLs
    urls = set()
    keywords_count = {}
    entities_count = {}
    
    for finding in findings:
        urls.add(finding.get('url', ''))
        
        # Count keywords
        for match in finding.get('keyword_matches', []):
            keyword = match.get('keyword', '')
            keywords_count[keyword] = keywords_count.get(keyword, 0) + 1
        
        # Count entities
        for entity_type, entity_list in finding.get('entities', {}).items():
            if entity_type not in entities_count:
                entities_count[entity_type] = 0
            entities_count[entity_type] += len(entity_list)
    
    # Time range
    timestamps = [f.get('timestamp', 0) for f in findings if f.get('timestamp')]
    time_range = {
        'earliest': datetime.fromtimestamp(min(timestamps)).isoformat() if timestamps else None,
        'latest': datetime.fromtimestamp(max(timestamps)).isoformat() if timestamps else None
    }
    
    return {
        'summary': {
            'total_findings': total_findings,
            'findings_with_matches': findings_with_matches,
            'unique_urls': len(urls),
            'match_rate': (findings_with_matches / total_findings * 100) if total_findings > 0 else 0
        },
        'time_range': time_range,
        'top_keywords': dict(sorted(keywords_count.items(), key=lambda x: x[1], reverse=True)[:10]),
        'entity_summary': entities_count,
        'generated_at': datetime.now().isoformat()
    }