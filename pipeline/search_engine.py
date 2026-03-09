import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
})


SERPAPI_KEY = "3dccdb2e3d94a9396f59f6aae8270e10c7448dfd0618648c4d6902da26689ef9"


class SearchEngine:
    """Handles web search queries for event ticket platforms."""
    
    def __init__(
        self,
        cache_dir: str = "search_cache",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 10.0,
        use_serpapi: bool = True,
        serpapi_key: str = None
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self._cache_hits = 0
        self._cache_misses = 0
        self.use_serpapi = use_serpapi
        self.serpapi_key = serpapi_key or SERPAPI_KEY
    
    def _get_cache_path(self, query: str) -> Path:
        """Get cache file path for a query."""
        safe_name = "".join(c if c.isalnum() else "_" for c in query.lower())[:50]
        return self.cache_dir / f"{safe_name}.json"
    
    def _load_from_cache(self, query: str) -> Optional[List[Dict]]:
        """Load search results from cache."""
        cache_path = self._get_cache_path(query)
        if cache_path.exists():
            try:
                with cache_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._cache_hits += 1
                    logger.debug(f"Cache hit for query: {query[:50]}")
                    return data.get("results")
            except Exception:
                pass
        self._cache_misses += 1
        return None
    
    def _save_to_cache(self, query: str, results: List[Dict]) -> None:
        """Save search results to cache."""
        cache_path = self._get_cache_path(query)
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"query": query, "results": results}, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def _make_request(self, url: str) -> Optional[str]:
        """Make HTTP request with retries."""
        for attempt in range(self.max_retries):
            try:
                response = SESSION.get(url, timeout=self.timeout, allow_redirects=True)
                if response.status_code == 200:
                    if "duckduckgo" in url and "html" in url:
                        if len(response.text) < 5000 or "DuckDuckGo" not in response.text:
                            logger.debug(f"DuckDuckGo returned minimal content, may be blocked")
                            continue
                    return response.text
                elif response.status_code == 429:
                    wait_time = self.retry_delay * (attempt + 1) * 2
                    logger.warning(f"Rate limited, waiting {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logger.debug(f"HTTP {response.status_code} for {url}")
            except requests.RequestException as e:
                logger.debug(f"Request error: {e}")
            time.sleep(self.retry_delay)
        return None
    
    def _extract_links_from_html(self, html: str, base_url: str) -> List[Dict]:
        """Extract links from HTML using BeautifulSoup."""
        results = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            for a_tag in soup.find_all("a", href=True):
                href = a_tag.get("href", "")
                text = a_tag.get_text(strip=True)
                
                if not href or href.startswith(("javascript:", "mailto:", "tel:")):
                    continue
                    
                if href.startswith("//"):
                    href = "https:" + href
                elif href.startswith("/"):
                    parsed = urlparse(base_url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
                
                if href.startswith("http"):
                    results.append({
                        "url": href,
                        "title": text or href
                    })
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
        
        return results
    
    def _search_serpapi(self, query: str) -> List[Dict]:
        """Search using SerpAPI (Google search results)."""
        results = []
        
        # Single query to conserve API credits (250 free searches limit)
        search_queries = [
            f'{query} tickets Canada',
        ]
        
        for sq in search_queries:
            try:
                params = {
                    "api_key": self.serpapi_key,
                    "q": sq,
                    "engine": "google",
                    "gl": "ca",
                    "hl": "en",
                    "num": 10
                }
                
                response = requests.get(
                    "https://serpapi.com/search",
                    params=params,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for item in data.get("organic_results", []):
                        link = item.get("link", "")
                        title = item.get("title", "")
                        if link:
                            results.append({
                                "url": link,
                                "title": title or link
                            })
                    
                    for item in data.get("shopping_results", []):
                        link = item.get("link", "")
                        title = item.get("title", "")
                        if link:
                            results.append({
                                "url": link,
                                "title": title or link
                            })
                            
                elif response.status_code == 403:
                    logger.error("SerpAPI key invalid or quota exceeded")
                    break
                else:
                    logger.debug(f"SerpAPI HTTP {response.status_code}")
                    
            except Exception as e:
                logger.debug(f"SerpAPI error for '{sq}': {e}")
        
        return results
    
    def _search_duckduckgo(self, query: str) -> List[Dict]:
        """Search using DuckDuckGo (fallback)."""
        results = []
        
        search_queries = [
            f'"{query}" tickets Canada',
            f'"{query}" buy tickets',
        ]
        
        for sq in search_queries:
            try:
                encoded_query = requests.utils.quote(sq)
                search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
                
                html = self._make_request(search_url)
                if html:
                    links = self._extract_links_from_html(html, search_url)
                    results.extend(links)
                    
            except Exception as e:
                logger.debug(f"Search error for '{sq}': {e}")
        
        return results
    
    def search(self, query: str, use_cache: bool = True) -> List[Dict]:
        """Search for event tickets using SerpAPI (primary) or DuckDuckGo (fallback)."""
        cached = self._load_from_cache(query) if use_cache else None
        if cached is not None:
            return cached
        
        results = []
        
        if self.use_serpapi and self.serpapi_key:
            logger.debug(f"Using SerpAPI for: {query[:30]}...")
            results = self._search_serpapi(query)
        
        if not results:
            logger.debug(f"Falling back to DuckDuckGo for: {query[:30]}...")
            results = self._search_duckduckgo(query)
        
        unique_results = self._deduplicate_results(results)
        self._save_to_cache(query, unique_results)
        
        logger.info(f"Search completed for '{query[:30]}...': {len(unique_results)} results")
        return unique_results
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate URLs from search results."""
        seen_urls: Set[str] = set()
        unique = []
        
        for r in results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(r)
        
        return unique
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total": self._cache_hits + self._cache_misses
        }
