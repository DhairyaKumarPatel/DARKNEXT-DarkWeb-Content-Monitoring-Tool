"""
DARKNEXT - Tor-based Web Crawler Module
Handles crawling of .onion sites through Tor proxy
"""

import asyncio
import logging
import random
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup


class TorCrawler:
    """Tor-based web crawler for .onion sites"""
    
    def __init__(self, config: Dict):
        """Initialize the Tor crawler with configuration"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Tor proxy settings
        self.tor_proxy = {
            'http': f"socks5h://{config['tor']['proxy_host']}:{config['tor']['proxy_port']}",
            'https': f"socks5h://{config['tor']['proxy_host']}:{config['tor']['proxy_port']}"
        }
        
        # Session configuration
        self.session = None
        self.setup_session()
        
    def setup_session(self):
        """Setup requests session with Tor proxy"""
        self.session = requests.Session()
        self.session.proxies.update(self.tor_proxy)
        
        # Set headers to appear more legitimate
        headers = self.config.get('security', {}).get('request_headers', {})
        if headers:
            self.session.headers.update(headers)
            
        # Add user agent
        if 'user_agent' in self.config.get('crawler', {}):
            self.session.headers['User-Agent'] = self.config['crawler']['user_agent']
            
    def test_tor_connection(self) -> bool:
        """Test if Tor connection is working"""
        try:
            # Try to connect to a known .onion site or Tor check service
            response = self.session.get(
                'http://httpbin.org/ip',  # This will show our IP through Tor
                timeout=self.config['tor']['timeout']
            )
            
            if response.status_code == 200:
                ip_data = response.json()
                self.logger.info(f"Tor connection successful. Current IP: {ip_data.get('origin', 'Unknown')}")
                return True
            else:
                self.logger.error(f"Tor connection test failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Tor connection test failed: {str(e)}")
            return False
    
    def crawl_page(self, url: str) -> Optional[Dict]:
        """Crawl a single page and return content data"""
        try:
            self.logger.info(f"Crawling: {url}")
            
            # Add random delay to avoid detection
            delay = self.config.get('crawler', {}).get('delay_between_requests', 5)
            time.sleep(random.uniform(delay * 0.5, delay * 1.5))
            
            response = self.session.get(
                url,
                timeout=self.config.get('crawler', {}).get('page_timeout', 60)
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Non-200 response from {url}: {response.status_code}")
                return None
            
            # Check content length
            max_length = self.config.get('content', {}).get('max_content_length', 1048576)
            if len(response.content) > max_length:
                self.logger.warning(f"Page too large, truncating: {url}")
                content = response.text[:max_length]
            else:
                content = response.text
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract text content
            text_content = soup.get_text(separator=' ', strip=True)
            
            # Check minimum content length
            min_length = self.config.get('content', {}).get('min_content_length', 100)
            if len(text_content) < min_length:
                self.logger.info(f"Page content too short, skipping: {url}")
                return None
            
            # Extract links for further crawling
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(url, href)
                if self._is_valid_onion_url(full_url):
                    links.append(full_url)
            
            return {
                'url': url,
                'status_code': response.status_code,
                'content': text_content,
                'raw_html': content,
                'title': soup.title.string if soup.title else '',
                'links': links,
                'headers': dict(response.headers),
                'timestamp': time.time(),
                'content_length': len(content)
            }
            
        except requests.exceptions.Timeout:
            self.logger.warning(f"Timeout crawling {url}")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.warning(f"Connection error crawling {url}")
            return None
        except Exception as e:
            self.logger.error(f"Error crawling {url}: {str(e)}")
            return None
    
    def crawl_site(self, base_url: str) -> List[Dict]:
        """Crawl multiple pages from a site"""
        results = []
        visited_urls = set()
        urls_to_visit = [base_url]
        
        max_pages = self.config.get('crawler', {}).get('max_pages_per_site', 10)
        
        while urls_to_visit and len(results) < max_pages:
            url = urls_to_visit.pop(0)
            
            if url in visited_urls:
                continue
                
            visited_urls.add(url)
            
            page_data = self.crawl_page(url)
            if page_data:
                results.append(page_data)
                
                # Add new links to crawl (from same domain)
                for link in page_data.get('links', []):
                    if (link not in visited_urls and 
                        link not in urls_to_visit and
                        self._same_domain(base_url, link)):
                        urls_to_visit.append(link)
        
        self.logger.info(f"Crawled {len(results)} pages from {base_url}")
        return results
    
    def crawl_urls_from_file(self, filepath: str) -> List[Dict]:
        """Crawl URLs listed in a file"""
        all_results = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f 
                       if line.strip() and not line.strip().startswith('#')]
            
            self.logger.info(f"Found {len(urls)} URLs to crawl")
            
            for url in urls:
                if self._is_valid_onion_url(url):
                    self.logger.info(f"Starting crawl of {url}")
                    site_results = self.crawl_site(url)
                    all_results.extend(site_results)
                else:
                    self.logger.warning(f"Invalid .onion URL: {url}")
                    
        except FileNotFoundError:
            self.logger.error(f"URL file not found: {filepath}")
        except Exception as e:
            self.logger.error(f"Error reading URL file: {str(e)}")
        
        return all_results
    
    def _is_valid_onion_url(self, url: str) -> bool:
        """Check if URL is a valid .onion URL"""
        try:
            parsed = urlparse(url)
            return (parsed.scheme in ['http', 'https'] and 
                   parsed.netloc.endswith('.onion'))
        except:
            return False
    
    def _same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain"""
        try:
            domain1 = urlparse(url1).netloc
            domain2 = urlparse(url2).netloc
            return domain1 == domain2
        except:
            return False
    
    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()


class AsyncTorCrawler:
    """Asynchronous version of TorCrawler for better performance"""
    
    def __init__(self, config: Dict):
        """Initialize the async Tor crawler"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Tor proxy settings for aiohttp
        self.proxy = f"socks5://{config['tor']['proxy_host']}:{config['tor']['proxy_port']}"
        
    async def crawl_page_async(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        """Asynchronously crawl a single page"""
        try:
            self.logger.info(f"Async crawling: {url}")
            
            # Add random delay
            delay = self.config.get('crawler', {}).get('delay_between_requests', 5)
            await asyncio.sleep(random.uniform(delay * 0.5, delay * 1.5))
            
            timeout = aiohttp.ClientTimeout(
                total=self.config.get('crawler', {}).get('page_timeout', 60)
            )
            
            async with session.get(url, timeout=timeout, proxy=self.proxy) as response:
                if response.status != 200:
                    self.logger.warning(f"Non-200 response from {url}: {response.status}")
                    return None
                
                content = await response.text()
                
                # Check content length
                max_length = self.config.get('content', {}).get('max_content_length', 1048576)
                if len(content) > max_length:
                    content = content[:max_length]
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                text_content = soup.get_text(separator=' ', strip=True)
                
                # Check minimum content length
                min_length = self.config.get('content', {}).get('min_content_length', 100)
                if len(text_content) < min_length:
                    return None
                
                return {
                    'url': url,
                    'status_code': response.status,
                    'content': text_content,
                    'raw_html': content,
                    'title': soup.title.string if soup.title else '',
                    'headers': dict(response.headers),
                    'timestamp': time.time(),
                    'content_length': len(content)
                }
                
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout crawling {url}")
            return None
        except Exception as e:
            self.logger.error(f"Error async crawling {url}: {str(e)}")
            return None
    
    async def crawl_urls_async(self, urls: List[str]) -> List[Dict]:
        """Asynchronously crawl multiple URLs"""
        headers = self.config.get('security', {}).get('request_headers', {})
        if 'user_agent' in self.config.get('crawler', {}):
            headers['User-Agent'] = self.config['crawler']['user_agent']
        
        connector = aiohttp.TCPConnector(limit=self.config.get('crawler', {}).get('max_concurrent_requests', 3))
        
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            tasks = [self.crawl_page_async(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None results and exceptions
            valid_results = [r for r in results if r is not None and not isinstance(r, Exception)]
            
            return valid_results