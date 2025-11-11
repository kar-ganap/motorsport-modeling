# Data Setup Guide

This document explains how to set up the race telemetry data for development and analysis.

## Quick Start

### Option 1: Use Sample Data (For Testing)

We provide a representative sample of the Indianapolis telemetry data in the repository:

```bash
# Sample data is already included
data/samples/indy_telemetry_sample.csv  # ~1-2 MB, ~50k rows
```

This sample includes:
- Multiple drivers (diverse driving styles)
- Multiple laps (early, mid, late race phases)
- All telemetry parameters
- Sufficient for development and testing

### Option 2: Download Full Dataset (For Production Analysis)

For complete analysis, download the full race data from the [Toyota Gazoo Racing Hack the Track](https://hack-the-track.devpost.com/) website.

**Required files for Indianapolis analysis:**
1. `R1_indianapolis_motor_speedway_telemetry.csv` (~250 MB)
2. `R2_indianapolis_motor_speedway_telemetry.csv` (~250 MB)
3. Lap timing files (included in dataset)
4. Race results files (included in dataset)

**Installation:**

```bash
# 1. Download the Indianapolis dataset zip file(s)
# 2. Place in the data/ directory
data/
├── R1_indianapolis_motor_speedway_telemetry.zip
└── R2_indianapolis_motor_speedway_telemetry.zip

# 3. Extract (optional - scripts can read from .zip)
unzip data/R1_indianapolis_motor_speedway_telemetry.zip -d data/indianapolis/
```

## Creating Your Own Sample

If you want to create a custom sample from the full data:

```bash
python scripts/create_sample_data.py data/R1_indianapolis_motor_speedway_telemetry.zip
```

**Options:**
```bash
# Custom sample size (default: 50,000 rows)
python scripts/create_sample_data.py data/R1_telemetry.zip --sample-size 100000

# Custom output location
python scripts/create_sample_data.py data/R1_telemetry.zip --output-dir data/my_samples
```

The sampling script intelligently selects:
- Multiple drivers for diversity
- Different race phases (early/mid/late laps)
- All telemetry parameters proportionally
- Small enough to commit (<10 MB recommended)

## Data Structure

### Telemetry Data Format

The telemetry CSV uses **long format** (one row per measurement):

```csv
lap,vehicle_number,telemetry_name,telemetry_value,timestamp,...
1,55,speed,145.2,2024-07-20T10:15:23.450Z,...
1,55,ath,85.0,2024-07-20T10:15:23.450Z,...
1,55,pbrake_f,12.5,2024-07-20T10:15:23.450Z,...
```

### Available Telemetry Parameters

| Parameter | Description | Unit |
|-----------|-------------|------|
| `speed` | Vehicle speed | km/h |
| `ath` | Throttle position | 0-100% |
| `pbrake_f` | Front brake pressure | bar |
| `pbrake_r` | Rear brake pressure | bar |
| `gear` | Current gear | 1-6 |
| `nmot` | Engine RPM | RPM |
| `Steering_Angle` | Steering wheel angle | degrees |
| `accx_can` | Longitudinal acceleration | G |
| `accy_can` | Lateral acceleration | G |
| `VBOX_Lat_Min` | GPS Latitude | degrees |
| `VBOX_Long_Minutes` | GPS Longitude | degrees |
| `Laptrigger_lapdist_dls` | Distance from start/finish | meters |

### Track Metadata

Track configuration files are included in the repository:

```bash
data/
├── indy.json         # Track geometry, sectors, pit lane
└── indy_table.csv    # Sector lengths in inches/meters
```

## Data Storage Strategy

```
data/
├── *.zip                    # Large files (gitignored)
├── indianapolis/            # Extracted data (gitignored)
│   ├── R1_telemetry.csv    # ~250 MB
│   └── ...
├── samples/                 # Sample data (committed to git)
│   └── indy_telemetry_sample.csv  # ~1-2 MB ✅
├── *.json                   # Track metadata (committed) ✅
└── *_table.csv             # Reference data (committed) ✅
```

**Why this structure?**
- Large telemetry files stay local (fast git operations)
- Small samples and metadata are version controlled (everyone has them)
- Anyone can reproduce full analysis by downloading race data

## Validation

Verify your data setup:

```python
import pandas as pd

# Check sample data
df = pd.read_csv('data/samples/indy_telemetry_sample.csv')
print(f"Rows: {len(df):,}")
print(f"Vehicles: {df['vehicle_number'].nunique()}")
print(f"Parameters: {df['telemetry_name'].nunique()}")
```

Expected output:
```
Rows: ~50,000
Vehicles: 15-19
Parameters: 12
```

## Troubleshooting

### "File not found" errors

**Problem:** Scripts can't find telemetry data

**Solution:**
- Check the file path matches your directory structure
- Ensure .zip files are in `data/` directory
- Try using absolute paths

### Memory issues when loading data

**Problem:** Python crashes loading full telemetry CSV

**Solution:**
```python
# Read in chunks instead of all at once
for chunk in pd.read_csv('telemetry.csv', chunksize=100000):
    process(chunk)
```

### Sample data too large for git

**Problem:** Git refuses to commit sample file (>100 MB)

**Solution:**
```bash
# Create smaller sample
python scripts/create_sample_data.py data/R1_telemetry.zip --sample-size 20000
```

## Next Steps

1. ✅ Verify you have access to either sample or full data
2. 📊 Run exploratory data analysis: `notebooks/01_data_exploration.ipynb`
3. 🏎️ Start building metrics: `src/metrics/`
4. 📈 Train models: `src/models/`

## Questions?

See the main [README.md](README.md) for project overview and documentation links.
