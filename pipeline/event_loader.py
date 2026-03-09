import csv
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def load_events_from_csv(csv_path: str, event_name_column: str = "Name") -> List[str]:
    """Load event names from a CSV file.
    
    Args:
        csv_path: Path to the CSV file containing events
        event_name_column: Name of the column containing event names
        
    Returns:
        List of event names
    """
    events = []
    path = Path(csv_path)
    
    if not path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return events
    
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    event_name = row.get(event_name_column, "").strip()
                    if event_name:
                        events.append(event_name)
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            continue
    
    logger.info(f"Loaded {len(events)} events from {csv_path}")
    return events


def load_events_from_list(events_list: List[str]) -> List[str]:
    """Load event names from a Python list.
    
    Args:
        events_list: List of event names
        
    Returns:
        List of cleaned event names
    """
    events = [e.strip() for e in events_list if e and e.strip()]
    logger.info(f"Loaded {len(events)} events from list")
    return events


def load_events(
    source: Optional[str] = None,
    events_list: Optional[List[str]] = None,
    event_name_column: str = "Name"
) -> List[str]:
    """Load events from either a CSV file or a Python list.
    
    Args:
        source: Path to CSV file (if loading from file)
        events_list: List of event names (if loading from list)
        event_name_column: Column name for CSV source
        
    Returns:
        List of event names
    """
    if source:
        return load_events_from_csv(source, event_name_column)
    elif events_list:
        return load_events_from_list(events_list)
    else:
        logger.error("Either source or events_list must be provided")
        return []
