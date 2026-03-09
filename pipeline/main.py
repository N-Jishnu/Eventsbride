#!/usr/bin/env python3
"""
Event Ticket Pipeline

Main entry point for the event ticket discovery pipeline.
Discovers ticketing platforms for events from Eventbrite Canada.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List

from csv_exporter import CSVExporter
from deduplicator import Deduplicator
from event_loader import load_events
from event_matcher import EventMatcher
from json_exporter import JSONExporter
from platform_detector import PlatformDetector
from platform_searcher import search_all_platforms, deduplicate_links, create_driver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_pipeline(
    events: List[str],
    similarity_threshold: float = 30.0,
    output_dir: str = ".",
    max_events: int = 0
) -> Dict[str, List[Dict]]:
    """Run the full pipeline using direct platform scraping.
    
    Args:
        events: List of event names
        similarity_threshold: Minimum similarity score for matching
        output_dir: Directory for output files
        max_events: Maximum number of events to process (0 = all)
        
    Returns:
        Dict mapping event names to platform results
    """
    if max_events > 0 and len(events) > max_events:
        events = events[:max_events]
    
    platform_detector = PlatformDetector()
    event_matcher = EventMatcher(threshold=similarity_threshold)
    deduplicator = Deduplicator()
    
    all_results: Dict[str, List[Dict]] = {}
    total_links_found = 0
    
    logger.info(f"Processing {len(events)} events (direct platform scraping with reusable browser)")
    
    driver = None
    try:
        logger.info("Creating headless browser...")
        driver = create_driver()
        
        for idx, event in enumerate(events):
            try:
                logger.info(f"Processing ({idx+1}/{len(events)}): {event[:50]}...")
                
                search_results = search_all_platforms(event, delay=0.5, driver=driver)
                
                search_results = deduplicate_links(search_results)
                
                search_results = [r for r in search_results if "eventbrite" not in r.get("url", "").lower()]
                
                platforms = platform_detector.detect_platforms(search_results)
                
                matches = event_matcher.match(event, platforms)
                
                unique_platforms = platform_detector.get_unique_platforms(matches)
                
                all_results[event] = unique_platforms
                total_links_found += len(unique_platforms)
                
                if (idx + 1) % 10 == 0:
                    logger.info(f"Progress: {idx+1}/{len(events)} events processed | Total links found: {total_links_found}")
                
            except Exception as e:
                logger.error(f"Error processing '{event[:30]}...': {e}")
                all_results[event] = []
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Browser closed")
            except Exception:
                pass
    
    all_results = deduplicator.deduplicate_all(all_results)
    
    stats = deduplicator.get_stats()
    logger.info(
        f"Deduplication: {stats['input']} input -> {stats['output']} output"
    )
    logger.info(f"Total links found: {total_links_found}")
    
    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Event Ticket Pipeline - Find ticket platforms for events"
    )
    
    parser.add_argument(
        "--input",
        "-i",
        help="Input CSV file with events"
    )
    
    parser.add_argument(
        "--events",
        "-e",
        nargs="+",
        help="Event names as arguments (space-separated)"
    )
    
    parser.add_argument(
        "--event-column",
        default="Name",
        help="Column name for event names in CSV (default: Name)"
    )
    
    parser.add_argument(
        "--output-dir",
        "-o",
        default=".",
        help="Output directory (default: current directory)"
    )
    
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=20.0,
        help="Similarity threshold for event matching (default: 30.0)"
    )
    
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Export to CSV format"
    )
    
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export to JSON format"
    )
    
    parser.add_argument(
        "--export-all",
        action="store_true",
        help="Export to all formats"
    )
    
    parser.add_argument(
        "--include-not-found",
        action="store_true",
        default=True,
        help="Include events without platforms in export"
    )
    
    parser.add_argument(
        "--max-urls",
        type=int,
        default=0,
        help="Limit number of events to process (0 = all)"
    )
    
    args = parser.parse_args()
    
    if not args.input and not args.events:
        parser.error("Either --input or --events is required")
    
    events = load_events(source=args.input, events_list=args.events, event_name_column=args.event_column)
    
    if not events:
        logger.error("No events loaded")
        sys.exit(1)
    
    logger.info(f"Loaded {len(events)} events")
    
    results = run_pipeline(
        events=events,
        similarity_threshold=args.threshold,
        output_dir=args.output_dir,
        max_events=args.max_urls
    )
    
    events_with_tickets = sum(1 for p in results.values() if p)
    logger.info(
        f"Results: {events_with_tickets}/{len(events)} events have ticket platforms"
    )
    
    export_csv = args.export_csv or args.export_all
    export_json = args.export_json or args.export_all
    
    if export_csv:
        csv_exporter = CSVExporter(output_dir=args.output_dir)
        csv_exporter.export_both(
            results,
            include_not_found=args.include_not_found
        )
        logger.info("CSV exports completed")
    
    if export_json:
        json_exporter = JSONExporter(output_dir=args.output_dir)
        json_exporter.export_with_summary(results)
        logger.info("JSON export completed")
    
    if not export_csv and not export_json:
        logger.info("No exports requested (use --export-csv, --export-json, or --export-all)")
    
    logger.info("Pipeline completed successfully")


if __name__ == "__main__":
    main()
