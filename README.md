# RaceCraft AI - Motorsport Performance Analysis

**Real-time race simulation and coaching system for the Toyota Gazoo Racing GR Cup Series**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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
Download from the [Hack the Track](https://hack-the-track.devpost.com/) website and place in `data/raw/`.

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
