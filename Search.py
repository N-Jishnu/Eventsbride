import time
import random
import requests
import csv

# -------------------------------
# 1. Force real browser headers
# -------------------------------
requests.utils.default_headers = lambda: {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}

# ------------------------------------------------
# 2. Monkey-patch requests to slow every request
# ------------------------------------------------
_old_request = requests.sessions.Session.request

def slow_request(self, method, url, **kwargs):
    time.sleep(random.uniform(2.5, 4.5))
    return _old_request(self, method, url, **kwargs)

requests.sessions.Session.request = slow_request

# -------------------------------
# 3. Run Eventbrite scraper
# -------------------------------
from eventbrite_scrapper import Eventbrite

client = Eventbrite()

events = client.search_events.get_results(
    region="canada--halton",
    dt_start="2026-02-01",
    dt_end="2026-02-28",   # wider range = more events
    max_pages=3,
)

print(f"\nTotal events scraped: {len(events)}\n")

# -------------------------------
# 4. Save to CSV (extended fields)
# -------------------------------
csv_filename = "halton_events.csv"

with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)

    # Header
    writer.writerow([
        "Event Name",
        "Start Date",
        "Event URL",
        "Poster/Image URL",
        "Venue",
        "Organizer"
    ])

    # Rows
    for event in events:
        writer.writerow([
            event.name,
            event.start_datetime,
            event.url,
            getattr(event, "image_url", None),
            getattr(event, "venue_name", None),
            getattr(event, "organizer_name", None),
        ])

print(f"Data saved to {csv_filename}")

# -------------------------------
# 5. Optional console preview
# -------------------------------
for i, event in enumerate(events, start=1):
    print(f"{i}. {event.name}")
    print(f"   Date      : {event.start_datetime}")
    print(f"   Venue     : {getattr(event, 'venue_name', 'N/A')}")
    print(f"   Organizer : {getattr(event, 'organizer_name', 'N/A')}")
    print(f"   Image URL : {getattr(event, 'image_url', 'N/A')}")
    print(f"   URL       : {event.url}")
    print("-" * 60)
