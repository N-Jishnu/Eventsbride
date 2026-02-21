import pandas as pd

# Load CSV safely
df = pd.read_csv("deduplicated.csv", encoding="latin1")

# Clean column names
df.columns = df.columns.str.replace("\t", "", regex=False).str.strip()

# Auto-detect URL column
url_column = next(
    col for col in df.columns
    if "url" in col.lower() or "link" in col.lower() or "page" in col.lower()
)

print("Detected URL column:", url_column)

# Find URLs present more than once
url_counts = df[url_column].value_counts()
duplicate_urls = url_counts[url_counts > 1].reset_index()
duplicate_urls.columns = [url_column, "Count"]

# Save to CSV
duplicate_urls.to_csv("duplicate_urls.csv", index=False)

print("duplicate_urls.csv created successfully")
