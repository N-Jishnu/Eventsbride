import pandas as pd
import json

# Read CSV (no header in your file)
df = pd.read_csv("deduplicated_updated.csv", encoding="latin1", header=None)

# Assign column names
df.columns = [
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
    "Date & Time"
]

# Convert to JSON
json_file = "March.json"
df.to_json(json_file, orient="records", indent=2, force_ascii=False)

print("CSV successfully converted to JSON:", json_file)
