# Event Ticket Pipeline

A Python pipeline that discovers ticketing platforms for events from Eventbrite Canada.

## Overview

This pipeline takes event names from Eventbrite Canada and discovers other legitimate ticket purchasing platforms where the same events are available.

## Project Structure

```
event_ticket_pipeline/
├── event_loader.py       # Load events from CSV or Python list
├── search_engine.py      # Web search for event tickets
├── platform_detector.py  # Detect ticketing platforms from results
├── event_matcher.py      # Fuzzy match events with search results
├── deduplicator.py       # Remove duplicate platform entries
├── csv_exporter.py       # Export to CSV formats
├── json_exporter.py      # Export to JSON format
├── main.py              # Main entry point
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Installation

```bash
cd event_ticket_pipeline
pip install -r requirements.txt
```

## Requirements

- requests>=2.28.0
- beautifulsoup4>=4.11.0
- pandas>=1.5.0
- rapidfuzz>=2.0.0 (optional, for better fuzzy matching)
- lxml>=4.9.0

## Usage

### Basic Usage with Event List

```bash
python main.py -e "Coldplay Music Of The Spheres Tour Toronto 2026" "AI Global Summit Vancouver 2026" --export-all
```

### Load from CSV

```bash
python main.py --input "../Data/deduplicated.csv" --event-column "Name" --export-all
```

### Full Options

```bash
python main.py \
  --input "events.csv" \
  --event-column "Name" \
  --output-dir "./output" \
  --concurrency 5 \
  --threshold 60.0 \
  --export-all
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-i, --input` | Input CSV file | None |
| `-e, --events` | Event names (space-separated) | None |
| `--event-column` | Column name for events in CSV | "Name" |
| `-o, --output-dir` | Output directory | Current dir |
| `-c, --concurrency` | Parallel workers | 5 |
| `--no-cache` | Disable search caching | False |
| `-t, --threshold` | Similarity threshold | 60.0 |
| `--export-csv` | Export to CSV | False |
| `--export-json` | Export to JSON | False |
| `--export-all` | Export to all formats | False |

## Output Files

### CSV Files

- `event_ticket_sites.csv` - Flat format with one row per platform
- `event_ticket_sites_grouped.csv` - Grouped format with platforms comma-separated

### JSON Files

- `events_ticket_data.json` - JSON format with event -> platforms mapping

## Supported Platforms

The pipeline detects these ticketing platforms:

- Ticketmaster (ticketmaster.ca, ticketmaster.com)
- StubHub (stubhub.ca)
- SeatGeek (seatgeek.com)
- AXS (axs.com)
- Eventbrite (eventbrite.ca, eventbrite.com)
- TicketWeb (ticketweb.ca, ticketweb.com)
- Showpass (showpass.com)
- Universe (universe.com)
- TicketLeap (ticketleap.com)
- Etix (etix.com)
- Brown Paper Tickets (brownpapertickets.com)
- Dice (dice.fm)
- SeeTickets (seetickets.com)
- Bandsintown (bandsintown.com)
- Songkick (songkick.com)

## Using with Search API (Recommended for Production)

For production use with 5000+ events, it's recommended to use a real search API:

### SerpAPI

```python
# In search_engine.py, replace search method with:
def search(self, query: str, use_cache: bool = True) -> List[Dict]:
    # Use SerpAPI
    params = {
        "api_key": "YOUR_SERPAPI_KEY",
        "q": query,
        "engine": "google",
        "gl": "ca",  # Canada
        "hl": "en"
    }
    response = requests.get("https://serpapi.com/search", params=params)
    # Parse results...
```

### Google Custom Search API

```python
# Use Google Custom Search JSON API
url = "https://www.googleapis.com/customsearch/v1"
params = {
    "key": "YOUR_API_KEY",
    "cx": "YOUR_CSE_ID",
    "q": query,
    "gl": "ca"
}
```

## Performance

- Handles 5000+ events with parallel processing
- Caches search results to avoid repeated queries
- Automatic retries for failed requests
- Fuzzy matching for event name variations

## License

MIT License
