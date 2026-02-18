import argparse
import csv
import html
import json
import random
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import requests
from bs4 import BeautifulSoup


DEFAULT_URL = "https://www.eventbrite.com/d/canada--hamilton/start_date%3D2026-03-22%26end_date%3D2026-03-22/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def extract_json_from_assignment(html: str, marker: str) -> Optional[Dict[str, Any]]:
    marker_index = html.find(marker)
    if marker_index == -1:
        return None

    start = html.find("{", marker_index)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    end = None

    for i in range(start, len(html)):
        ch = html[i]

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if not end:
        return None

    try:
        return json.loads(html[start:end])
    except json.JSONDecodeError:
        return None


def load_json_ld(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []

    for script in soup.find_all("script", {"type": "application/ld+json"}):
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    nodes.append(item)
        elif isinstance(data, dict):
            nodes.append(data)

    return nodes


def normalize_type(type_value: Any) -> List[str]:
    if isinstance(type_value, list):
        return [str(x) for x in type_value]
    if isinstance(type_value, str):
        return [type_value]
    return []


def first_event_schema(json_ld_nodes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for node in json_ld_nodes:
        types = normalize_type(node.get("@type"))
        if any(t in ("Event", "SocialEvent", "Festival") for t in types):
            return node
    return None


def extract_category(html: str) -> str:
    match = re.search(r"Category:\s*</span>\s*([^<]+)<", html)
    if match:
        return html_unescape_clean(match.group(1))
    return ""


def html_unescape_clean(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return html.unescape(text)


def strip_html_tags(value: Any) -> str:
    text = BeautifulSoup(str(value or ""), "html.parser").get_text(" ", strip=True)
    return html_unescape_clean(text)


def extract_visible_highlights(soup: BeautifulSoup) -> List[str]:
    values: List[str] = []

    for li in soup.select('ul[class*="Highlights_wrapper"] li'):
        text = html_unescape_clean(li.get_text(" ", strip=True))
        if text:
            values.append(text)

    if values:
        return values

    for card in soup.find_all(["div", "section"]):
        title = card.find(["p", "h2", "h3"])
        if not title:
            continue
        if title.get_text(" ", strip=True).lower() != "highlights":
            continue

        for li in card.find_all("li"):
            text = html_unescape_clean(li.get_text(" ", strip=True))
            if text:
                values.append(text)
        if values:
            return values

    return values


def format_highlights(highlights: Dict[str, Any], soup: BeautifulSoup) -> str:
    merged: List[str] = []
    seen: Set[str] = set()

    if isinstance(highlights, dict):
        friendly = {
            "freeParking": "Free parking",
            "paidParking": "Paid parking",
            "parking": "Parking available",
            "notAvailableParking": "No parking",
        }
        for key, value in highlights.items():
            if not bool(value):
                continue
            label = friendly.get(key, key)
            if label not in seen:
                seen.add(label)
                merged.append(label)

    for label in extract_visible_highlights(soup):
        if label not in seen:
            seen.add(label)
            merged.append(label)

    return ", ".join(merged)


def format_refund_policy(refunds: Dict[str, Any]) -> str:
    if not isinstance(refunds, dict):
        return ""

    description = refunds.get("refundPolicyDescription")
    if description:
        return strip_html_tags(description)

    code = refunds.get("refundPolicyCode")
    if code:
        return str(code)

    return ""


def format_address(event_schema: Dict[str, Any], soup: BeautifulSoup) -> str:
    address = ((event_schema.get("location") or {}).get("address") or {})
    if isinstance(address, dict):
        street = str(address.get("streetAddress", "") or "").strip()
        if "," in street:
            return street

        ordered = [
            street,
            address.get("addressLocality", ""),
            address.get("addressRegion", ""),
            address.get("postalCode", ""),
            address.get("addressCountry", ""),
        ]
        cleaned = [str(x).strip() for x in ordered if str(x).strip()]
        if cleaned:
            return ", ".join(cleaned)

    # Fallback: Eventbrite often stores location in social meta tags
    twitter_data1 = soup.find("meta", {"name": "twitter:data1"})
    if twitter_data1:
        text = html_unescape_clean(
            twitter_data1.get("value") or twitter_data1.get("content") or ""
        )
        if text:
            return text

    # Fallback: visible location section on page
    for selector in [
        '[data-testid="event-location"]',
        '[data-testid="location-info"]',
        '[data-testid="location-module"]',
    ]:
        node = soup.select_one(selector)
        if node:
            text = html_unescape_clean(node.get_text(" ", strip=True))
            if text:
                return text

    return ""


def format_price(event_schema: Dict[str, Any], server_data: Dict[str, Any], soup: BeautifulSoup) -> str:
    def clean_currency_amount(value: Any) -> str:
        text = html_unescape_clean(value)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def extract_price_from_visible_aside() -> str:
        aside = soup.find(attrs={"data-testid": "aside"})
        if not aside:
            return ""
        text = html_unescape_clean(aside.get_text(" ", strip=True))
        if not text:
            return ""

        if re.search(r"\bdonation\b", text, re.I):
            return "Donation"
        if re.search(r"\bfree\b", text, re.I):
            return "Free"

        from_match = re.search(
            r"\bFrom\s+((?:CA\$|US\$|C\$|\$|CAD\s+|USD\s+)?\d+(?:\.\d{1,2})?)",
            text,
            re.I,
        )
        if from_match:
            return f"From {clean_currency_amount(from_match.group(1))}"

        any_price_match = re.search(
            r"\b(?:CA\$|US\$|C\$|\$|CAD\s+|USD\s+)?\d+(?:\.\d{1,2})?\b",
            text,
            re.I,
        )
        if any_price_match:
            return clean_currency_amount(any_price_match.group(0))

        return ""

    offers = event_schema.get("offers")

    if isinstance(offers, dict):
        currency = offers.get("priceCurrency") or ""
        price = offers.get("price")
        low = offers.get("lowPrice")
        high = offers.get("highPrice")
        if offers.get("name") and "donation" in str(offers.get("name")).lower():
            return "Donation"
        if price is not None:
            return f"{currency} {price}".strip()
        if low is not None and high is not None:
            return f"{currency} {low} - {currency} {high}".strip()

    if isinstance(offers, list) and offers:
        priced = [o for o in offers if isinstance(o, dict)]
        values: List[float] = []
        for offer in priced:
            raw_price = offer.get("price")
            try:
                values.append(float(str(raw_price)))
            except (TypeError, ValueError):
                continue
        currency = next(
            (o.get("priceCurrency") for o in priced if o.get("priceCurrency")),
            "",
        )
        if values:
            low, high = min(values), max(values)
            if low == high:
                return f"{currency} {low}".strip()
            return f"{currency} {low} - {currency} {high}".strip()

    tickets = (
        ((server_data.get("event_listing_response") or {}).get("tickets") or {}).get(
            "ticketClasses"
        )
        or []
    )

    saw_donation = False
    saw_free = False
    ticket_prices: List[str] = []

    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue
        characteristics = ticket.get("characteristics") or {}
        if characteristics.get("isDonation"):
            saw_donation = True
        if characteristics.get("isFree"):
            saw_free = True

        if ticket.get("name") and "donation" in str(ticket.get("name")).lower():
            saw_donation = True

        total_cost = (ticket.get("totalCost") or {}).get("display")
        if total_cost:
            ticket_prices.append(clean_currency_amount(total_cost))
            continue

        cost = (ticket.get("cost") or {}).get("display")
        if cost:
            ticket_prices.append(clean_currency_amount(cost))

    if ticket_prices:
        unique_prices = sorted(set(ticket_prices))
        if len(unique_prices) == 1:
            return unique_prices[0]
        return " - ".join([unique_prices[0], unique_prices[-1]])

    if saw_donation:
        return "Donation"
    if saw_free:
        return "Free"

    visible_price = extract_price_from_visible_aside()
    if visible_price:
        return visible_price

    return ""


def format_date_time(event_schema: Dict[str, Any], soup: BeautifulSoup) -> str:
    month_map = {
        "january": "Jan",
        "february": "Feb",
        "march": "Mar",
        "april": "Apr",
        "may": "May",
        "june": "Jun",
        "july": "Jul",
        "august": "Aug",
        "september": "Sep",
        "october": "Oct",
        "november": "Nov",
        "december": "Dec",
        "jan": "Jan",
        "feb": "Feb",
        "mar": "Mar",
        "apr": "Apr",
        "jun": "Jun",
        "jul": "Jul",
        "aug": "Aug",
        "sep": "Sep",
        "oct": "Oct",
        "nov": "Nov",
        "dec": "Dec",
    }
    tz_pattern = r"(?:EST|EDT|PST|PDT|CST|CDT|MST|MDT|UTC|GMT)"
    month_pattern = (
        r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
        r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    )

    def normalize_date(date_text: str) -> str:
        match = re.search(
            rf"(?P<month>{month_pattern})\.?\s+(?P<day>\d{{1,2}})",
            date_text,
            re.I,
        )
        if not match:
            return html_unescape_clean(date_text)
        month = month_map.get(match.group("month").lower().rstrip("."), match.group("month"))
        day = match.group("day")
        return f"{month} {day}"

    def normalize_time(time_text: str) -> str:
        match = re.search(r"(?P<hour>\d{1,2})(?::(?P<min>\d{2}))?\s*(?P<ampm>[APap][Mm])", time_text)
        if not match:
            return html_unescape_clean(time_text)
        hour = int(match.group("hour"))
        minute = match.group("min") or "00"
        ampm = match.group("ampm").upper()
        return f"{hour}:{minute} {ampm}"

    def extract_details_lines() -> List[str]:
        lines: List[str] = []
        for testid in ["event-details", "aside"]:
            node = soup.find(attrs={"data-testid": testid})
            if not node:
                continue
            for raw_line in node.get_text("\n", strip=True).split("\n"):
                clean = html_unescape_clean(raw_line)
                if clean and clean not in lines:
                    lines.append(clean)
        return lines

    def parse_visible_line(line: str) -> Optional[str]:
        range_match = re.search(
            rf"(?P<date>{month_pattern}\.?(?:\s+\d{{1,2}})(?:,\s*\d{{4}})?)"
            rf"\s*from\s*"
            rf"(?P<start>\d{{1,2}}(?::\d{{2}})?\s*[APap][Mm])"
            rf"\s*to\s*(?P<end>\d{{1,2}}(?::\d{{2}})?\s*[APap][Mm])"
            rf"(?:\s*(?P<tz>{tz_pattern}))?",
            line,
            re.I,
        )
        if range_match:
            date_part = normalize_date(range_match.group("date"))
            start_part = normalize_time(range_match.group("start"))
            end_part = normalize_time(range_match.group("end"))
            tz = (range_match.group("tz") or "").upper()
            tz_suffix = f" {tz}" if tz else ""
            return f"{date_part} from {start_part} to {end_part}{tz_suffix}"

        single_match = re.search(
            rf"(?P<date>{month_pattern}\.?(?:\s+\d{{1,2}})(?:,\s*\d{{4}})?)"
            rf"\s*(?:at|\u00b7|from)\s*(?P<start>\d{{1,2}}(?::\d{{2}})?\s*[APap][Mm])"
            rf"(?:\s*(?P<tz>{tz_pattern}))?",
            line,
            re.I,
        )
        if single_match:
            date_part = normalize_date(single_match.group("date"))
            start_part = normalize_time(single_match.group("start"))
            tz = (single_match.group("tz") or "").upper()
            tz_suffix = f" {tz}" if tz else ""
            return f"{date_part} at {start_part}{tz_suffix}"

        return None

    for line in extract_details_lines():
        parsed = parse_visible_line(line)
        if parsed:
            return parsed

    twitter_when = soup.find("meta", {"name": "twitter:data2"})
    if twitter_when:
        text = html_unescape_clean(
            twitter_when.get("value") or twitter_when.get("content") or ""
        )
        twitter_match = re.search(
            rf"(?P<date>{month_pattern}\s+\d{{1,2}}(?:,\s*\d{{4}})?)\s+at\s+"
            rf"(?P<start>\d{{1,2}}(?::\d{{2}})?\s*[APap][Mm])"
            rf"(?:\s*(?P<tz>{tz_pattern}))?",
            text,
            re.I,
        )
        if twitter_match:
            date_part = normalize_date(twitter_match.group("date"))
            start_part = normalize_time(twitter_match.group("start"))
            tz = (twitter_match.group("tz") or "").upper()
            tz_suffix = f" {tz}" if tz else ""
            return f"{date_part} at {start_part}{tz_suffix}"

    start_meta = soup.find("meta", {"property": "event:start_time"})
    start_raw = start_meta.get("content") if start_meta else ""
    if not start_raw:
        start_raw = event_schema.get("startDate", "")

    if start_raw:
        try:
            start_dt = datetime.fromisoformat(str(start_raw).replace("Z", "+00:00"))
            return f"{start_dt.strftime('%b')} {start_dt.day} at {start_dt.strftime('%I:%M %p').lstrip('0')}"
        except ValueError:
            pass

    return html_unescape_clean(str(start_raw or ""))


def format_organizer(event_schema: Dict[str, Any], soup: BeautifulSoup) -> str:
    organizer = html_unescape_clean((event_schema.get("organizer") or {}).get("name") or "")
    if organizer:
        return organizer

    # Fallback from explicit organizer profile links
    for link in soup.find_all("a", href=True):
        href = str(link.get("href") or "")
        if "/o/" not in href:
            continue
        text = html_unescape_clean(link.get_text(" ", strip=True))
        if text:
            return text

    # Fallback from meta description: "Eventbrite - X presents ..."
    description_meta = soup.find("meta", {"name": "description"})
    if description_meta:
        description_text = html_unescape_clean(
            description_meta.get("content") or description_meta.get("value") or ""
        )
        match = re.search(r"Eventbrite\s*-\s*(.*?)\s+presents\s+", description_text, re.I)
        if match:
            candidate = html_unescape_clean(match.group(1))
            if candidate:
                return candidate

    return ""


def parse_event_page(session: requests.Session, url: str, timeout: int) -> Dict[str, str]:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()

    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    server_data = extract_json_from_assignment(html, "window.__SERVER_DATA__") or {}

    json_ld_nodes = load_json_ld(soup)
    event_schema = first_event_schema(json_ld_nodes) or {}

    og_image = soup.find("meta", {"property": "og:image"})
    og_title = soup.find("meta", {"property": "og:title"})
    og_description = soup.find("meta", {"property": "og:description"})

    organizer = format_organizer(event_schema, soup)
    description = (
        (event_schema.get("description") or "")
        or (og_description.get("content", "") if og_description else "")
    )

    row = {
        "Page url": url,
        "Poster": str(og_image.get("content", "") if og_image else "").strip(),
        "Name": html_unescape_clean(
            (event_schema.get("name") or "")
            or (og_title.get("content", "") if og_title else "")
        ),
        "Organizer": organizer,
        "Description": strip_html_tags(description),
        "Category": extract_category(html),
        "Highlights": format_highlights(
            (server_data.get("event_listing_response") or {}).get("highlights") or {},
            soup,
        ),
        "Refund Policy": format_refund_policy((server_data.get("event_listing_response") or {}).get("refunds") or {}),
        "Address": format_address(event_schema, soup),
        "Price": format_price(event_schema, server_data, soup),
        "Date & Time": format_date_time(event_schema, soup),
    }

    return row


def collect_event_urls(
    session: requests.Session,
    base_url: str,
    max_pages: int,
    timeout: int,
    delay_seconds: float,
) -> List[str]:
    urls: List[str] = []
    seen: Set[str] = set()

    for page in range(1, max_pages + 1):
        page_url = base_url if page == 1 else f"{base_url}?page={page}"
        response = session.get(page_url, timeout=timeout)
        response.raise_for_status()
        html = response.text

        server_data = extract_json_from_assignment(html, "window.__SERVER_DATA__") or {}
        results = (
            (((server_data.get("search_data") or {}).get("events") or {}).get("results"))
            or []
        )

        if not results:
            break

        added_this_page = 0
        for event in results:
            if not isinstance(event, dict):
                continue
            url = str(event.get("url") or "").strip()
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
                added_this_page += 1

        if added_this_page == 0:
            break

        time.sleep(delay_seconds + random.uniform(0.2, 0.8))

    return urls


def save_csv(rows: List[Dict[str, str]], output_file: str) -> None:
    headers = [
        "Page url",
        "Poster",
        "Name",
        "Organizer",
        "Description",
        "Category",
        "Highlights",
        "Refund Policy",
        "Address",
        "Price",
        "Date & Time",
    ]

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Eventbrite event details from Hamilton listing pages."
    )
    parser.add_argument("--base-url", default=DEFAULT_URL, help="Eventbrite listing URL")
    parser.add_argument("--max-pages", type=int, default=20, help="How many listing pages to scan")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    parser.add_argument("--delay", type=float, default=1.2, help="Delay between requests")
    parser.add_argument(
        "--output",
        default="hamilton_eventbrite_details.csv",
        help="Output CSV file path",
    )
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update(HEADERS)

    print(f"Collecting event URLs from: {args.base_url}")
    event_urls = collect_event_urls(
        session=session,
        base_url=args.base_url,
        max_pages=args.max_pages,
        timeout=args.timeout,
        delay_seconds=args.delay,
    )
    print(f"Found {len(event_urls)} event URLs")

    rows: List[Dict[str, str]] = []
    for index, event_url in enumerate(event_urls, start=1):
        try:
            row = parse_event_page(session, event_url, args.timeout)
            rows.append(row)
            print(f"[{index}/{len(event_urls)}] Scraped: {row['Name']}")
        except Exception as exc:
            print(f"[{index}/{len(event_urls)}] Failed: {event_url} ({exc})")
        time.sleep(args.delay + random.uniform(0.2, 0.8))

    save_csv(rows, args.output)
    print(f"Saved {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
