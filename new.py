import time
import random
import csv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from eventbrite_scrapper import Eventbrite

# -------------------------------
# Selenium setup
# -------------------------------
options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--start-maximized")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

wait = WebDriverWait(driver, 20)

# -------------------------------
# Get event URLs
# -------------------------------
client = Eventbrite()

events = client.search_events.get_results(
    region="canada--halton",
    dt_start="2026-02-01",
    dt_end="2026-02-28",
    max_pages=1,
)

print(f"Found {len(events)} events")

# -------------------------------
# CSV output
# -------------------------------
with open("halton_events_full.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Event Name",
        "Date",
        "Venue",
        "Organizer",
        "Poster URL",
        "Event URL"
    ])

    for i, event in enumerate(events, start=1):
        print(f"Scraping {i}/{len(events)}")
        driver.get(event.url)

        # Let React hydrate
        time.sleep(random.uniform(5, 7))

        # ---------------- POSTER IMAGE ----------------
        poster = None
        try:
            poster = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//meta[@property='og:image']")
                )
            ).get_attribute("content")
        except:
            pass

        # ---------------- VENUE ----------------
        venue = None
        try:
            venue = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class,'location-info')]")
                )
            ).text
        except:
            try:
                venue = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//p[contains(@class,'location')]")
                    )
                ).text
            except:
                pass

        # ---------------- ORGANIZER ----------------
        organizer = None
        try:
            organizer = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(@href,'/o/')]")
                )
            ).text
        except:
            pass

        writer.writerow([
            event.name,
            event.start_datetime,
            venue,
            organizer,
            poster,
            event.url
        ])

driver.quit()
print("Saved halton_events_fulls.csv")
