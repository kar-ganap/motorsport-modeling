# Data Directory

This directory contains all race data and track metadata.

## Structure

```
data/
├── raw/                    # Original data files (gitignored)
│   ├── *.zip              # Downloaded race data archives
│   └── indianapolis/      # Extracted telemetry files
├── processed/             # Cleaned and transformed data (gitignored)
│   └── *.parquet         # Processed data in efficient format
├── samples/               # Small representative samples (committed to git)
│   └── indy_telemetry_sample.csv
└── tracks/                # Track metadata and configuration (committed to git)
    ├── indy.json         # Indianapolis Motor Speedway configuration
    └── indy_table.csv    # Indianapolis sector measurements
```

## Getting Started

### Option 1: Use Sample Data

Sample data is included in the repository for testing and development:

```python
import pandas as pd

df = pd.read_csv('data/samples/indy_telemetry_sample.csv')
```

### Option 2: Download Full Dataset

1. Visit [Hack the Track](https://hack-the-track.devpost.com/)
2. Download the Indianapolis Motor Speedway dataset
3. Place .zip files in `data/raw/`
4. Run the data loader scripts

See [../DATA.md](../DATA.md) for complete setup instructions.

## Track Metadata

Track configuration files are version controlled:

- **`tracks/indy.json`** - Circuit geometry, sectors, pit lane configuration
- **`tracks/indy_table.csv`** - Sector lengths in various units

These files are used by the analysis pipeline to map telemetry data to track locations.
