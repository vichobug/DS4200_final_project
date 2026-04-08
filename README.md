# DS4200 Final Project — U.S. Flight Delay Analysis (2015)

**DS4200: Information Presentation and Visualization**

An interactive visual analysis of 2015 U.S. domestic flight delays, built to help travelers make smarter booking decisions by identifying when, where, and why delays happen.

---

## Overview

Using a dataset of 5.8 million flights from the Bureau of Transportation Statistics, this project explores delay patterns across airlines, airports, times of day, and seasons. The deliverable is a dark-themed single-page website with five complementary interactive visualizations.

**Core questions:**
- Which airlines have the worst on-time performance, and why?
- When during the day or week are delays most likely?
- Which airports and regions experience the highest average delays?
- Does flight distance predict delay severity?
- How do airline delay trends evolve over summer months?

---

## Live Website

Open `index.html` in a browser to view the full interactive dashboard.

---

## Repository Structure

```
DS4200_final_project/
├── index.html                  # Main single-page website
├── style.css                   # Dark-theme styling
│
├── EDA.ipynb                   # Exploratory data analysis notebook
├── visualizations_final.ipynb  # Final visualization development notebook
│
├── preprocess.py               # Data cleaning & sampling pipeline
├── generate_vizzes.py          # Generates all 5 visualization files
│
├── flights_cleaned.csv         # Preprocessed 10,000-row sample (committed)
├── airports_stats.json         # Airport-level delay statistics
├── daily_delays.json           # Daily delay aggregates by airline
│
├── airlines.csv                # 14 US carrier names + IATA codes
├── airports.csv                # 322 US airports with coordinates
│
├── viz1.html                   # Airline on-time performance (Altair)
├── viz2.html                   # Delay heatmap: hour x day (Altair)
├── viz3.html                   # Distance vs. delay scatter (Altair)
├── viz4.html / viz4.js         # Airport delay map (D3)
└── viz5.html / viz5.js         # Daily delay trends by airline (D3)
```

> **Note:** `flights.csv` (5.8 million rows, ~592 MB) is excluded via `.gitignore`. Download it separately (see Data Sources).

---

## Data

### Source
[2015 Flight Delays and Cancellations](https://www.kaggle.com/datasets/usdot/flight-delays) — U.S. Bureau of Transportation Statistics via Kaggle.

### Raw Dataset
- **5.8 million** flight records
- **31 features** per flight (timings, delays, cancellations, distance, etc.)
- **14 major U.S. carriers**, **322 domestic airports**

### Preprocessing Pipeline (`preprocess.py`)

The raw dataset is too large for direct visualization, so the following steps reduce it to a manageable sample:

1. **Filter by season** — Keep only summer flights (June, July, August)
2. **Filter by airport** — Restrict to the top-20 busiest origin airports (ATL, ORD, DFW, LAX, DEN, etc.)
3. **Drop missing data** — Remove rows without `ARRIVAL_DELAY`
4. **Sample** — Randomly sample ~10,000 rows (`seed=42` for reproducibility)
5. **Enrich** — Merge airline names and airport metadata (lat/lon, city, state) for origin and destination
6. **Derive features:**
   - `hour` — departure hour extracted from `SCHEDULED_DEPARTURE`
   - `delayed` — binary flag if `ARRIVAL_DELAY > 15` minutes
   - `time_of_day` — Morning (5–11 AM), Afternoon (12–4 PM), Evening (5–8 PM), Night
   - `primary_delay_cause` — whichever of 5 delay categories had the most minutes for that flight
7. **Export** — Write to `flights_cleaned.csv`

---

## Visualizations

### 1. Airline On-Time Performance
**Type:** Stacked horizontal bar chart (Altair)

Compares delay rates across all 14 airlines, broken down by delay cause (Late Aircraft, Carrier, Weather, NAS, Security). A reference line marks the fleet-wide average. Spirit Airlines is the worst performer; Hawaiian Airlines is the best.

### 2. Delay Heatmap: Hour x Day of Week
**Type:** Interactive heatmap with hover tooltips (Altair)

Shows average departure delay for every combination of hour (0–23) and day of week. Delays peak in the 4–9 PM window on weekdays. Flights before 8 AM are consistently the safest choice.

### 3. Distance vs. Arrival Delay (Linked Views)
**Type:** Linked scatter plot + histogram with brush selection (Altair)

Scatter shows individual flights colored by time of day. Drag-selecting a region in the scatter updates the histogram on the right to show the delay distribution for only those flights. Distance is a weak predictor of delay; short-haul flights show more extreme outliers.

### 4. U.S. Airport Delay Map
**Type:** Zoomable/pannable geographic bubble map (D3 + TopoJSON)

Plots all top-20 airports on an Albers USA projection. Bubble size encodes total departures; color encodes average delay (blue = on-time, red = delayed). Hover for airport name, city, flight count, average delay, and top carrier. Scroll to zoom, drag to pan, double-click to reset.

### 5. Daily Delay Trends by Airline
**Type:** Multi-line time series with dropdown airline selector (D3)

Shows daily average arrival delay for each airline across June–August 2015. A dropdown + checkboxes let you toggle airlines on/off. A vertical rule marks July 4. Delay spikes around the holiday are visible; recovery speed varies significantly by carrier.

---

## Key Findings

1. **Late aircraft delay is the dominant cause.** Cascading operational delays — not weather — account for the majority of delay minutes across all airlines. This suggests a systemic, schedule-driven problem.

2. **Time of departure matters more than airline choice.** Delays compound through the day. Flying before 8 AM nearly eliminates delay risk regardless of carrier. Friday evenings are consistently worst; Saturday mornings are best.

3. **High traffic volume does not predict high delays.** ATL (the busiest U.S. hub) maintains lower average delays than ORD or SFO despite comparable traffic, pointing to operational efficiency differences.

---

## Setup & Reproduction

### Requirements

No `requirements.txt` is included. Install the following manually:

```bash
pip install pandas numpy matplotlib seaborn altair plotly
```

D3.js v7 and TopoJSON are loaded from CDN in `index.html` — no installation needed.

### Steps

```bash
# 1. Download flights.csv from Kaggle and place it in the project root

# 2. Preprocess the data
python preprocess.py

# 3. Generate all visualizations
python generate_vizzes.py

# 4. Open the website
open index.html
```

---

## EDA

`EDA.ipynb` contains a full exploratory analysis of the raw 5.8M-flight dataset, including:
- Delay distributions per airline and per month
- Day-of-week patterns
- Delay cause breakdowns
- Cancellation rates and reasons
- Busiest routes and airports
- Geographic choropleth of delays by state (Plotly)

---

## References

- U.S. Bureau of Transportation Statistics — [On-Time Performance Data](https://www.transtats.bts.gov/)
- Kaggle Dataset — [2015 Flight Delays and Cancellations](https://www.kaggle.com/datasets/usdot/flight-delays)
