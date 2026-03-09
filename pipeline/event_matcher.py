import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz not installed, using simple matching")


def normalize_event_name(name: str) -> str:
    """Normalize event name for comparison."""
    if not name:
        return ""
    
    normalized = name.lower()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    
    return normalized


def simple_similarity(s1: str, s2: str) -> float:
    """Simple string similarity without rapidfuzz."""
    if not s1 or not s2:
        return 0.0
    
    n1, n2 = normalize_event_name(s1), normalize_event_name(s2)
    
    if n1 == n2:
        return 100.0
    
    if n1 in n2 or n2 in n1:
        return 80.0
    
    words1 = set(n1.split())
    words2 = set(n2.split())
    
    if not words1 or not words2:
        return 0.0
    
    common = words1 & words2
    total = words1 | words2
    
    return (len(common) / len(total)) * 100


def calculate_similarity(event_name: str, result_title: str) -> float:
    """Calculate similarity between event name and search result title.
    
    Args:
        event_name: Original event name from Eventbrite
        result_title: Title from search result
        
    Returns:
        Similarity score (0-100)
    """
    if RAPIDFUZZ_AVAILABLE:
        score = fuzz.token_set_ratio(
            normalize_event_name(event_name),
            normalize_event_name(result_title)
        )
        return score
    else:
        return simple_similarity(event_name, result_title)


def is_matching_event(
    event_name: str,
    result_title: str,
    result_url: str,
    threshold: float = 60.0
) -> bool:
    """Check if search result matches the event.
    
    Args:
        event_name: Original event name
        result_title: Title from search result
        result_url: URL from search result
        threshold: Minimum similarity score (default 60)
        
    Returns:
        True if event matches
    """
    if not event_name or not (result_title or result_url):
        return False
    
    title_score = calculate_similarity(event_name, result_title)
    
    if title_score >= threshold:
        return True
    
    if result_url:
        url_score = calculate_similarity(event_name, result_url)
        if url_score >= threshold:
            return True
    
    return False


def filter_matching_results(
    event_name: str,
    search_results: List[Dict],
    threshold: float = 60.0
) -> List[Dict]:
    """Filter search results to only those matching the event.
    
    Args:
        event_name: Original event name
        search_results: List of search result dicts
        threshold: Minimum similarity score
        
    Returns:
        Filtered list of matching results
    """
    matches = []
    
    for result in search_results:
        title = result.get("title", "")
        url = result.get("url", "")
        
        if is_matching_event(event_name, title, url, threshold):
            matches.append(result)
    
    logger.debug(
        f"Matched {len(matches)}/{len(search_results)} results "
        f"for '{event_name[:30]}...' (threshold: {threshold})"
    )
    
    return matches


class EventMatcher:
    """Matches search results to events using fuzzy matching."""
    
    def __init__(self, threshold: float = 60.0):
        self.threshold = threshold
        self._match_count = 0
        self._total_checked = 0
    
    def match(
        self,
        event_name: str,
        search_results: List[Dict]
    ) -> List[Dict]:
        """Match search results to an event.
        
        Args:
            event_name: Event name to match against
            search_results: Search results to filter
            
        Returns:
            List of matching results
        """
        self._total_checked += len(search_results)
        
        matches = filter_matching_results(
            event_name,
            search_results,
            self.threshold
        )
        
        self._match_count += len(matches)
        
        return matches
    
    def get_stats(self) -> Dict:
        """Get matching statistics."""
        return {
            "total_checked": self._total_checked,
            "matches_found": self._match_count,
            "match_rate": (
                self._match_count / self._total_checked * 100
                if self._total_checked > 0 else 0
            )
        }
