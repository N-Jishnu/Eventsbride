import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def export_to_json(
    results: Dict[str, List[Dict]],
    output_path: str,
    indent: int = 2
) -> int:
    """Export results to JSON file.
    
    Args:
        results: Dict mapping event names to platform results
        output_path: Path to output JSON file
        indent: JSON indentation level
        
    Returns:
        Number of events exported
    """
    formatted = {}
    
    for event_name, platforms in results.items():
        if platforms:
            formatted[event_name] = [
                {
                    "platform": p.get("platform", ""),
                    "url": p.get("url", "")
                }
                for p in platforms
            ]
        else:
            formatted[event_name] = []
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with path.open("w", encoding="utf-8") as f:
        json.dump(formatted, f, indent=indent, ensure_ascii=False)
    
    logger.info(f"Exported {len(formatted)} events to {output_path}")
    return len(formatted)


def export_to_json_pretty(
    results: Dict[str, List[Dict]],
    output_path: str
) -> int:
    """Export results to pretty-printed JSON file.
    
    Args:
        results: Dict mapping event names to platform results
        output_path: Path to output JSON file
        
    Returns:
        Number of events exported
    """
    return export_to_json(results, output_path, indent=2)


def export_to_json_compact(
    results: Dict[str, List[Dict]],
    output_path: str
) -> int:
    """Export results to compact JSON file (no indentation).
    
    Args:
        results: Dict mapping event names to platform results
        output_path: Path to output JSON file
        
    Returns:
        Number of events exported
    """
    return export_to_json(results, output_path, indent=None)


def export_with_summary(
    results: Dict[str, List[Dict]],
    output_path: str
) -> int:
    """Export results to JSON with summary statistics.
    
    Args:
        results: Dict mapping event names to platform results
        output_path: Path to output JSON file
        
    Returns:
        Number of events exported
    """
    total_events = len(results)
    events_with_tickets = sum(1 for platforms in results.values() if platforms)
    events_without_tickets = total_events - events_with_tickets
    
    platform_counts: Dict[str, int] = {}
    for platforms in results.values():
        for p in platforms:
            platform = p.get("platform", "Unknown")
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
    
    output = {
        "summary": {
            "total_events": total_events,
            "events_with_tickets": events_with_tickets,
            "events_without_tickets": events_without_tickets,
            "platform_counts": platform_counts
        },
        "events": {}
    }
    
    for event_name, platforms in results.items():
        if platforms:
            output["events"][event_name] = [
                {
                    "platform": p.get("platform", ""),
                    "url": p.get("url", "")
                }
                for p in platforms
            ]
        else:
            output["events"][event_name] = []
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Exported {total_events} events to {output_path}")
    return total_events


class JSONExporter:
    """Handles JSON export operations."""
    
    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export(
        self,
        results: Dict[str, List[Dict]],
        filename: str = "events_ticket_data.json",
        pretty: bool = True
    ) -> str:
        """Export results to JSON file.
        
        Args:
            results: Event results
            filename: Output filename
            pretty: Use pretty printing
            
        Returns:
            Path to exported file
        """
        output_path = self.output_dir / filename
        
        if pretty:
            export_to_json_pretty(results, str(output_path))
        else:
            export_to_json_compact(results, str(output_path))
        
        return str(output_path)
    
    def export_with_summary(
        self,
        results: Dict[str, List[Dict]],
        filename: str = "events_ticket_data.json"
    ) -> str:
        """Export results with summary to JSON file.
        
        Args:
            results: Event results
            filename: Output filename
            
        Returns:
            Path to exported file
        """
        output_path = self.output_dir / filename
        export_with_summary(results, str(output_path))
        return str(output_path)
    
    def export_multiple(
        self,
        results: Dict[str, List[Dict]],
        filenames: List[str] = None
    ) -> Dict[str, str]:
        """Export results to multiple JSON formats.
        
        Args:
            results: Event results
            filenames: List of filenames to export
            
        Returns:
            Dict mapping filename to exported path
        """
        if filenames is None:
            filenames = [
                "events_ticket_data.json",
                "events_ticket_data_compact.json",
                "events_ticket_data_with_summary.json"
            ]
        
        exported = {}
        
        for i, filename in enumerate(filenames):
            if i == 0:
                exported[filename] = self.export(results, filename, pretty=True)
            elif i == 1:
                exported[filename] = self.export(results, filename, pretty=False)
            else:
                exported[filename] = self.export_with_summary(results, filename)
        
        return exported
