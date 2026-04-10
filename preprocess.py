"""
preprocess.py
─────────────
DS4200 Final Project — Data Preprocessing
Produces flights_cleaned.csv from the raw Kaggle CSVs.

Steps
  1. Load raw CSVs
  2. Filter to June–August (MONTH 6, 7, 8)
  3. Keep only flights from the top-20 busiest origin airports
  4. Drop rows with missing ARRIVAL_DELAY
  5. Sample to ~10,000 rows (reproducible)
  6. Merge airline names and airport lat/lon (origin + destination)
  7. Add derived columns: delayed, time_of_day, primary_delay_cause, hour
  8. Export → flights_cleaned.csv
  9. Print row count + file size check
"""

import pandas as pd
import numpy as np
import os

SEED        = 42
TARGET_ROWS = 10_000
OUT_PATH    = "flights_cleaned.csv"

#  1. Load raw CSVs 
print("Loading raw CSVs…")
flights  = pd.read_csv("flights.csv",  low_memory=False)
airlines = pd.read_csv("airlines.csv")
airports = pd.read_csv("airports.csv")

print(f"  flights  : {len(flights):>10,} rows × {flights.shape[1]} cols")
print(f"  airlines : {len(airlines):>10,} rows")
print(f"  airports : {len(airports):>10,} rows")

#    2. Filter to June–August   
print("\nFiltering to June–August…")
df = flights[flights["MONTH"].isin([6, 7, 8])].copy()
print(f"  After month filter : {len(df):,} rows")

#  3. Top-20 busiest origin airports 
print("\nFinding top-20 busiest origin airports…")
top20 = (
    df["ORIGIN_AIRPORT"]
    .value_counts()
    .head(20)
    .index.tolist()
)
print(f"  Top 20: {', '.join(top20)}")

df = df[df["ORIGIN_AIRPORT"].isin(top20)].copy()
print(f"  After airport filter : {len(df):,} rows")

#  4. Drop missing ARRIVAL_DELAY 
print("\nDropping rows with missing ARRIVAL_DELAY…")
df = df.dropna(subset=["ARRIVAL_DELAY"]).copy()
print(f"  After dropna : {len(df):,} rows")

#  5. Sample to ~10,000 rows 
if len(df) > TARGET_ROWS:
    print(f"\nSampling to {TARGET_ROWS:,} rows (seed={SEED})…")
    df = df.sample(n=TARGET_ROWS, random_state=SEED).reset_index(drop=True)
else:
    print(f"\nNo sampling needed ({len(df):,} rows ≤ {TARGET_ROWS:,})")

#  6. Merge airline names 
print("\nMerging airline names…")
airline_map = dict(zip(airlines["IATA_CODE"], airlines["AIRLINE"]))
df["AIRLINE_NAME"] = df["AIRLINE"].map(airline_map)

#  6b. Merge airport lat/lon (origin) 
print("Merging origin airport metadata…")
apt = airports[["IATA_CODE", "AIRPORT", "CITY", "STATE",
                "LATITUDE", "LONGITUDE"]].copy()

df = df.merge(
    apt.rename(columns={
        "IATA_CODE": "ORIGIN_AIRPORT",
        "AIRPORT":   "ORIGIN_AIRPORT_NAME",
        "CITY":      "ORIGIN_CITY",
        "STATE":     "ORIGIN_STATE",
        "LATITUDE":  "ORIGIN_LAT",
        "LONGITUDE": "ORIGIN_LON",
    }),
    on="ORIGIN_AIRPORT",
    how="left",
)

#  6c. Merge airport lat/lon (destination) 
print("Merging destination airport metadata…")
df = df.merge(
    apt.rename(columns={
        "IATA_CODE": "DESTINATION_AIRPORT",
        "AIRPORT":   "DEST_AIRPORT_NAME",
        "CITY":      "DEST_CITY",
        "STATE":     "DEST_STATE",
        "LATITUDE":  "DEST_LAT",
        "LONGITUDE": "DEST_LON",
    }),
    on="DESTINATION_AIRPORT",
    how="left",
)

#  7. Derived columns 
print("\nAdding derived columns…")


df["hour"] = (df["SCHEDULED_DEPARTURE"] // 100).clip(0, 23).astype(int)
df["delayed"] = (df["ARRIVAL_DELAY"] > 15).astype(int)

# time_of_day
def _tod(h):
    if 5  <= h <= 11: return "Morning"
    if 12 <= h <= 16: return "Afternoon"
    if 17 <= h <= 20: return "Evening"
    return "Night"

df["time_of_day"] = df["hour"].apply(_tod)

# Actual column names in this dataset:
CAUSE_COLS = {
    "AIRLINE_DELAY":       "Carrier",
    "WEATHER_DELAY":       "Weather",
    "AIR_SYSTEM_DELAY":    "NAS",
    "SECURITY_DELAY":      "Security",
    "LATE_AIRCRAFT_DELAY": "Late Aircraft",
}

# Only rows where at least one cause is populated
cause_data = df[list(CAUSE_COLS.keys())].copy()
has_cause  = cause_data.notna().any(axis=1)

df["primary_delay_cause"] = np.nan
df.loc[has_cause, "primary_delay_cause"] = (
    cause_data[has_cause]
    .fillna(0)
    .idxmax(axis=1)
    .map(CAUSE_COLS)
)

# Keep a tidy set of columns (drop low-value / redundant raw fields)
KEEP = [
    # identifiers
    "YEAR", "MONTH", "DAY", "DAY_OF_WEEK",
    "AIRLINE", "AIRLINE_NAME",
    "FLIGHT_NUMBER", "TAIL_NUMBER",
    # route
    "ORIGIN_AIRPORT", "ORIGIN_AIRPORT_NAME", "ORIGIN_CITY", "ORIGIN_STATE",
    "ORIGIN_LAT", "ORIGIN_LON",
    "DESTINATION_AIRPORT", "DEST_AIRPORT_NAME", "DEST_CITY", "DEST_STATE",
    "DEST_LAT", "DEST_LON",
    "DISTANCE",
    # timing
    "SCHEDULED_DEPARTURE", "DEPARTURE_TIME", "DEPARTURE_DELAY",
    "SCHEDULED_ARRIVAL",   "ARRIVAL_TIME",   "ARRIVAL_DELAY",
    "SCHEDULED_TIME", "ELAPSED_TIME", "AIR_TIME",
    # derived
    "hour", "time_of_day", "delayed",
    # delay causes
    "AIRLINE_DELAY", "WEATHER_DELAY", "AIR_SYSTEM_DELAY",
    "SECURITY_DELAY", "LATE_AIRCRAFT_DELAY", "primary_delay_cause",
    # status
    "CANCELLED", "DIVERTED", "CANCELLATION_REASON",
]

# Only keep columns that actually exist in the dataframe
KEEP = [c for c in KEEP if c in df.columns]
df_out = df[KEEP].copy()

print(f"\nExporting {len(df_out):,} rows × {df_out.shape[1]} cols → {OUT_PATH}")
df_out.to_csv(OUT_PATH, index=False)

#  9. Size check 
size_mb = os.path.getsize(OUT_PATH) / 1_048_576
print(f"\n{'='*50}")
print(f"  Output file  : {OUT_PATH}")
print(f"  Rows         : {len(df_out):,}")
print(f"  Columns      : {df_out.shape[1]}")
print(f"  File size    : {size_mb:.2f} MB")
if size_mb > 25:
    print("  ⚠️  WARNING: file exceeds 25 MB GitHub limit — reduce TARGET_ROWS")
else:
    print(f"  ✓  Within GitHub 25 MB limit")

print(f"\nDelayed flights   : {df_out['delayed'].sum():,}  ({df_out['delayed'].mean()*100:.1f}%)")
print(f"Time-of-day dist  :\n{df_out['time_of_day'].value_counts().to_string()}")
print(f"\nPrimary delay cause dist:")
print(df_out["primary_delay_cause"].value_counts(dropna=False).to_string())
print(f"\nTop 5 origin airports:")
print(df_out["ORIGIN_AIRPORT"].value_counts().head(5).to_string())
print(f"\nDone.")
