import logging
from collections import defaultdict
from typing import Dict, List

logger = logging.getLogger(__name__)


def deduplicate_results(results: List[Dict]) -> List[Dict]:
    """Remove duplicate platform entries.
    
    Args:
        results: List of result dicts with 'platform', 'url', 'title'
        
    Returns:
        Deduplicated list
    """
    seen = set()
    unique = []
    
    for r in results:
        key = (r.get("platform", ""), r.get("url", ""))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    logger.debug(f"Deduplicated {len(results)} to {len(unique)} results")
    return unique


def deduplicate_by_platform(results: List[Dict]) -> Dict[str, List[Dict]]:
    """Group results by platform, keeping best URL for each.
    
    Args:
        results: List of result dicts
        
    Returns:
        Dict mapping platform name to list of results
    """
    platform_results = defaultdict(list)
    
    for r in results:
        platform = r.get("platform", "Unknown")
        platform_results[platform].append(r)
    
    deduplicated = {}
    for platform, items in platform_results.items():
        best_items = []
        seen_urls = set()
        
        sorted_items = sorted(
            items,
            key=lambda x: (
                0 if is_primary_url(x.get("url", "")) else 1,
                len(x.get("url", ""))
            )
        )
        
        for item in sorted_items:
            url = item.get("url", "")
            if url and url not in seen_urls:
                best_items.append(item)
                seen_urls.add(url)
        
        deduplicated[platform] = best_items
    
    return deduplicated


def is_primary_url(url: str) -> bool:
    """Check if URL is a primary ticket purchase page."""
    url_lower = url.lower()
    
    primary_patterns = [
        "/event/", "/e/", "/tickets/", "/buy/", "/checkout",
        "/listing/", "/show/"
    ]
    
    for pattern in primary_patterns:
        if pattern in url_lower:
            return True
    
    return False


def merge_event_results(
    all_results: Dict[str, List[Dict]]
) -> Dict[str, List[Dict]]:
    """Merge and deduplicate results across all events.
    
    Args:
        all_results: Dict mapping event names to their results
        
    Returns:
        Merged and deduplicated results
    """
    merged = {}
    
    for event_name, platforms in all_results.items():
        seen = set()
        unique = []
        
        for p in platforms:
            key = (p.get("platform", ""), p.get("url", ""))
            if key not in seen:
                seen.add(key)
                unique.append(p)
        
        merged[event_name] = unique
    
    return merged


class Deduplicator:
    """Handles deduplication of event-platform results."""
    
    def __init__(self):
        self._stats = {"input": 0, "output": 0}
    
    def deduplicate(self, results: List[Dict]) -> List[Dict]:
        """Deduplicate a list of results."""
        self._stats["input"] += len(results)
        unique = deduplicate_results(results)
        self._stats["output"] += len(unique)
        return unique
    
    def deduplicate_all(
        self,
        all_results: Dict[str, List[Dict]]
    ) -> Dict[str, List[Dict]]:
        """Deduplicate results for all events."""
        merged = {}
        
        for event_name, platforms in all_results.items():
            merged[event_name] = self.deduplicate(platforms)
        
        return merged
    
    def get_stats(self) -> Dict:
        """Get deduplication statistics."""
        return self._stats.copy()
