import pandas as pd

# Load original CSV
df = pd.read_csv("deduplicated.csv", encoding="latin1")
df.columns = df.columns.str.replace("\t", "", regex=False).str.strip()

# Print columns so you can see them
print("Available columns:")
for col in df.columns:
    print(repr(col))

# Manually pick URL column if auto detection fails
url_candidates = [
    col for col in df.columns
    if any(x in col.lower() for x in ["url", "link", "page", "website"])
]

if not url_candidates:
    raise ValueError("No URL column found. Check column names printed above.")

url_column = url_candidates[0]
print("Using URL column:", url_column)

# Remove duplicate URLs, keep first occurrence
df_cleaned = df.drop_duplicates(subset=[url_column], keep="first")

# Save cleaned file
df_cleaned.to_csv("Events.csv", index=False)

print("Duplicate links removed successfully.")
