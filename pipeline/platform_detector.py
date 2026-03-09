import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

TICKETING_PLATFORMS = {
    "ticketmaster.ca": "Ticketmaster",
    "ticketmaster.com": "Ticketmaster",
    "stubhub.ca": "StubHub",
    "stubhub.com": "StubHub",
    "seatgeek.ca": "SeatGeek",
    "seatgeek.com": "SeatGeek",
    "axs.com": "AXS",
    "axs.ca": "AXS",
    "eventbrite.ca": "Eventbrite",
    "eventbrite.com": "Eventbrite",
    "ticketweb.ca": "TicketWeb",
    "ticketweb.com": "TicketWeb",
    "showpass.com": "Showpass",
    "universe.com": "Universe",
    "ticketleap.com": "TicketLeap",
    "etix.com": "Etix",
    "brownpapertickets.com": "Brown Paper Tickets",
    "dice.fm": "Dice",
    "seetickets.com": "SeeTickets",
    "bandsintown.com": "Bandsintown",
    "songkick.com": "Songkick",
    "ticketfly.com": "Ticketfly",
    "frontgatetickets.com": "Frontgate Tickets",
    "evenue.net": "Evenue",
    "ticketsnow.com": "TicketsNow",
    "ticketnetwork.com": "TicketNetwork",
    "ticketliquidator.com": "Ticket Liquidator",
    "ticketexchangebeat.com": "Ticket Exchange",
    "northeasttickets.com": "Northeast Tickets",
    "viagogo.com": "Viagogo",
    "ticketgalaxy.com": "TicketGalaxy",
    "razorgangtickets.com": "Razorgang Tickets",
    "premiumseats.com": "Premium Seats",
    "livenation.com": "Live Nation",
    "ticket.ca": "Tickets.ca",
    "tickets.ca": "Tickets.ca",
}

TICKET_KEYWORDS = [
    "ticket", "tickets", "buy", "purchase", "checkout", 
    "register", "rsvp", "book", "event", "schedule",
    "concerts", "festival", "show", "performance"
]


def normalize_domain(url: str) -> Optional[str]:
    """Extract and normalize domain from URL or domain string."""
    try:
        if not url:
            return None
            
        url_lower = url.lower().strip()
        
        if not url_lower.startswith(('http://', 'https://')):
            if '.' in url_lower:
                return url_lower
            return None
            
        parsed = urlparse(url_lower)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else None
    except Exception:
        return None


def get_platform_name(domain: str) -> Optional[str]:
    """Get platform name from domain."""
    normalized = normalize_domain(domain)
    if not normalized:
        return None
    
    for platform_domain, platform_name in TICKETING_PLATFORMS.items():
        if platform_domain in normalized or normalized in platform_domain:
            return platform_name
    
    return None


def is_ticket_url(url: str) -> bool:
    """Check if URL likely points to a ticket purchasing page."""
    normalized = url.lower()
    
    for keyword in TICKET_KEYWORDS:
        if keyword in normalized:
            return True
    
    return False


def is_valid_ticket_url(url: str) -> bool:
    """Validate if URL is a legitimate ticket URL."""
    if not url or not url.startswith("http"):
        return False
    
    normalized = normalize_domain(url)
    if not normalized:
        return False
    
    blocked_patterns = [
        r"facebook\.com", r"twitter\.com", r"instagram\.com",
        r"youtube\.com", r"linkedin\.com", r"reddit\.com",
        r"google\.com", r"wikipedia\.org", r"amazon\.co",
    ]
    
    for pattern in blocked_patterns:
        if re.search(pattern, normalized):
            return False
    
    if get_platform_name(normalized):
        return True
    
    return is_ticket_url(url)


class PlatformDetector:
    """Detects ticketing platforms from search results."""
    
    def __init__(self):
        self.platforms = TICKETING_PLATFORMS
        self._stats = {"total_checked": 0, "platforms_found": 0}
    
    def detect_platforms(self, search_results: List[Dict]) -> List[Dict]:
        """Detect ticketing platforms from search results.
        
        Args:
            search_results: List of dicts with 'url' and 'title' keys
            
        Returns:
            List of detected platforms with their URLs
        """
        detected = []
        seen_urls = set()
        
        for result in search_results:
            url = result.get("url", "")
            title = result.get("title", "")
            
            if not url or url in seen_urls:
                continue
            
            self._stats["total_checked"] += 1
            
            domain = normalize_domain(url)
            if not domain:
                continue
            
            platform_name = get_platform_name(domain)
            
            if platform_name and is_valid_ticket_url(url):
                detected.append({
                    "platform": platform_name,
                    "url": url,
                    "domain": domain,
                    "title": title
                })
                seen_urls.add(url)
                self._stats["platforms_found"] += 1
                logger.debug(f"Found platform: {platform_name} at {url}")
        
        return detected
    
    def get_unique_platforms(self, platforms: List[Dict]) -> List[Dict]:
        """Get unique platforms, preferring official ticket URLs."""
        seen = set()
        unique = []
        
        sorted_platforms = sorted(
            platforms,
            key=lambda x: (
                0 if is_official_ticket_url(x.get("url", "")) else 1,
                x.get("platform", "")
            )
        )
        
        for p in sorted_platforms:
            key = (p.get("platform", ""), p.get("domain", ""))
            if key not in seen:
                seen.add(key)
                unique.append(p)
        
        return unique
    
    def get_stats(self) -> Dict:
        """Get detection statistics."""
        return self._stats.copy()


def is_official_ticket_url(url: str) -> bool:
    """Check if URL is an official ticket purchasing page."""
    normalized = url.lower()
    
    official_patterns = [
        r"ticketmaster\.(ca|com)/event/",
        r"stubhub\.(ca|com)/event/",
        r"seatgeek\.com/listing/",
        r"axs\.com/events/",
        r"eventbrite\.(ca|com)/e/",
        r"showpass\.com/",
        r"universe\.com/events/",
        r"ticketleap\.com/",
    ]
    
    for pattern in official_patterns:
        if re.search(pattern, normalized):
            return True
    
    return False
