# RaceCraft AI - Motorsport Performance Analysis

**Real-time race simulation and coaching system for the Toyota Gazoo Racing GR Cup Series**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 FOR JUDGES - QUICK START (5 Minutes)

This application runs **locally on your machine** to provide full access to the Race Analytics engine with real-time telemetry visualization.

### Prerequisites
- Python 3.11 or higher
- ~2GB disk space for data
- macOS, Linux, or Windows

### Setup Steps

**1. Install uv** (fast Python package manager):
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**2. Clone this repository**:
```bash
git clone https://github.com/kar-ganap/toyota-motorsport-analysis.git
cd toyota-motorsport-analysis
```

**3. Set up Python environment**:
```bash
uv venv --python 3.11
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev,app,ml]"
```

**4. Download race data**:
- Visit: https://trddev.com/hackathon-2025/
- Download the GR Cup telemetry dataset
- See detailed extraction instructions below in "Raw Data Structure"

**5. Launch the dashboard**:
```bash
streamlit run Dashboard.py
```

The app will automatically open at **http://localhost:8501**

### What to Explore

1. **🏁 Race Analytics** (Main Feature):
   - Real-time lap-by-lap coaching system
   - Full telemetry visualization (speed, throttle, brake, G-forces)
   - Performance analysis with actionable recommendations

2. **📊 Race Insights**:
   - Compare drivers across tracks
   - Identify performance patterns
   - Explore race dynamics

3. **ℹ️ About**:
   - Technical details and methodology

### Troubleshooting

- **Import errors**: Ensure you ran `uv pip install -e ".[dev,app,ml]"`
- **Data not found**: Verify `data/raw/tracks/` directory structure matches step 4
- **Port in use**: Run `streamlit run Home.py --server.port 8502`

---

## Overview

RaceCraft AI is a comprehensive motorsport analytics platform that combines predictive modeling with prescriptive coaching insights. Built for the [Toyota Gazoo Racing Hack the Track](https://hack-the-track.devpost.com/) hackathon.

**Key Features:**
- 📊 **Real-time analytics** - Lap-by-lap race simulation with live predictions
- 🎯 **Performance metrics** - 10 quantifiable metrics from telemetry data
- 🔮 **Predictive models** - Lap time, position, and tire degradation forecasting
- 🏎️ **GPS racing lines** - Visual comparison of driving techniques
- 💡 **Coaching insights** - Actionable recommendations for improvement
- 📈 **Strategy optimization** - Pit stop timing and race strategy

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/kar-ganap/motorsport-modeling.git
cd motorsport-modeling

# Install with uv (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

### Data Setup

See [DATA.md](DATA.md) for detailed instructions on setting up race data.

**Quick option - Use sample data:**
```bash
# Sample data is included in the repository
data/samples/indy_telemetry_sample.csv
```

**Full dataset:**
Download from https://trddev.com/hackathon-2025/ and see "Raw Data Structure" section below for detailed extraction instructions.

## Raw Data Structure

### Overview

The GR Cup dataset contains telemetry and timing data for 7 tracks with 2 races each (14 total races). The data is provided as ZIP archives that must be extracted into a specific directory structure for the application to work correctly.

### Required Directory Structure

Extract all downloaded data into `data/raw/tracks/` following this structure:

```
data/raw/tracks/
├── barber/
│   ├── race1/
│   │   ├── R1_barber_telemetry_data.csv          (REQUIRED - ~1.5GB)
│   │   ├── R1_barber_lap_time.csv                (REQUIRED)
│   │   ├── R1_barber_lap_start.csv               (REQUIRED)
│   │   ├── R1_barber_lap_end.csv                 (REQUIRED)
│   │   ├── 03_*.CSV                              (Optional - race results)
│   │   ├── 23_AnalysisEnduranceWithSections_*.CSV (Optional - analytics)
│   │   ├── 26_Weather_*.CSV                      (Optional - weather)
│   │   └── 99_Best 10 Laps By Driver_*.CSV       (Optional - best laps)
│   └── race2/
│       └── [same file structure as race1]
│
├── cota/
│   ├── race1/
│   │   ├── R1_cota_telemetry_data.csv
│   │   ├── COTA_lap_time_R1.csv
│   │   ├── COTA_lap_start_time_R1.csv
│   │   └── COTA_lap_end_time_R1.csv
│   └── race2/
│       └── [same file structure as race1]
│
├── indianapolis/
│   ├── race1/
│   │   ├── R1_indianapolis_motor_speedway_telemetry.csv  (REQUIRED - ~3GB, includes GPS)
│   │   ├── R1_indianapolis_motor_speedway_lap_time.csv   (REQUIRED)
│   │   ├── R1_indianapolis_motor_speedway_lap_start.csv  (REQUIRED)
│   │   ├── R1_indianapolis_motor_speedway_lap_end.csv    (REQUIRED)
│   │   └── [optional analytics files]
│   └── race2/
│       └── [same file structure as race1]
│
├── road-america/
│   ├── race1/
│   │   ├── R1_road_america_telemetry_data.csv
│   │   ├── road_america_lap_time_R1.csv
│   │   ├── road_america_lap_start_R1.csv
│   │   └── road_america_lap_end_R1.csv
│   └── race2/
│       └── [same file structure as race1]
│
├── sebring/
│   ├── race1/
│   │   ├── sebring_telemetry_R1.csv
│   │   ├── sebring_lap_time_R1.csv
│   │   ├── sebring_lap_start_time_R1.csv
│   │   └── sebring_lap_end_time_R1.csv
│   └── race2/
│       └── [same file structure as race1]
│
├── sonoma/
│   ├── race1/
│   │   ├── R1_sonoma_telemetry_data.csv
│   │   ├── sonoma_lap_time_R1.csv
│   │   ├── sonoma_lap_start_time_R1.csv
│   │   └── sonoma_lap_end_time_R1.csv
│   └── race2/
│       └── [same file structure as race1]
│
└── vir/
    ├── race1/
    │   ├── R1_VIR_telemetry_data.csv
    │   ├── vir_lap_time_R1.csv
    │   ├── vir_lap_start_R1.csv
    │   └── vir_lap_end_R1.csv
    └── race2/
        └── [same file structure as race1]
```

### Step-by-Step Extraction Instructions

1. **Download all race data** from https://trddev.com/hackathon-2025/
   - You should have 14 ZIP files (7 tracks × 2 races)

2. **Create the base directory** (if it doesn't exist):
   ```bash
   mkdir -p data/raw/tracks
   ```

3. **For each track** (e.g., `indianapolis`):
   ```bash
   # Create track directory
   mkdir -p data/raw/tracks/indianapolis/race1
   mkdir -p data/raw/tracks/indianapolis/race2
   ```

4. **Extract ZIP contents**:
   ```bash
   # Example for Indianapolis Race 1
   unzip R1_indianapolis_telemetry.zip -d data/raw/tracks/indianapolis/race1/

   # Example for Indianapolis Race 2
   unzip R2_indianapolis_telemetry.zip -d data/raw/tracks/indianapolis/race2/
   ```

5. **Repeat for all tracks**:
   - barber (race1, race2)
   - cota (race1, race2)
   - indianapolis (race1, race2)
   - road-america (race1, race2)
   - sebring (race1, race2)
   - sonoma (race1, race2)
   - vir (race1, race2)

### File Types and Importance

#### Required Files (4 per race):

1. **Telemetry CSV** (`*_telemetry*.csv` or `*_telemetry_data.csv`)
   - High-frequency sensor data (~247,000 samples per race)
   - Contains: speed, throttle, brake, G-forces, steering angle, GPS (some tracks only)
   - Size: 1.5-3GB per race
   - **Critical for all analysis**

2. **Lap Times CSV** (`*_lap_time*.csv`)
   - Lap-by-lap timing data for all drivers
   - Contains: vehicle_number, lap, lap_time, position
   - Size: ~50-90KB
   - **Critical for Race Insights**

3. **Lap Start Times CSV** (`*_lap_start*.csv`)
   - Timestamp when each lap begins
   - Used for time-syncing telemetry with lap numbers
   - Size: ~50-90KB
   - **Critical for telemetry alignment**

4. **Lap End Times CSV** (`*_lap_end*.csv`)
   - Timestamp when each lap completes
   - Used for lap boundary detection
   - Size: ~50-90KB
   - **Critical for telemetry alignment**

#### Optional Files (analytics metadata):

- `03_*.CSV` - Official race results
- `23_AnalysisEnduranceWithSections_*.CSV` - Sector-level analytics
- `26_Weather_*.CSV` - Weather conditions
- `99_Best 10 Laps By Driver_*.CSV` - Best lap summary

These files are used by the system when available but are not required for core functionality.

### Track-Specific Notes

**Indianapolis & COTA**: Include GPS data (latitude, longitude) in telemetry - enables racing line visualization

**Barber, Road America, Sebring, Sonoma, VIR**: No GPS data - analysis focuses on telemetry-based metrics only

**Sebring**: JSON format with lap 32768 corruption bug - automatically filtered by data loader

### Verification

After extraction, verify your structure:

```bash
# Check that all 14 race directories exist
ls data/raw/tracks/*/race*

# Should output:
# data/raw/tracks/barber/race1
# data/raw/tracks/barber/race2
# data/raw/tracks/cota/race1
# data/raw/tracks/cota/race2
# ... (14 total)

# Check required files for one race
ls data/raw/tracks/indianapolis/race1/*telemetry*.csv
ls data/raw/tracks/indianapolis/race1/*lap_time*.csv
ls data/raw/tracks/indianapolis/race1/*lap_start*.csv
ls data/raw/tracks/indianapolis/race1/*lap_end*.csv
```

All four commands should return existing files. If any are missing, re-extract that race's ZIP file.

### Disk Space Requirements

- **Full dataset**: ~20-25GB (all 14 races)
- **Single race**: ~1.5-3GB (telemetry files are largest)
- **Processed data**: ~2MB per race (generated automatically by dashboard)

### Troubleshooting

**"Data not found" errors**:
- Verify directory names match exactly (lowercase, hyphens not underscores)
- Ensure files are in `data/raw/tracks/<track>/race1/` not `data/raw/tracks/<track>/race1/<track>/`

**"No telemetry data" warnings**:
- Check that telemetry CSV files are present and not empty
- File names vary by track - loader auto-detects format

**"Missing GPS data" warnings**:
- Normal for most tracks - only Indianapolis and COTA have GPS
- Dashboard will skip GPS-based visualizations automatically

## Project Structure

```
motorsport-modeling/
├── src/motorsport_modeling/    # Main Python package
│   ├── data/                   # Data loading and processing
│   ├── metrics/                # Performance metrics
│   ├── models/                 # Predictive models
│   ├── visualization/          # Plotting and dashboards
│   └── utils/                  # Utilities
├── scripts/                    # Standalone scripts
├── notebooks/                  # Jupyter notebooks
├── tests/                      # Unit tests
├── docs/                       # Documentation
│   ├── project/               # Project planning
│   ├── domain/                # Racing fundamentals
│   ├── data/                  # Data guides
│   ├── technical/             # Technical specs
│   └── hackathon/             # Competition info
├── data/                      # Data directory
│   ├── raw/                   # Raw data (gitignored)
│   ├── processed/             # Processed data (gitignored)
│   ├── samples/               # Sample data (committed)
│   └── tracks/                # Track metadata (committed)
├── outputs/                   # Generated results (gitignored)
└── app/                       # Dashboard application
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed structure documentation.

## Usage

### As a Package

```python
from motorsport_modeling.data import load_telemetry
from motorsport_modeling.metrics import calculate_lap_consistency

# Load telemetry data
telemetry = load_telemetry('data/samples/indy_telemetry_sample.csv')

# Calculate metrics
consistency = calculate_lap_consistency(telemetry)
```

### Run Scripts

```bash
# Create sample data from full dataset
python scripts/create_sample_data.py data/raw/R1_indianapolis_telemetry.zip

# Process telemetry data
python scripts/process_telemetry.py

# Train predictive models
python scripts/train_models.py
```

### Explore with Notebooks

```bash
jupyter lab notebooks/
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=motorsport_modeling --cov-report=html
```

### Code Quality

```bash
# Format code (if using black)
black src/ tests/

# Lint (if using ruff)
ruff check src/ tests/
```

## Documentation

- **[DATA.md](DATA.md)** - Data setup and structure guide
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Detailed project organization
- **[docs/project/proposal.md](docs/project/proposal.md)** - Full project proposal
- **[docs/domain/racing_fundamentals.md](docs/domain/racing_fundamentals.md)** - Racing theory and principles
- **[docs/domain/quantifiable_metrics.md](docs/domain/quantifiable_metrics.md)** - Metrics documentation

## Hackathon Category

**Category 4: Real-Time Analytics**

> "Design a tool that simulates real-time decision-making for a race engineer."

Our approach: Lap-by-lap race replay with predictive analytics, technique monitoring, and strategy recommendations.

## Project Status

🚧 **In Development** - Building for Toyota Gazoo Racing Hack the Track hackathon

- [x] Project structure and organization
- [x] Data infrastructure and sampling
- [ ] Data loaders and processors
- [ ] Performance metrics implementation
- [ ] Predictive models
- [ ] GPS visualization
- [ ] Interactive dashboard
- [ ] Demo video

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Toyota Gazoo Racing for providing the race data
- GR Cup Series teams and drivers
- Hack the Track hackathon organizers

## Contact

For questions or collaboration: [Your contact info]

---

**Built with ❤️ for motorsport analytics**
