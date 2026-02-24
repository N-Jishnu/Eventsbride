# Eventsbride

Scrapes Eventbrite listings for Hamilton, Canada and produces a clean CSV of event details. Designed to extract robust metadata from JSON-LD and Eventbrite’s server-side payloads, with sensible fallbacks to visible page content.

## Features
- Collects event URLs across multiple listing pages
- Extracts metadata: Page url, Poster, Name, Organizer, Description, Category, Highlights, Refund Policy, Address, Price, Date & Time
- Normalizes date/time into readable formats:
  - Single time: `Mon DD at HH:MM AM/PM [TZ]`
  - Ranges: `Mon DD from HH:MM AM/PM to HH:MM AM/PM [TZ]`
- Handles visible highlights and refund policy text where structured data is unavailable
- Friendly price parsing: single price, price ranges, Free, Donation

## Requirements
- Python 3.8+
- Packages:
  - requests
  - beautifulsoup4

Install:
```powershell
python -m pip install -U requests beautifulsoup4
```

## Quick Start
Run with defaults (Hamilton, single-day listing URL baked in):
```powershell
python eventbrite_hamilton_scraper.py
```

Common options:
```powershell
python eventbrite_hamilton_scraper.py `
  --base-url "https://www.eventbrite.com/d/canada--hamilton/" `
  --max-pages 10 `
  --timeout 30 `
  --delay 1.2 `
  --output "hamilton_eventbrite_details.csv"
```

Arguments:
- --base-url: Eventbrite listing URL to start from
- --max-pages: Number of listing pages to scan
- --timeout: HTTP timeout (seconds)
- --delay: Delay between requests (seconds), random jitter is added
- --output: Output CSV file path

## Output
CSV headers:
- Page url
- Poster
- Name
- Organizer
- Description
- Category
- Highlights
- Refund Policy
- Address
- Price
- Date & Time

Default output file: `hamilton_eventbrite_details.csv`

## Post‑Processing (optional)
Deduplicate rows by URL, keeping the first:
```powershell
$path = 'c:\Users\kumar\Desktop\EventsBride\hamilton_eventbrite_details.csv'
$csv = Import-Csv -Path $path
$seen = @{}
$filtered = foreach ($row in $csv) {
  $key = $row.'Page url'
  if ($seen.ContainsKey($key)) { continue }
  $seen[$key] = $true
  $row
}
$filtered | Export-Csv -Path $path -NoTypeInformation -Encoding UTF8
```

Normalize “Date & Time” segments to “date from time” or “date at time” while preserving existing values:
```powershell
$path = 'c:\Users\kumar\Desktop\EventsBride\hamilton_eventbrite_details.csv'
$rows = Import-Csv -Path $path
function Normalize-DateTime([string] $value) {
  if ([string]::IsNullOrWhiteSpace($value)) { return $value }
  $segments = $value -split '\s+AND\s+'
  $normalized = foreach ($seg in $segments) {
    $s = ($seg -replace '\s+', ' ').Trim()
    $s = [regex]::Replace($s, '(?i)(?<=\d)\s*(am|pm)\b', { param($m) $m.Value.Trim().ToUpper() })
    $s = $s -replace '\s*[-–]\s*', ' - '
    $m = [regex]::Match($s, '\b\d{1,2}:\d{2}\s*(?:AM|PM)\b')
    if ($m.Success) {
      $datePart = $s.Substring(0, $m.Index).Trim()
      $timePart = $s.Substring($m.Index).Trim()
      "$datePart from $timePart"
    } else { $s }
  }
  ($normalized -join ' AND ')
}
foreach ($row in $rows) { $row.'Date & Time' = Normalize-DateTime $row.'Date & Time' }
$rows | Export-Csv -Path $path -NoTypeInformation -Encoding UTF8
```

## Notes and Best Practices
- Respect Eventbrite’s Terms of Service and robots rules; this scraper is for educational/research use
- If you encounter 403 or captcha:
  - Increase `--delay`
  - Reduce `--max-pages`
  - Consider running less frequently
- To update the User-Agent or headers, edit the `HEADERS` constant in the script

## Project Structure
- eventbrite_hamilton_scraper.py — CLI scraper producing a CSV

## License
No license specified. Add a LICENSE file appropriate to your use case (e.g., MIT, Apache-2.0).
