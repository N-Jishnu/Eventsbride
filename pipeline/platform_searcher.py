"""
Direct Platform Search Module with Headless Browser

Uses Selenium to scrape ticketing platforms with JavaScript rendering.
"""

import logging
import time
from typing import Dict, List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

PLATFORMS = {
    "ticketmaster": {
        "name": "Ticketmaster",
        "domain": "ticketmaster.ca",
        "search_url": "https://www.ticketmaster.ca/search?q={query}",
        "wait_selector": "a[href*='/event/']",
    },
    "stubhub": {
        "name": "StubHub",
        "domain": "stubhub.ca",
        "search_url": "https://www.stubhub.ca/search?q={query}",
        "wait_selector": "a[href*='/event/']",
    },
    "seatgeek": {
        "name": "SeatGeek",
        "domain": "seatgeek.ca",
        "search_url": "https://seatgeek.ca/search?query={query}",
        "wait_selector": "a[href*='/listing/']",
    },
    "showpass": {
        "name": "Showpass",
        "domain": "showpass.com",
        "search_url": "https://www.showpass.com/search/?q={query}",
        "wait_selector": "a[href*='/event/']",
    },
    "universe": {
        "name": "Universe",
        "domain": "universe.com",
        "search_url": "https://www.universe.com/search/?q={query}",
        "wait_selector": "a[href*='/events/']",
    },
    "livenation": {
        "name": "Live Nation",
        "domain": "livenation.com",
        "search_url": "https://www.livenation.com/search?q={query}",
        "wait_selector": "a[href*='/event/']",
    },
    "ticketmastercom": {
        "name": "Ticketmaster",
        "domain": "ticketmaster.com",
        "search_url": "https://www.ticketmaster.com/search?q={query}",
        "wait_selector": "a[href*='/event/']",
    },
}


def create_driver() -> webdriver.Chrome:
    """Create a headless Chrome driver."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        driver = webdriver.Chrome(options=options)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    
    return driver


def extract_links_from_page(driver: webdriver.Chrome, platform_info: Dict) -> List[Dict]:
    """Extract event links from the current page using Selenium."""
    results = []
    
    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        base_url = driver.current_url
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            text = a_tag.get_text(strip=True)
            
            if not href:
                continue
            
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                parsed = __import__("urllib.parse", fromlist=["urlparse"]).urlparse(base_url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            
            if href.startswith("http") and "event" in href.lower():
                results.append({
                    "url": href,
                    "title": text or href,
                    "platform": platform_info["name"],
                    "domain": platform_info["domain"],
                })
                
    except Exception as e:
        logger.debug(f"Error extracting links: {e}")
    
    return results


def search_platform(driver: webdriver.Chrome, platform_key: str, event_name: str) -> List[Dict]:
    """Search a single platform for an event."""
    if platform_key not in PLATFORMS:
        return []
    
    platform = PLATFORMS[platform_key]
    query = quote(event_name)
    url = platform["search_url"].format(query=query)
    
    results = []
    
    try:
        logger.debug(f"Searching {platform_key} for: {event_name[:30]}...")
        driver.get(url)
        
        time.sleep(2)
        
        wait = WebDriverWait(driver, 10)
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        except Exception:
            pass
        
        time.sleep(1)
        
        results = extract_links_from_page(driver, platform)
        logger.debug(f"  {platform_key}: {len(results)} results")
        
    except Exception as e:
        logger.debug(f"Error searching {platform_key}: {e}")
    
    return results


def search_all_platforms(event_name: str, delay: float = 1.0, driver=None) -> List[Dict]:
    """Search all platforms for an event using headless browser.
    
    Args:
        event_name: Name of event to search for
        delay: Delay between platform requests
        driver: Optional existing WebDriver instance to reuse
        
    Returns:
        List of dicts with url, title, platform, domain
    """
    all_results = []
    own_driver = False
    
    try:
        if driver is None:
            driver = create_driver()
            own_driver = True
        
        for platform_key in PLATFORMS.keys():
            try:
                results = search_platform(driver, platform_key, event_name)
                all_results.extend(results)
                time.sleep(delay)
            except Exception as e:
                logger.debug(f"Error on {platform_key}: {e}")
                
    except Exception as e:
        logger.error(f"Driver error: {e}")
    finally:
        if own_driver and driver:
            try:
                driver.quit()
            except Exception:
                pass
    
    return all_results


def deduplicate_links(results: List[Dict]) -> List[Dict]:
    """Remove duplicate URLs."""
    seen = set()
    unique = []
    
    for r in results:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)
    
    return unique
