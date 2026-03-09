import csv
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def export_to_csv(
    results: Dict[str, List[Dict]],
    output_path: str,
    include_not_found: bool = True
) -> int:
    """Export results to CSV file.
    
    Args:
        results: Dict mapping event names to platform results
        output_path: Path to output CSV file
        include_not_found: Include events with no platforms found
        
    Returns:
        Number of rows written
    """
    rows = []
    
    for event_name, platforms in results.items():
        if not platforms and not include_not_found:
            continue
            
        if platforms:
            for p in platforms:
                rows.append({
                    "event_name": event_name,
                    "platform": p.get("platform", "Not Found"),
                    "platform_url": p.get("url", "")
                })
        else:
            rows.append({
                "event_name": event_name,
                "platform": "Not Found",
                "platform_url": ""
            })
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["event_name", "platform", "platform_url"]
        )
        writer.writeheader()
        writer.writerows(rows)
    
    logger.info(f"Exported {len(rows)} rows to {output_path}")
    return len(rows)


def export_grouped_csv(
    results: Dict[str, List[Dict]],
    output_path: str,
    include_not_found: bool = True
) -> int:
    """Export results to grouped CSV file.
    
    Args:
        results: Dict mapping event names to platform results
        output_path: Path to output CSV file
        include_not_found: Include events with no platforms found
        
    Returns:
        Number of rows written
    """
    rows = []
    
    for event_name, platforms in results.items():
        if not platforms and not include_not_found:
            continue
            
        if platforms:
            platform_names = sorted([p.get("platform", "") for p in platforms])
            platform_str = ",".join(platform_names)
        else:
            platform_str = "Not Found"
        
        rows.append({
            "event_name": event_name,
            "platforms": platform_str
        })
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["event_name", "platforms"]
        )
        writer.writeheader()
        writer.writerows(rows)
    
    logger.info(f"Exported {len(rows)} rows to {output_path}")
    return len(rows)


class CSVExporter:
    """Handles CSV export operations."""
    
    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_flat(
        self,
        results: Dict[str, List[Dict]],
        filename: str = "event_ticket_sites.csv",
        include_not_found: bool = True
    ) -> str:
        """Export to flat CSV format.
        
        Args:
            results: Event results
            filename: Output filename
            include_not_found: Include events without platforms
            
        Returns:
            Path to exported file
        """
        output_path = self.output_dir / filename
        export_to_csv(results, str(output_path), include_not_found)
        return str(output_path)
    
    def export_grouped(
        self,
        results: Dict[str, List[Dict]],
        filename: str = "event_ticket_sites_grouped.csv",
        include_not_found: bool = True
    ) -> str:
        """Export to grouped CSV format.
        
        Args:
            results: Event results
            filename: Output filename
            include_not_found: Include events without platforms
            
        Returns:
            Path to exported file
        """
        output_path = self.output_dir / filename
        export_grouped_csv(results, str(output_path), include_not_found)
        return str(output_path)
    
    def export_both(
        self,
        results: Dict[str, List[Dict]],
        flat_filename: str = "event_ticket_sites.csv",
        grouped_filename: str = "event_ticket_sites_grouped.csv",
        include_not_found: bool = True
    ) -> Dict[str, str]:
        """Export to both CSV formats.
        
        Args:
            results: Event results
            flat_filename: Flat CSV filename
            grouped_filename: Grouped CSV filename
            include_not_found: Include events without platforms
            
        Returns:
            Dict with paths to both exported files
        """
        return {
            "flat": self.export_flat(results, flat_filename, include_not_found),
            "grouped": self.export_grouped(results, grouped_filename, include_not_found)
        }
