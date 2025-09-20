"""
DARKNEXT - Content Parser Module
Handles keyword matching and entity extraction from crawled content
"""

import logging
import re
from typing import Dict, List, Set, Tuple
from datetime import datetime


class ContentParser:
    """Parses crawled content for keywords and entities"""
    
    def __init__(self, config: Dict, keywords_file: str):
        """Initialize the content parser"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.keywords = self._load_keywords(keywords_file)
        
        # Compile regex patterns for entity extraction
        self._compile_patterns()
        
    def _load_keywords(self, filepath: str) -> Set[str]:
        """Load keywords from file"""
        keywords = set()
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        keywords.add(line.lower())
            
            self.logger.info(f"Loaded {len(keywords)} keywords")
            return keywords
            
        except FileNotFoundError:
            self.logger.error(f"Keywords file not found: {filepath}")
            return set()
        except Exception as e:
            self.logger.error(f"Error loading keywords: {str(e)}")
            return set()
    
    def _compile_patterns(self):
        """Compile regex patterns for entity extraction"""
        # Email pattern
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
        # Bitcoin address patterns
        self.btc_legacy_pattern = re.compile(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b')
        self.btc_segwit_pattern = re.compile(r'\bbc1[a-z0-9]{39,59}\b')
        
        # Ethereum address pattern
        self.eth_pattern = re.compile(r'\b0x[a-fA-F0-9]{40}\b')
        
        # Monero address pattern
        self.xmr_pattern = re.compile(r'\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b')
        
        # PGP key pattern
        self.pgp_pattern = re.compile(
            r'-----BEGIN PGP (?:PUBLIC|PRIVATE) KEY BLOCK-----.*?-----END PGP (?:PUBLIC|PRIVATE) KEY BLOCK-----',
            re.DOTALL
        )
        
        # Phone number pattern (various formats)
        self.phone_pattern = re.compile(
            r'(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'
        )
        
        # Credit card pattern (basic)
        self.cc_pattern = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')
        
        # IP address pattern
        self.ip_pattern = re.compile(
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        )
        
        # URL pattern
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        # SSH key pattern
        self.ssh_key_pattern = re.compile(
            r'ssh-(?:rsa|dss|ed25519) [A-Za-z0-9+/]+=*'
        )
        
        # API key patterns (common formats)
        self.api_key_patterns = [
            re.compile(r'api[_-]?key[\'"]?\s*[:=]\s*[\'"]?([A-Za-z0-9_-]{20,})[\'"]?', re.IGNORECASE),
            re.compile(r'token[\'"]?\s*[:=]\s*[\'"]?([A-Za-z0-9_.-]{20,})[\'"]?', re.IGNORECASE),
            re.compile(r'secret[\'"]?\s*[:=]\s*[\'"]?([A-Za-z0-9_.-]{20,})[\'"]?', re.IGNORECASE),
        ]
    
    def parse_content(self, page_data: Dict) -> Dict:
        """Parse page content for keywords and entities"""
        content = page_data.get('content', '').lower()
        url = page_data.get('url', '')
        
        # Find keyword matches
        keyword_matches = self._find_keyword_matches(content)
        
        # Extract entities if enabled
        entities = {}
        if self.config.get('content', {}).get('extract_entities', True):
            entities = self._extract_entities(page_data.get('content', ''))
        
        # Create result
        result = {
            'url': url,
            'title': page_data.get('title', ''),
            'timestamp': page_data.get('timestamp', datetime.now().timestamp()),
            'keyword_matches': keyword_matches,
            'entities': entities,
            'content_snippet': self._create_snippet(page_data.get('content', ''), keyword_matches),
            'content_length': page_data.get('content_length', 0),
            'has_matches': len(keyword_matches) > 0 or any(entities.values())
        }
        
        return result
    
    def _find_keyword_matches(self, content: str) -> List[Dict]:
        """Find keyword matches in content"""
        matches = []
        
        for keyword in self.keywords:
            # Use word boundaries for more accurate matching
            pattern = rf'\b{re.escape(keyword)}\b'
            found_matches = list(re.finditer(pattern, content, re.IGNORECASE))
            
            for match in found_matches:
                matches.append({
                    'keyword': keyword,
                    'position': match.start(),
                    'context': self._get_context(content, match.start(), match.end())
                })
        
        return matches
    
    def _extract_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract various entities from content"""
        entities = {
            'emails': [],
            'bitcoin_addresses': [],
            'ethereum_addresses': [],
            'monero_addresses': [],
            'phone_numbers': [],
            'credit_cards': [],
            'ip_addresses': [],
            'urls': [],
            'ssh_keys': [],
            'pgp_keys': [],
            'api_keys': []
        }
        
        # Extract emails
        entities['emails'] = list(set(self.email_pattern.findall(content)))
        
        # Extract Bitcoin addresses
        btc_legacy = self.btc_legacy_pattern.findall(content)
        btc_segwit = self.btc_segwit_pattern.findall(content)
        entities['bitcoin_addresses'] = list(set(btc_legacy + btc_segwit))
        
        # Extract Ethereum addresses
        entities['ethereum_addresses'] = list(set(self.eth_pattern.findall(content)))
        
        # Extract Monero addresses
        entities['monero_addresses'] = list(set(self.xmr_pattern.findall(content)))
        
        # Extract phone numbers
        entities['phone_numbers'] = list(set(self.phone_pattern.findall(content)))
        
        # Extract credit card numbers (be careful with false positives)
        cc_matches = self.cc_pattern.findall(content)
        # Basic validation to reduce false positives
        entities['credit_cards'] = [cc for cc in cc_matches if self._is_valid_cc_format(cc)]
        
        # Extract IP addresses
        ip_matches = self.ip_pattern.findall(content)
        entities['ip_addresses'] = [ip for ip in ip_matches if self._is_valid_ip(ip)]
        
        # Extract URLs
        entities['urls'] = list(set(self.url_pattern.findall(content)))
        
        # Extract SSH keys
        entities['ssh_keys'] = list(set(self.ssh_key_pattern.findall(content)))
        
        # Extract PGP keys
        entities['pgp_keys'] = list(set(self.pgp_pattern.findall(content)))
        
        # Extract API keys
        api_keys = []
        for pattern in self.api_key_patterns:
            matches = pattern.findall(content)
            api_keys.extend(matches)
        entities['api_keys'] = list(set(api_keys))
        
        # Remove empty lists
        entities = {k: v for k, v in entities.items() if v}
        
        return entities
    
    def _get_context(self, content: str, start: int, end: int, context_length: int = 100) -> str:
        """Get context around a match"""
        context_start = max(0, start - context_length)
        context_end = min(len(content), end + context_length)
        
        context = content[context_start:context_end]
        
        # Add ellipsis if truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(content):
            context = context + "..."
            
        return context.strip()
    
    def _create_snippet(self, content: str, keyword_matches: List[Dict], max_length: int = 500) -> str:
        """Create a content snippet highlighting matches"""
        if not keyword_matches:
            return content[:max_length] + ("..." if len(content) > max_length else "")
        
        # Get context around the first match
        first_match = keyword_matches[0]
        position = first_match['position']
        
        start = max(0, position - max_length // 2)
        end = min(len(content), start + max_length)
        
        snippet = content[start:end]
        
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
            
        return snippet.strip()
    
    def _is_valid_cc_format(self, cc: str) -> bool:
        """Basic credit card format validation"""
        # Remove spaces and hyphens
        cc_clean = re.sub(r'[-\s]', '', cc)
        
        # Check if it's all digits and correct length
        if not cc_clean.isdigit():
            return False
        
        length = len(cc_clean)
        # Common credit card lengths: 13-19 digits
        return 13 <= length <= 19
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        try:
            for part in parts:
                num = int(part)
                if not (0 <= num <= 255):
                    return False
            return True
        except ValueError:
            return False
    
    def get_statistics(self, parsed_results: List[Dict]) -> Dict:
        """Get statistics from parsed results"""
        stats = {
            'total_pages': len(parsed_results),
            'pages_with_matches': sum(1 for r in parsed_results if r['has_matches']),
            'total_keyword_matches': sum(len(r['keyword_matches']) for r in parsed_results),
            'keyword_frequency': {},
            'entity_counts': {},
            'unique_entities': set()
        }
        
        # Count keyword frequencies
        for result in parsed_results:
            for match in result['keyword_matches']:
                keyword = match['keyword']
                stats['keyword_frequency'][keyword] = stats['keyword_frequency'].get(keyword, 0) + 1
        
        # Count entities
        for result in parsed_results:
            for entity_type, entities in result['entities'].items():
                if entity_type not in stats['entity_counts']:
                    stats['entity_counts'][entity_type] = 0
                stats['entity_counts'][entity_type] += len(entities)
                
                # Add to unique entities
                for entity in entities:
                    stats['unique_entities'].add(f"{entity_type}:{entity}")
        
        stats['unique_entities'] = len(stats['unique_entities'])
        
        return stats