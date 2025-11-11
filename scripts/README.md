# Scripts Directory

Utility scripts for data processing and analysis.

## Available Scripts

### `create_sample_data.py`

Creates a representative sample of telemetry data for development and testing.

**Purpose:**
- Extract a small, manageable subset from large telemetry files
- Ensure sample includes diverse drivers, laps, and parameters
- Small enough to commit to git (~1-2 MB)

**Usage:**
```bash
python scripts/create_sample_data.py data/R1_indianapolis_motor_speedway_telemetry.zip
```

**Options:**
- `--sample-size N`: Number of rows to sample (default: 50000)
- `--output-dir DIR`: Output directory (default: data/samples)

**Example:**
```bash
# Create a larger sample
python scripts/create_sample_data.py data/R1_telemetry.zip --sample-size 100000

# Save to custom location
python scripts/create_sample_data.py data/R1_telemetry.zip --output-dir data/my_samples
```

**Output:**
```
data/samples/indy_telemetry_sample.csv
```

See [DATA.md](../DATA.md) for more information on data setup and structure.
